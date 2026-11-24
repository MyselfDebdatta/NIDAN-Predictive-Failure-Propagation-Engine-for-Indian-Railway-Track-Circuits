import { createFileRoute, Link, useNavigate } from "@tanstack/react-router";
import { useSuspenseQuery } from "@tanstack/react-query";
import { useId, useMemo, useState } from "react";
import {
  ArrowUpRight,
  ClipboardCopy,
  FileSearch,
  Loader2,
  RotateCcw,
  ShieldOff,
} from "lucide-react";
import { toast } from "sonner";
import type { Alert, Cluster } from "@/data/fixtures";
import { alertsQuery, assetQuery, clustersQuery } from "@/lib/queries";
import { useEvidenceReview } from "@/lib/mutations";
import {
  REVIEW_LIMITS,
  buildAlertSummary,
  buildCircuitContext,
  type ReviewResult,
} from "@/lib/review";
import {
  Chip,
  EmptyState,
  ErrorPanel,
  LevelBadge,
  Notice,
  PageHeading,
  PageSkeleton,
  Panel,
  Skeleton,
} from "@/components/nidan/primitives";
import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";

const byRank = (alerts: Alert[]) => [...alerts].sort((a, b) => a.policyRank - b.policyRank);
const pickAlert = (alerts: Alert[], id?: string) =>
  alerts.find((a) => a.id === id || a.assetId === id) ?? byRank(alerts)[0];

export const Route = createFileRoute("/review")({
  validateSearch: (search: Record<string, unknown>): { alert?: string } =>
    typeof search["alert"] === "string" ? { alert: search["alert"] } : {},
  loaderDeps: ({ search }) => ({ alert: search.alert }),
  loader: async ({ context, deps }) => {
    const alerts = await context.queryClient.ensureQueryData(alertsQuery);
    const selected = pickAlert(alerts, deps.alert);
    await Promise.all([
      context.queryClient.ensureQueryData(clustersQuery),
      selected ? context.queryClient.ensureQueryData(assetQuery(selected.assetId)) : null,
    ]);
  },
  head: () => ({
    meta: [
      { title: "Evidence review · AI draft — NIDAN" },
      {
        name: "description",
        content:
          "Give NIDAN an alert and its circuit context; an AI model summarises the evidence and drafts a non-vital checklist for the operator to verify.",
      },
      { property: "og:title", content: "NIDAN evidence review" },
      {
        property: "og:description",
        content:
          "An AI-drafted evidence summary and verification checklist — advisory, verified by the operator.",
      },
      { property: "og:type", content: "website" },
      { name: "twitter:card", content: "summary_large_image" },
    ],
  }),
  pendingComponent: PageSkeleton,
  component: EvidenceReview,
});

function EvidenceReview() {
  const search = Route.useSearch();
  const { data: alerts } = useSuspenseQuery(alertsQuery);
  const { data: clusters } = useSuspenseQuery(clustersQuery);
  const ranked = useMemo(() => byRank(alerts), [alerts]);
  const selected = pickAlert(alerts, search.alert);

  return (
    <div className="space-y-5 lg:space-y-6">
      <PageHeading
        eyebrow="Assure · AI draft"
        title="Evidence review"
        titleHi="साक्ष्य समीक्षा"
        subtitle="Choose an alert, check the circuit context, and let an AI model summarise the evidence and draft a checklist. You verify every step; the draft never changes a level, a ranking or any equipment."
      >
        <Chip tone="accent">
          <ShieldOff className="h-3.5 w-3.5" aria-hidden="true" />
          Advisory · non-vital
        </Chip>
        <Chip tone="warning">Demo data</Chip>
      </PageHeading>
      <Notice title="What leaves this device">
        This page is the only part of NIDAN that calls a language model. When you draft a summary,
        the selected alert, its circuit context and your notes are sent through the platform AI
        gateway to a hosted model for processing. They are not stored by NIDAN, not written to SMMS
        and never applied to equipment. In a real deployment the gateway and model are governed by
        the railway's data-handling policy; the API key stays server-side and never reaches the
        browser. If the policy forbids external processing, do not use this page — every other
        screen works without it.
      </Notice>
      {selected ? (
        <ReviewWorkspace key={selected.id} alert={selected} alerts={ranked} clusters={clusters} />
      ) : (
        <EmptyState title="No open alerts">There is nothing to review right now.</EmptyState>
      )}
    </div>
  );
}

