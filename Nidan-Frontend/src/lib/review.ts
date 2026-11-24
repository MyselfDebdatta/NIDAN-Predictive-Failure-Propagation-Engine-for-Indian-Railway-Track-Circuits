import { z } from "zod";
import { failureModes, type Alert, type Cluster } from "@/data/fixtures";
import type { AssetDetail } from "@/lib/api";

/**
 * AI evidence review: the operator supplies an alert and its circuit context; a model drafts an
 * evidence summary and a checklist for the operator to verify. Client-safe helpers only — the
 * model call lives in review.server.ts. The draft is advisory and never changes ranking or levels.
 */
export const REVIEW_MODEL = "openai/gpt-6-astra" as const;

export const REVIEW_LIMITS = { alert: 6000, context: 4000, notes: 2000, minContext: 20 } as const;

export const reviewRequestSchema = z.object({
  alertId: z.string().trim().min(1).max(80),
  alertSummary: z.string().trim().min(1).max(REVIEW_LIMITS.alert),
  circuitContext: z
    .string()
    .trim()
    .min(REVIEW_LIMITS.minContext, "Add at least a sentence of circuit context.")
    .max(REVIEW_LIMITS.context),
  operatorNotes: z.string().trim().max(REVIEW_LIMITS.notes),
});
export type ReviewRequest = z.infer<typeof reviewRequestSchema>;

export const evidenceSources = [
  "physics",
  "model",
  "precedent",
  "data-trust",
  "cluster",
  "block",
  "operator",
] as const;
export const evidenceStrengths = ["strong", "moderate", "weak"] as const;
export const checklistCategories = [
  "records",
  "telemetry",
  "field-observation",
  "data-quality",
  "planning",
] as const;

export const reviewDraftSchema = z.object({
  summary: z.string().min(1),
  evidence: z.array(
    z.object({
      claim: z.string().min(1),
      source: z.enum(evidenceSources),
      strength: z.enum(evidenceStrengths),
    }),
  ),
  uncertainties: z.array(z.string().min(1)),
  checklist: z.array(
    z.object({
      check: z.string().min(1),
      rationale: z.string().min(1),
      category: z.enum(checklistCategories),
    }),
  ),
});
export type ReviewDraft = z.infer<typeof reviewDraftSchema>;
export type ChecklistItem = ReviewDraft["checklist"][number];

/** Strict JSON schema mirrored from reviewDraftSchema for the model's structured output. */
export const reviewJsonSchema = {
  type: "object",
  additionalProperties: false,
  required: ["summary", "evidence", "uncertainties", "checklist"],
  properties: {
    summary: {
      type: "string",
      description:
        "3–5 plain sentences: what the evidence shows, how strong it is, what is still unknown.",
    },
    evidence: {
      type: "array",
      items: {
        type: "object",
        additionalProperties: false,
        required: ["claim", "source", "strength"],
        properties: {
          claim: { type: "string" },
          source: { type: "string", enum: [...evidenceSources] },
          strength: { type: "string", enum: [...evidenceStrengths] },
        },
      },
    },
    uncertainties: { type: "array", items: { type: "string" } },
    checklist: {
      type: "array",
      items: {
        type: "object",
        additionalProperties: false,
        required: ["check", "rationale", "category"],
        properties: {
          check: {
            type: "string",
            description:
              "One verification step an operator can confirm by reading records, telemetry or a field report.",
          },
          rationale: { type: "string" },
          category: { type: "string", enum: [...checklistCategories] },
        },
      },
    },
  },
} as const;

export const REVIEW_INSTRUCTIONS = [
  "You assist an Indian Railways signalling control-room operator (SSE Signal) reviewing a NIDAN advisory alert for a track circuit.",
  "NIDAN is advisory and non-vital. It has no write path to interlocking, signals, routes, points or track circuits, and neither do you.",
  "Summarise only the evidence supplied. Never invent readings, dates, asset IDs or precedents. If something is missing, say so in uncertainties.",
  "Do not change or second-guess the alert level, risk, remaining useful life or ranking; treat them as model outputs to be verified.",
  "Draft a checklist of 5–8 verification steps an operator can confirm by reading records, telemetry, SMMS history, weather data, or by asking the maintainer for a field report during a Rolling Block.",
  "Every step must be observational or a records check. Never include a step that operates, resets, bypasses, isolates or alters any vital equipment or its state; say 'Report to the maintainer' instead.",
  "Include the falsifier from the alert as a checklist step when one is given.",
  "Write in clear British English for a railway engineer. Keep each step under 30 words.",
].join("\n");

export function buildReviewPrompt(request: ReviewRequest) {
  return [
    "Return JSON matching the schema.",
    "",
    `## Alert ${request.alertId}`,
    request.alertSummary,
    "",
    "## Circuit context (supplied by operator)",
    request.circuitContext,
    "",
    "## Operator notes",
    request.operatorNotes || "(none)",
  ].join("\n");
}

const pct = (value: number) => `${Math.round(value * 100)}%`;

