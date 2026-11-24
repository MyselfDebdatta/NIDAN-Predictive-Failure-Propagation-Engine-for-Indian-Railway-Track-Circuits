import { createFileRoute, Link } from "@tanstack/react-router";
import { useSuspenseQuery } from "@tanstack/react-query";
import { useState } from "react";
import { ArrowLeft, FilePlus2, FileSearch } from "lucide-react";
import { toast } from "sonner";
import { assetQuery, clustersQuery } from "@/lib/queries";
import { useDraftWorkOrder } from "@/lib/mutations";
import { failureModes } from "@/data/fixtures";
import { formatDecimal, formatShortDate } from "@/lib/formatters";
import {
  AssetLink,
  BlockFitBadge,
  Chip,
  DataTrust,
  EmptyState,
  LevelBadge,
  Notice,
  PageSkeleton,
  Panel,
  StageRail,
  ErrorPanel,
} from "@/components/nidan/primitives";
import { ExplanationCard, RiskHorizon, RulBand, Sparkline } from "@/components/nidan/charts";
import { AssetRecordList, DraftSmmsDialog } from "@/components/nidan/domain";
import { Button } from "@/components/ui/button";
import { blockFitText } from "@/lib/policy";
import { blockInsideP10, blockWhenLabel, daysUntilBlock } from "@/lib/blocks";

export const Route = createFileRoute("/assets/$assetId")({
  loader: ({ context, params }) =>
    Promise.all([
      context.queryClient.ensureQueryData(assetQuery(params.assetId)),
      context.queryClient.ensureQueryData(clustersQuery),
    ]),
  head: ({ params }) => ({
    meta: [
      { title: `${params.assetId} · circuit detail — NIDAN` },
      {
        name: "description",
        content: `What is happening to track circuit ${params.assetId}, the physical story, remaining useful life and the Rolling Block that can absorb the fix.`,
      },
      { property: "og:title", content: `NIDAN circuit detail · ${params.assetId}` },
      {
        property: "og:description",
        content: "Early signs, cause, course and response for one track circuit.",
      },
      { property: "og:type", content: "website" },
      { name: "twitter:card", content: "summary_large_image" },
    ],
  }),
  pendingComponent: PageSkeleton,
  errorComponent: ({ error, reset }) => (
    <ErrorPanel
      title="Circuit detail didn't load"
      detail={error instanceof Error ? error.message : "Unknown error"}
      traceId="demo-404"
      onRetry={reset}
    />
  ),
  component: CircuitDetail,
});

const recommended = "Ballast clearing + drain rodding";