function ReviewWorkspace({
  alert,
  alerts,
  clusters,
}: {
  alert: Alert;
  alerts: Alert[];
  clusters: Cluster[];
}) {
  const { data: asset } = useSuspenseQuery(assetQuery(alert.assetId));
  const cluster = clusters.find((c) => c.id === alert.clusterId);
  const navigate = useNavigate();
  const defaultContext = useMemo(() => buildCircuitContext(asset, cluster), [asset, cluster]);
  const alertSummary = useMemo(() => buildAlertSummary(alert), [alert]);
  const [context, setContext] = useState(defaultContext);
  const [notes, setNotes] = useState("");
  const [contextError, setContextError] = useState<string | null>(null);
  const [result, setResult] = useState<ReviewResult | null>(null);
  const review = useEvidenceReview();
  const ids = {
    alert: useId(),
    context: useId(),
    notes: useId(),
    contextHint: useId(),
    contextError: useId(),
  };

  const submit = () => {
    const trimmed = context.trim();
    if (trimmed.length < REVIEW_LIMITS.minContext) {
      setContextError("Add at least a sentence of circuit context.");
      document.getElementById(ids.context)?.focus();
      return;
    }
    setContextError(null);
    setResult(null);
    review.mutate(
      { alertId: alert.id, alertSummary, circuitContext: trimmed, operatorNotes: notes.trim() },
      {
        onSuccess: (value) => setResult(value),
        onError: () =>
          setResult({
            ok: false,
            kind: "unavailable",
            message: "The draft could not be requested. Check your connection and try again.",
            referenceId: null,
          }),
      },
    );
  };

  return (
    <div className="grid gap-4 lg:grid-cols-12 lg:gap-5">
      <div className="min-w-0 lg:col-span-5">
        <Panel eyebrow="Step 1 · inputs" title="Alert and circuit context">
          <form
            className="space-y-4"
            onSubmit={(event) => {
              event.preventDefault();
              submit();
            }}
          >
            <div>
              <label htmlFor={ids.alert} className="text-sm font-semibold text-text-hi">
                Alert
              </label>
              <select
                id={ids.alert}
                value={alert.id}
                onChange={(event) =>
                  void navigate({ to: "/review", search: { alert: event.target.value } })
                }
                className="mt-1.5 min-h-11 w-full rounded-sm border border-border-strong bg-bg-inset px-3 font-data text-sm text-text-hi"
              >
                {alerts.map((a) => (
                  <option key={a.id} value={a.id}>
                    #{a.policyRank} · {a.assetId} · {a.level}
                  </option>
                ))}
              </select>
            </div>

            <div className="rounded-md border border-border p-3">
              <div className="flex flex-wrap items-center gap-2">
                <LevelBadge level={alert.level} />
                <Chip tone="mono">{alert.id}</Chip>
                {alert.clusterId && <Chip tone="mono">{alert.clusterId}</Chip>}
              </div>
              <p className="mt-2 text-sm text-text-hi">{alert.assetName}</p>
              <p className="mt-1 text-sm leading-6 text-text-mid">
                {alert.explanation.physics.headline}.
              </p>
              <div className="mt-2 flex flex-wrap gap-x-4">
                <Link
                  to="/alerts/$alertId"
                  params={{ alertId: alert.id }}
                  className="inline-flex min-h-11 items-center gap-1 text-sm font-semibold text-accent-text underline-offset-4 hover:underline"
                >
                  Triage
                  <ArrowUpRight className="h-4 w-4" aria-hidden="true" />
                </Link>
                <Link
                  to="/assets/$assetId"
                  params={{ assetId: alert.assetId }}
                  className="inline-flex min-h-11 items-center gap-1 text-sm font-semibold text-accent-text underline-offset-4 hover:underline"
                >
                  Circuit detail
                  <ArrowUpRight className="h-4 w-4" aria-hidden="true" />
                </Link>
              </div>
              <details className="group mt-1">
                <summary className="inline-flex min-h-11 cursor-pointer items-center text-sm font-semibold text-text-mid hover:text-text-hi">
                  Alert evidence sent to the model
                </summary>
                <pre className="scrollbar-thin mt-1 max-h-64 overflow-auto whitespace-pre-wrap rounded-sm bg-bg-inset p-3 font-data text-xs leading-5 text-text-mid">
                  {alertSummary}
                </pre>
              </details>
            </div>

            <div>
              <div className="flex items-end justify-between gap-2">
                <label htmlFor={ids.context} className="text-sm font-semibold text-text-hi">
                  Circuit context
                </label>
                <button
                  type="button"
                  onClick={() => {
                    setContext(defaultContext);
                    setContextError(null);
                  }}
                  className="inline-flex min-h-11 items-center gap-1 text-xs font-semibold text-text-mid hover:text-text-hi"
                >
                  <RotateCcw className="h-3.5 w-3.5" aria-hidden="true" />
                  Reset to record
                </button>
              </div>
              <p id={ids.contextHint} className="text-xs leading-5 text-text-lo">
                Pre-filled from the asset record, signals and common-cause links. Edit freely.
              </p>
              <textarea
                id={ids.context}
                value={context}
                onChange={(event) => setContext(event.target.value)}
                maxLength={REVIEW_LIMITS.context}
                rows={9}
                aria-invalid={!!contextError}
                aria-describedby={
                  contextError ? `${ids.contextHint} ${ids.contextError}` : ids.contextHint
                }
                className="mt-1.5 w-full rounded-sm border border-border-strong bg-bg-inset p-3 font-data text-xs leading-5 text-text-hi"
              />
              <div className="mt-1 flex justify-between gap-2 text-xs">
                <p id={ids.contextError} className="min-h-4 text-critical">
                  {contextError ?? ""}
                </p>
                <span className="font-data text-text-lo">
                  {context.length}/{REVIEW_LIMITS.context}
                </span>
              </div>
            </div>

            <div>
              <label htmlFor={ids.notes} className="text-sm font-semibold text-text-hi">
                Operator notes <span className="font-normal text-text-lo">(optional)</span>
              </label>
              <textarea
                id={ids.notes}
                value={notes}
                onChange={(event) => setNotes(event.target.value)}
                maxLength={REVIEW_LIMITS.notes}
                rows={4}
                placeholder="e.g. Maintainer reported standing water at the Down Goods cess on 12 Jul."
                className="mt-1.5 w-full rounded-sm border border-border-strong bg-bg-inset p-3 text-sm text-text-hi placeholder:text-text-lo"
              />
            </div>

            <Button type="submit" size="lg" className="w-full" disabled={review.isPending}>
              {review.isPending ? (
                <Loader2 className="animate-spin" aria-hidden="true" />
              ) : (
                <FileSearch aria-hidden="true" />
              )}
              {review.isPending
                ? "Drafting…"
                : result?.ok
                  ? "Draft again"
                  : "Draft summary & checklist"}
            </Button>
            <p className="text-xs leading-5 text-text-lo">
              The alert evidence, context and notes above are sent through the platform AI gateway
              to a hosted model. Nothing is saved by NIDAN, sent to SMMS or applied to equipment.
            </p>
          </form>
        </Panel>
      </div>

      <div className="min-w-0 lg:col-span-7">
        <ReviewOutput
          pending={review.isPending}
          result={result}
          onRetry={submit}
          assetId={alert.assetId}
        />
      </div>
    </div>
  );
}

