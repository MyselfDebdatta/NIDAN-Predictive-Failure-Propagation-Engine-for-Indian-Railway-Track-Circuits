import {
  GatewayError,
  PaymentRequiredError,
  PermissionDeniedError,
  RateLimitError,
  RequestRejectedError,
  generateResponse,
} from "@lovable.dev/ai-gateway";
import {
  REVIEW_INSTRUCTIONS,
  REVIEW_MODEL,
  buildReviewPrompt,
  enforceNonVital,
  reviewDraftSchema,
  reviewJsonSchema,
  type ReviewRequest,
  type ReviewResult,
} from "@/lib/review";

export async function runEvidenceReview(request: ReviewRequest): Promise<ReviewResult> {
  try {
    const response = await generateResponse({
      model: REVIEW_MODEL,
      instructions: REVIEW_INSTRUCTIONS,
      input: [{ role: "user", content: buildReviewPrompt(request) }],
      text: {
        format: {
          type: "json_schema",
          name: "nidan_evidence_review",
          strict: true,
          schema: reviewJsonSchema,
        },
      },
      reasoning: { effort: "medium" },
    });

    let text = "";
    let refusal = "";
    for (const item of response.output ?? []) {
      if (item.type !== "message") continue;
      for (const part of item.content ?? []) {
        if (part.type === "output_text") text += part.text;
        else if (part.type === "refusal") refusal += part.refusal;
      }
    }
    if (!text) {
      return {
        ok: false,
        kind: "invalid",
        message: refusal
          ? `The model declined: ${refusal}`
          : "The model returned no draft. Check the context and try again.",
        referenceId: response.id ?? null,
      };
    }
    const parsed = reviewDraftSchema.safeParse(JSON.parse(text));
    if (!parsed.success) {
      console.error("[evidence-review] unexpected draft shape", parsed.error.message);
      return {
        ok: false,
        kind: "invalid",
        message: "The draft came back in an unexpected shape. Try again.",
        referenceId: response.id ?? null,
      };
    }
    const { kept, removedCount } = enforceNonVital(parsed.data.checklist);
    return {
      ok: true,
      review: { ...parsed.data, checklist: kept },
      removedCount,
      model: REVIEW_MODEL,
      generatedAt: new Date().toISOString(),
      referenceId: response.id ?? "unknown",
    };
  } catch (error) {
    if (error instanceof GatewayError) {
      const referenceId = error.ids?.requestId ?? error.ids?.logId ?? null;
      console.error("[evidence-review] gateway error", error.code, error.httpStatus, error.ids);
      if (error instanceof RateLimitError)
        return {
          ok: false,
          kind: "busy",
          message: "The AI service is busy. Wait a minute before drafting again.",
          referenceId,
        };
      if (error instanceof PaymentRequiredError)
        return {
          ok: false,
          kind: "credits",
          message:
            "AI credits for this workspace are used up. A workspace owner needs to add credits.",
          referenceId,
        };
      if (error instanceof PermissionDeniedError)
        return {
          ok: false,
          kind: "denied",
          message: "AI drafting is not allowed for this workspace right now.",
          referenceId,
        };
      if (error instanceof RequestRejectedError)
        return {
          ok: false,
          kind: "invalid",
          message: "The request was rejected. Shorten the context and try again.",
          referenceId,
        };
      return {
        ok: false,
        kind: "unavailable",
        message: "The draft could not be completed. Check whether it appeared before trying again.",
        referenceId,
      };
    }
    console.error("[evidence-review] failed", error);
    return {
      ok: false,
      kind: "unavailable",
      message: "The draft could not be completed. Try again.",
      referenceId: null,
    };
  }
}
