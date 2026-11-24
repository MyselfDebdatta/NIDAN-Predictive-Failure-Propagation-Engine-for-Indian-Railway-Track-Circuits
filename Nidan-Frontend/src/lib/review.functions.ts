import { createServerFn } from "@tanstack/react-start";
import { reviewRequestSchema } from "@/lib/review";
import { runEvidenceReview } from "@/lib/review.server";

/** Drafts an evidence summary + non-vital verification checklist. Advisory text only; nothing is stored or actioned. */
export const draftEvidenceReview = createServerFn({ method: "POST" })
  .inputValidator((input: unknown) => reviewRequestSchema.parse(input))
  .handler(async ({ data }) => runEvidenceReview(data));
