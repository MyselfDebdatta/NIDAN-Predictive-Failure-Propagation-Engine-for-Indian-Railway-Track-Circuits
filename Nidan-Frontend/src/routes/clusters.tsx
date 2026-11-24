import { createFileRoute } from "@tanstack/react-router";
import { useSuspenseQuery } from "@tanstack/react-query";
import { alertsQuery, clustersQuery } from "@/lib/queries";
import { formatRisk, formatRul } from "@/lib/formatters";
import {
  AssetLink,
  Chip,
  KpiTile,
  LevelBadge,
  PageHeading,
  PageSkeleton,
  Panel,
} from "@/components/nidan/primitives";
import { PropagationMap } from "@/components/nidan/charts";

export const Route = createFileRoute("/clusters")({
  head: () => ({
    meta: [
      { title: "Common-cause clusters — NIDAN" },
      {
        name: "description",
        content:
          "Physical causes that explain several track-circuit alerts at once, folded into fewer field decisions.",
      },
      { property: "og:title", content: "NIDAN common-cause clusters" },
      { property: "og:description", content: "Which physical causes explain multiple alerts?" },
      { property: "og:type", content: "website" },
      { name: "twitter:card", content: "summary_large_image" },
    ],
  }),
  loader: ({ context }) =>
    Promise.all([
      context.queryClient.ensureQueryData(clustersQuery),
      context.queryClient.ensureQueryData(alertsQuery),
    ]),
  pendingComponent: PageSkeleton,
  component: Clusters,
});

function Clusters() {
  const { data: clusters } = useSuspenseQuery(clustersQuery);
  const { data: alerts } = useSuspenseQuery(alertsQuery);
  const open = clusters.filter((c) => c.state === "open");
  const folded = clusters.reduce((sum, c) => sum + c.alertsFolded, 0);
  const decisions = clusters.reduce((sum, c) => sum + c.decisions.length, 0);
  const hours = clusters.reduce((sum, c) => sum + c.savedBlockHours, 0);

  return (
    <div className="space-y-5 lg:space-y-6">
      <PageHeading
        eyebrow="SER / ADRA · common cause"
        title="Common-cause clusters"
        titleHi="साझा कारण क्लस्टर"
        subtitle="One physical cause, several alerts. Fold them into fewer decisions - membership comes from the propagation model and shared assets, never from the browser."
      />
      <div className="grid grid-cols-2 gap-3 lg:grid-cols-4 lg:gap-4">
        <KpiTile
          label="Open clusters"
          value={String(open.length)}
          delta={`${clusters.length - open.length} monitoring`}
          note="With a confirmed shared edge"
          tone="watch"
        />
        <KpiTile
          label="Alerts folded"
          value={String(folded)}
          delta={`→ ${decisions} decisions`}
          note="Across all clusters"
        />
        <KpiTile
          label="Block-hours saved"
          value={hours.toFixed(1)}
          delta="estimate"
          note="Against one job per alert"
          tone="watch"
        />
        <KpiTile
          label="Predicted cascades"
          value="1"
          delta="21T · 6–11 d"
          note="Not observed yet"
          tone="warning"
          glyph="watch"
        />
      </div>

      {clusters.map((cluster) => {
        const members = alerts.filter((a) => cluster.members.includes(a.assetId));
        return (
          <section
            key={cluster.id}
            id={cluster.id}
            aria-labelledby={`${cluster.id}-title`}
            className="scroll-mt-24 space-y-4"
          >
            <div className="flex flex-wrap items-center gap-2">
              <h2
                id={`${cluster.id}-title`}
                className="font-display text-xl font-semibold text-text-hi"
              >
                <span className="font-data">{cluster.id}</span> · {cluster.title}
              </h2>
              <Chip tone={cluster.state === "open" ? "accent" : "neutral"}>
                {cluster.state === "open" ? "Open" : "Monitoring"}
              </Chip>
            </div>
            <p className="max-w-3xl text-sm leading-6 text-text-mid">{cluster.summary}</p>
            <div className="grid gap-4 lg:grid-cols-12 lg:gap-5">
              <Panel
                className="lg:col-span-7"
                title="Members"
                eyebrow={`${members.length} track circuits`}
              >
                <ul className="divide-y divide-border-subtle">
                  {members.map((alert) => (
                    <li
                      key={alert.id}
                      className="flex flex-wrap items-center justify-between gap-x-4 gap-y-1 py-2"
                    >
                      <span className="flex min-w-0 items-center gap-3">
                        <LevelBadge level={alert.level} />
                        <AssetLink assetId={alert.assetId} />
                      </span>
                      <span className="flex gap-4 font-data text-sm text-text-mid">
                        <span>7 d {formatRisk(alert.risk.h7d)}</span>
                        <span>p10 {formatRul(alert.rul.p10Days)}</span>
                        <span>{alert.likelyModes.join(", ")}</span>
                      </span>
                    </li>
                  ))}
                </ul>
                {cluster.predictedCascade && (
                  <p className="mt-3 rounded-sm border border-dashed border-border-strong p-3 text-sm text-text-mid">
                    Predicted, not observed:{" "}
                    <span className="font-data font-semibold text-text-hi">
                      {cluster.predictedCascade.assetId}
                    </span>{" "}
                    in {cluster.predictedCascade.inDays.min}–{cluster.predictedCascade.inDays.max}{" "}
                    days if the shared cause is not removed.
                  </p>
                )}
              </Panel>
              <Panel
                className="lg:col-span-5"
                title="Shared edges"
                eyebrow="Why they move together"
              >
                <dl className="space-y-3">
                  {cluster.sharedEdges.map((edge) => (
                    <div
                      key={edge.id}
                      className="rounded-sm border border-border-subtle bg-bg-raised p-3"
                    >
                      <dt className="text-xs text-text-lo">{edge.kind}</dt>
                      <dd className="mt-0.5 break-words font-data text-[13px] font-semibold text-text-hi">
                        {edge.id}
                      </dd>
                      <dd className="mt-1 text-xs text-text-mid">{edge.note}</dd>
                    </div>
                  ))}
                </dl>
              </Panel>
              {cluster.id === "c-9917" && (
                <Panel className="lg:col-span-7" title="Propagation" eyebrow="Schematic">
                  <PropagationMap />
                </Panel>
              )}
              <Panel
                className={cluster.id === "c-9917" ? "lg:col-span-5" : "lg:col-span-12"}
                title="Folded decisions"
                eyebrow={`${cluster.alertsFolded} alerts → ${cluster.decisions.length} decisions · ${cluster.savedBlockHours} block-h saved`}
              >
                <ol className="space-y-2">
                  {cluster.decisions.map((decision, i) => (
                    <li
                      key={decision.title}
                      className="flex gap-3 rounded-sm border border-border-subtle p-3"
                    >
                      <span className="grid h-6 w-6 shrink-0 place-items-center rounded-full border border-border-strong font-data text-xs text-text-mid">
                        {i + 1}
                      </span>
                      <span className="min-w-0">
                        <span className="block text-sm font-semibold text-text-hi">
                          {decision.title}
                        </span>
                        <span className="block font-data text-xs text-text-lo">
                          {decision.blockId ?? "No published block"}
                        </span>
                      </span>
                    </li>
                  ))}
                </ol>
              </Panel>
            </div>
          </section>
        );
      })}
    </div>
  );
}