function CircuitDetail() {
  const { assetId } = Route.useParams();
  const { data } = useSuspenseQuery(assetQuery(assetId));
  const { data: clusters } = useSuspenseQuery(clustersQuery);
  const [draftOpen, setDraftOpen] = useState(false);
  const draft = useDraftWorkOrder();
  const alert = data.alert;
  if (!alert)
    return (
      <EmptyState title="No telemetry in 30 days">
        This asset has no recent evaluations. Data trust explains why.
      </EmptyState>
    );
  const cluster = clusters.find((c) => c.id === alert.clusterId);
  const block = alert.block;
  const blockInDays = daysUntilBlock(alert);
  const insideP10 = blockInsideP10(alert, blockInDays);
  const action =
    alert.assetId === "ADRA/TC/12T"
      ? recommended
      : `Inspect for ${alert.likelyModes[0]} · ${failureModes[alert.likelyModes[0] ?? "F12"]}`;

  return (
    <div className="space-y-5 lg:space-y-6">
      <header className="flex min-w-0 flex-col gap-4 lg:flex-row lg:items-end lg:justify-between">
        <div className="min-w-0">
          <Link
            to="/alerts"
            className="inline-flex min-h-11 items-center gap-1.5 text-xs font-semibold text-text-lo hover:text-text-hi"
          >
            <ArrowLeft className="h-4 w-4" aria-hidden="true" />
            Back to queue
          </Link>
          <h1 className="mt-1 break-words font-data text-[24px] font-semibold leading-8 text-text-hi sm:text-[28px] sm:leading-9">
            {alert.assetId}
          </h1>
          <p className="mt-1 text-sm text-text-mid">{alert.assetName}</p>
          <div className="mt-3 flex flex-wrap gap-2">
            <LevelBadge level={alert.level} />
            <Link to="/models" hash="data-trust" className="rounded-sm">
              <DataTrust score={alert.dataTrust.score} flags={alert.dataTrust.flags} />
            </Link>
            <Chip tone="mono">{alert.id}</Chip>
            <Chip>Held {alert.persistence} evaluations</Chip>
          </div>
        </div>
        <div className="flex flex-wrap gap-2">
          <Button size="lg" variant="outline" asChild>
            <Link to="/review" search={{ alert: alert.id }}>
              <FileSearch aria-hidden="true" />
              Review evidence
            </Link>
          </Button>
          <Button size="lg" onClick={() => setDraftOpen(true)}>
            <FilePlus2 aria-hidden="true" />
            Draft SMMS entry
          </Button>
        </div>
      </header>

      <StageRail
        current="samprapti"
        targets={{
          purvarupa: "signals",
          nidana: "explanation",
          samprapti: "rul",
          upasaya: "action",
        }}
      />

      <div className="grid gap-4 lg:grid-cols-12 lg:gap-5">
        <div className="min-w-0 space-y-4 lg:col-span-8 lg:space-y-5">
          <Panel
            id="rul"
            eyebrow="Samprāpti · course"
            title="Remaining useful life"
            action={
              block && blockInDays !== null ? (
                <Chip tone="mono">
                  {block.window.id} · {blockWhenLabel(blockInDays)}
                </Chip>
              ) : undefined
            }
          >
            <RulBand alert={alert} />
            <div className="mt-4 border-t border-border-subtle pt-4">
              <RiskHorizon alert={alert} />
            </div>
          </Panel>

          <ExplanationCard id="explanation" alert={alert} />

          <Panel id="signals" eyebrow="Pūrvarūpa · early signs" title="Signals, 12 days">
            {data.signals.length ? (
              <div className="grid gap-3 sm:grid-cols-2">
                {data.signals.map((series) => (
                  <Sparkline key={series.key} series={series} />
                ))}
              </div>
            ) : (
              <EmptyState title="No signal history for this circuit">
                This asset has no telemetry series in the current dataset. The explanation and RUL
                above still apply.
              </EmptyState>
            )}
          </Panel>
        </div>

        <div className="min-w-0 space-y-4 lg:col-span-4 lg:space-y-5">
          <Panel eyebrow="Nidāna · cause" title="Likely failure mode">
            <p className="flex flex-wrap items-baseline gap-x-2">
              <span className="font-data text-2xl font-semibold text-text-hi">
                {alert.likelyModes[0]}
              </span>
              <span className="text-sm text-text-mid">
                {failureModes[alert.likelyModes[0] ?? "F12"]}
              </span>
            </p>
            <p className="mt-1 text-sm text-text-mid">
              Probability{" "}
              <span className="font-data font-semibold text-text-hi">
                {formatDecimal(alert.modeProbability)}
              </span>{" "}
              · conformal set{" "}
              <span className="font-data text-text-hi">{`{${alert.explanation.model.modeSet.join(", ")}}`}</span>{" "}
              at {formatDecimal(alert.modeSetCoverage)}
            </p>
            {data.modes.length > 0 && (
              <ul className="mt-4 space-y-2">
                {data.modes.map((mode) => (
                  <li key={mode.code} className="text-sm">
                    <div className="flex items-center justify-between gap-2">
                      <span className="text-text-hi">
                        <span className="font-data font-semibold">{mode.code}</span>{" "}
                        <span className="text-text-mid">{failureModes[mode.code]}</span>
                      </span>
                      <span className="font-data text-text-hi">
                        {formatDecimal(mode.probability)}
                      </span>
                    </div>
                    <div aria-hidden="true" className="mt-1 h-1 rounded-full bg-bg-inset">
                      <div
                        className={
                          mode.inSet
                            ? "h-full rounded-full bg-accent"
                            : "h-full rounded-full bg-border-strong"
                        }
                        style={{ width: `${mode.probability * 100}%` }}
                      />
                    </div>
                    {mode.excluded && (
                      <p className="mt-1 text-xs text-text-lo">Excluded: {mode.excluded}</p>
                    )}
                    {mode.inSet && <span className="sr-only">In conformal set</span>}
                  </li>
                ))}
              </ul>
            )}
          </Panel>

          {cluster && (
            <Panel
              eyebrow="Common cause"
              title={`Cluster ${cluster.id}`}
              action={
                <Link
                  to="/clusters"
                  hash={cluster.id}
                  className="inline-flex min-h-11 items-center text-xs font-semibold text-accent-text hover:underline"
                >
                  Open
                </Link>
              }
            >
              <ul className="flex flex-wrap gap-2">
                {cluster.members.map((m) => (
                  <li key={m}>
                    <AssetLink
                      assetId={m}
                      className="min-h-9 rounded-sm border border-border px-2 text-xs"
                    />
                  </li>
                ))}
              </ul>
              <dl className="mt-3 space-y-2 text-sm">
                {cluster.sharedEdges.slice(0, 2).map((edge) => (
                  <div key={edge.id}>
                    <dt className="text-xs text-text-lo">{edge.kind}</dt>
                    <dd className="font-data text-[13px] text-text-hi">{edge.id}</dd>
                  </div>
                ))}
              </dl>
              {cluster.predictedCascade && (
                <p className="mt-3 text-sm text-text-mid">
                  Predicted cascade to{" "}
                  <span className="font-data font-semibold text-text-hi">
                    {cluster.predictedCascade.assetId}
                  </span>{" "}
                  in {cluster.predictedCascade.inDays.min}–{cluster.predictedCascade.inDays.max}{" "}
                  days.
                </p>
              )}
            </Panel>
          )}

          <Panel id="action" eyebrow="Upaśaya · response" title="Recommended action">
            <p className="text-sm font-semibold text-text-hi">{action}</p>
            {block && (
              <div className="mt-2 flex flex-wrap items-center gap-2 text-sm text-text-mid">
                <span className="font-data">
                  {block.minutes} min · {block.window.id} · {formatShortDate(block.window.date)}{" "}
                  {block.window.start}–{block.window.end}
                </span>
                <BlockFitBadge
                  fit={block.fit}
                  label={blockFitText(block.fit, block.minutes, block.window.durationMin)}
                />
              </div>
            )}
            <div className="mt-3">
              <Notice
                title={blockInDays !== null && !insideP10 ? "Already outside p10" : "If deferred"}
              >
                {block && blockInDays !== null
                  ? insideP10
                    ? `RUL p10 is ${alert.rul.p10Days} days; ${block.window.id} is ${blockWhenLabel(blockInDays)}, inside the horizon. Missing it leaves ${Math.max(0, alert.rul.p10Days - blockInDays)} days of margin before p10.`
                    : `RUL p10 is ${alert.rul.p10Days} days and ${block.window.id} is ${blockWhenLabel(blockInDays)} — already past the planning horizon. Escalate, or ask for an earlier block.`
                  : `RUL p10 is ${alert.rul.p10Days} days and no published block is available this week. The planner shows a special block once one is drafted.`}
                {cluster?.predictedCascade
                  ? ` ${cluster.predictedCascade.assetId} may follow in ${cluster.predictedCascade.inDays.min}–${cluster.predictedCascade.inDays.max} days.`
                  : ""}
              </Notice>
            </div>
            <Button className="mt-4 w-full" variant="outline" onClick={() => setDraftOpen(true)}>
              <FilePlus2 aria-hidden="true" />
              Draft SMMS entry
            </Button>
          </Panel>

          <Panel eyebrow="SMMS · read-only" title="Asset record">
            {data.record ? (
              <AssetRecordList record={data.record} trust={alert.dataTrust} />
            ) : (
              <EmptyState title="Asset record unavailable">
                SMMS has no record for this asset in the demo dataset. The alert and explanation
                above still apply.
              </EmptyState>
            )}
          </Panel>
        </div>
      </div>

      <DraftSmmsDialog
        open={draftOpen}
        onOpenChange={setDraftOpen}
        alert={alert}
        action={action}
        pending={draft.isPending}
        onSave={() =>
          draft.mutate(
            { alertId: alert.id, action, blockId: block?.window.id ?? "none" },
            {
              onSuccess: (result) => {
                setDraftOpen(false);
                toast.success(`Draft ${result.id} saved`, {
                  description: "Not submitted. Waiting for SSE (Sig) review.",
                });
              },
            },
          )
        }
      />
    </div>
  );
}