const strengthMark: Record<string, string> = { strong: "●●●", moderate: "●●○", weak: "●○○" };
const categoryLabel: Record<string, string> = {
  records: "Records",
  telemetry: "Telemetry",
  "field-observation": "Field report",
  "data-quality": "Data quality",
  planning: "Planning",
};
const sourceLabel: Record<string, string> = {
  physics: "Physics",
  model: "Model",
  precedent: "Precedent",
  "data-trust": "Data trust",
  cluster: "Common cause",
  block: "Rolling Block",
  operator: "Operator note",
};

function ReviewOutput({
  pending,
  result,
  onRetry,
  assetId,
}: {
  pending: boolean;
  result: ReviewResult | null;
  onRetry: () => void;
  assetId: string;
}) {
  if (pending) {
    return (
      <Panel eyebrow="Step 2 · AI draft" title="Drafting">
        <p role="status" className="text-sm text-text-mid">
          Reading the evidence for {assetId}. This usually takes 10–30 seconds.
        </p>
        <div className="mt-4 space-y-3">
          <Skeleton className="h-4 w-11/12" />
          <Skeleton className="h-4 w-9/12" />
          <Skeleton className="h-4 w-10/12" />
          <Skeleton className="mt-6 h-12 w-full" />
          <Skeleton className="h-12 w-full" />
          <Skeleton className="h-12 w-full" />
        </div>
      </Panel>
    );
  }
  if (!result) {
    return (
      <Panel eyebrow="Step 2 · AI draft" title="Summary and checklist">
        <EmptyState title="No draft yet">
          Check the context on the left, then choose “Draft summary & checklist”. The draft lists
          the evidence, what is still uncertain, and steps for you to verify.
        </EmptyState>
      </Panel>
    );
  }
  if (!result.ok) {
    return (
      <ErrorPanel
        title="The draft didn't complete"
        detail={result.message}
        {...(result.referenceId ? { traceId: result.referenceId } : {})}
        onRetry={onRetry}
      />
    );
  }
  return <ReviewDraftView result={result} />;
}