/** Plain-text snapshot of one alert, built from the same data the triage drawer shows. */
export function buildAlertSummary(alert: Alert) {
  const e = alert.explanation;
  const lines = [
    `Asset: ${alert.assetId} — ${alert.assetName} (${alert.division}, ${alert.route})`,
    `Level: ${alert.level}; policy rank #${alert.policyRank}; held for ${alert.persistence} evaluations; age ${alert.ageMinutes} min`,
    `Calibrated risk: 24 h ${pct(alert.risk.h24)}, 72 h ${pct(alert.risk.h72)}, 7 d ${pct(alert.risk.h7d)}`,
    `Remaining useful life: p10 ${alert.rul.p10Days} d, median ${alert.rul.medianDays} d, p90 ${alert.rul.p90Days} d (coverage ${alert.rul.coverage}, n=${alert.rul.heldOutN})`,
    `Likely modes: ${alert.likelyModes.map((m) => `${m} ${failureModes[m]}`).join("; ")}; top probability ${alert.modeProbability}; conformal set {${e.model.modeSet.join(", ")}} at ${alert.modeSetCoverage}`,
    `Physics: ${e.physics.headline}`,
    ...e.physics.state.map((s) => `  - ${s.label}: ${s.value} (baseline ${s.baseline})`),
    `Falsifier: ${e.physics.falsifier}`,
    `Model drivers: ${e.model.shapTop.map((s) => `${s.label} ${s.value}`).join("; ")}`,
    `Calibration: ${e.model.calibrationNote}; physics/model agreement ${e.model.agreement}`,
    `Precedents: ${e.precedents.map((p) => `${p.smmsId} ${p.assetId} ${p.confirmedMode} sim ${p.similarity}, ${p.daysAgo} d ago — ${p.outcome}`).join(" | ") || "none"}`,
    `Data trust: ${alert.dataTrust.score}${alert.dataTrust.flags.length ? ` (${alert.dataTrust.flags.join(", ")})` : ""}`,
    `Consequence: ${alert.ranking.consequence} — ${alert.ranking.consequenceNote}; exposure ${alert.ranking.exposure}`,
  ];
  if (alert.block)
    lines.push(
      `Rolling Block: ${alert.block.window.id} ${alert.block.window.date} ${alert.block.window.start}–${alert.block.window.end}; job ${alert.block.minutes} min; fit ${alert.block.fit}`,
    );
  if (alert.acknowledged) lines.push("Workflow: acknowledged, still open");
  if (alert.deferral)
    lines.push(`Workflow: deferred to ${alert.deferral.reviewDate} — ${alert.deferral.reason}`);
  return lines.join("\n");
}

/** Editable default for the circuit-context box: asset record, recent signals and common-cause links. */
export function buildCircuitContext(asset: AssetDetail, cluster?: Cluster) {
  const lines: string[] = [];
  const r = asset.record;
  if (r) {
    lines.push(
      `Record: ${r.circuitType} track circuit, ${r.lengthM} m, installed ${r.installed}, codal life ${r.codalLifeYears} y`,
    );
    lines.push(
      `Relay ${r.relay}; supply ${r.supply}; cable ${r.cable}; relay room ${r.relayRoom}; weather cell ${r.weatherCell}`,
    );
  }
  for (const s of asset.signals) {
    const first = s.values[0];
    const last = s.values.at(-1);
    if (first !== undefined && last !== undefined)
      lines.push(
        `Signal ${s.label}: ${first} → ${last} ${s.unit} over ${s.values.length} days (normal ${s.normalBand})`,
      );
  }
  if (cluster) {
    lines.push(
      `Common cause ${cluster.id} (${cluster.title}, ${cluster.state}): members ${cluster.members.join(", ")}`,
    );
    cluster.sharedEdges.forEach((edge) => lines.push(`  - ${edge.kind} ${edge.id}: ${edge.note}`));
    if (cluster.predictedCascade)
      lines.push(
        `Predicted cascade to ${cluster.predictedCascade.assetId} in ${cluster.predictedCascade.inDays.min}–${cluster.predictedCascade.inDays.max} days`,
      );
  }
  if (!lines.length)
    lines.push(
      "No asset record or signal history in the demo dataset for this circuit. Add what you know: recent maintenance, weather, crew reports.",
    );
  return lines.join("\n");
}

const controlVerbs =
  "operat(?:e|es|ed|ing)|set(?:s|ting)?|clear(?:s|ed|ing)?|throw(?:s|n|ing)?|reset(?:s|ting)?|bypass(?:es|ed|ing)?|overrid(?:e|es|den|ing)|disconnect(?:s|ed|ing)?|isolat(?:e|es|ed|ing)|switch(?:es|ed|ing)?|reconfigur(?:e|es|ed|ing)|jumper(?:s|ed|ing)?|strap(?:s|ped|ping)?|(?:de-?)?energi[sz](?:e|es|ed|ing)|forc(?:e|es|ed|ing)|cancel(?:s|led|ling)?|unlock(?:s|ed|ing)?|lock(?:s|ed|ing)?";
const vitalObjects =
  "interlocking|signals?|routes?|points?|track[- ]circuits?|relays?|block instruments?|axle[- ]counters?|panel|point machines?|crank handles?";
const verbThenObject = new RegExp(
  `\\b(?:${controlVerbs})\\b(?:\\W+\\w+){0,4}?\\W+(?:${vitalObjects})\\b`,
  "i",
);
const objectThenVerb = new RegExp(
  `\\b(?:${vitalObjects})\\b(?:\\W+\\w+){0,3}?\\W+(?:be\\W+)?(?:${controlVerbs})\\b`,
  "i",
);

/** True when a step would act on vital equipment rather than verify evidence. */
export function isVitalAction(text: string) {
  return verbThenObject.test(text) || objectThenVerb.test(text);
}

/** Non-vital boundary for model output: steps that act on vital equipment are dropped, never shown. */
export function enforceNonVital(items: ChecklistItem[]) {
  const kept = items.filter((item) => !isVitalAction(`${item.check} ${item.rationale}`));
  return { kept, removedCount: items.length - kept.length };
}

export type ReviewResult =
  | {
      ok: true;
      review: ReviewDraft;
      removedCount: number;
      model: string;
      generatedAt: string;
      referenceId: string;
    }
  | {
      ok: false;
      kind: "busy" | "credits" | "denied" | "invalid" | "unavailable";
      message: string;
      referenceId: string | null;
    };