function ReviewDraftView({ result }: { result: Extract<ReviewResult, { ok: true }> }) {
  const { review } = result;
  const [checked, setChecked] = useState<Set<number>>(() => new Set());
  const done = checked.size;
  const total = review.checklist.length;
  const time = new Intl.DateTimeFormat("en-IN", {
    timeZone: "Asia/Kolkata",
    hour: "2-digit",
    minute: "2-digit",
    hour12: false,
  }).format(new Date(result.generatedAt));
  const toggle = (index: number) =>
    setChecked((prev) => {
      const next = new Set(prev);
      if (next.has(index)) next.delete(index);
      else next.add(index);
      return next;
    });
  const copy = async () => {
    const text = [
      `NIDAN evidence review (AI draft, ${time} IST) — advisory, verify before use`,
      "",
      review.summary,
      "",
      ...review.checklist.map(
        (item, i) => `[${checked.has(i) ? "x" : " "}] ${item.check} — ${item.rationale}`,
      ),
    ].join("\n");
    try {
      await navigator.clipboard.writeText(text);
      toast.success("Checklist copied");
    } catch {
      toast.error("Copy failed — select the text instead.");
    }
  };

  return (
    <div className="space-y-4" aria-live="polite">
      <Notice tone="accent" title="AI draft · verify before use">
        Drafted by {result.model} at <span className="font-data">{time}</span> IST from the inputs
        on the left. It cannot change the alert level, ranking or any equipment.
      </Notice>
      {result.removedCount > 0 && (
        <Notice title="Steps removed">
          {result.removedCount} suggested {result.removedCount === 1 ? "step was" : "steps were"}{" "}
          removed because {result.removedCount === 1 ? "it" : "they"} would act on vital equipment.
          NIDAN only drafts verification steps.
        </Notice>
      )}

      <Panel eyebrow="Step 2 · AI draft" title="Evidence summary">
        <p className="text-sm leading-6 text-text-hi">{review.summary}</p>
        {review.evidence.length > 0 && (
          <ul className="mt-4 divide-y divide-border-subtle border-t border-border-subtle">
            {review.evidence.map((item, i) => (
              <li
                key={i}
                className="flex flex-col gap-1.5 py-2.5 sm:flex-row sm:items-start sm:gap-3"
              >
                <span className="flex shrink-0 items-center gap-2 sm:w-44">
                  <Chip tone="mono">{sourceLabel[item.source] ?? item.source}</Chip>
                  <span className="text-xs text-text-mid">
                    <span aria-hidden="true" className="font-data text-accent-text">
                      {strengthMark[item.strength]}
                    </span>{" "}
                    {item.strength}
                  </span>
                </span>
                <span className="text-sm leading-6 text-text-hi">{item.claim}</span>
              </li>
            ))}
          </ul>
        )}
        {review.uncertainties.length > 0 && (
          <div className="mt-4">
            <h3 className="text-sm font-semibold text-text-hi">Still uncertain</h3>
            <ul className="mt-2 list-disc space-y-1 pl-5 text-sm leading-6 text-text-mid">
              {review.uncertainties.map((u, i) => (
                <li key={i}>{u}</li>
              ))}
            </ul>
          </div>
        )}
      </Panel>

      <Panel
        eyebrow="Step 3 · you verify"
        title="Verification checklist"
        action={
          <span className="font-data text-sm text-text-mid" aria-live="polite">
            {done} of {total} verified
          </span>
        }
      >
        {total === 0 ? (
          <EmptyState title="No checklist steps">Draft again with more circuit context.</EmptyState>
        ) : (
          <ul className="space-y-2">
            {review.checklist.map((item, i) => {
              const id = `review-check-${i}`;
              const isChecked = checked.has(i);
              return (
                <li key={i}>
                  <label
                    htmlFor={id}
                    className={cn(
                      "flex cursor-pointer items-start gap-3 rounded-md border p-3 transition-colors duration-[var(--dur-1)]",
                      isChecked
                        ? "border-accent bg-accent-wash"
                        : "border-border hover:bg-bg-hover",
                    )}
                  >
                    <input
                      id={id}
                      type="checkbox"
                      checked={isChecked}
                      onChange={() => toggle(i)}
                      className="mt-0.5 h-5 w-5 shrink-0 accent-[var(--accent)]"
                    />
                    <span className="min-w-0 flex-1">
                      <span className="flex flex-wrap items-center gap-2">
                        <span
                          className={cn(
                            "text-sm font-semibold text-text-hi",
                            isChecked && "line-through decoration-text-lo",
                          )}
                        >
                          {item.check}
                        </span>
                        <Chip>{categoryLabel[item.category] ?? item.category}</Chip>
                      </span>
                      <span className="mt-1 block text-xs leading-5 text-text-mid">
                        {item.rationale}
                      </span>
                    </span>
                  </label>
                </li>
              );
            })}
          </ul>
        )}
        {total > 0 && done === total && (
          <div className="mt-4">
            <Notice tone="accent" title="All steps verified by you">
              Record the outcome in the SMMS draft from circuit detail. Ticks are kept only on this
              screen.
            </Notice>
          </div>
        )}
        <div className="mt-4 flex flex-wrap gap-2">
          <Button variant="outline" onClick={() => void copy()}>
            <ClipboardCopy aria-hidden="true" />
            Copy checklist
          </Button>
          {done > 0 && (
            <Button variant="ghost" onClick={() => setChecked(new Set())}>
              Clear ticks
            </Button>
          )}
        </div>
        <p className="mt-3 text-xs text-text-lo">
          Reference <span className="font-data">{result.referenceId}</span>
        </p>
      </Panel>
    </div>
  );
}
