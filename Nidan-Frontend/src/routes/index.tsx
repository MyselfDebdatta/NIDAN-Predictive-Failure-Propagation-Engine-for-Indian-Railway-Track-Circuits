import { createFileRoute, Link, useNavigate } from "@tanstack/react-router";
import { useQueryClient, useSuspenseQuery } from "@tanstack/react-query";
import { Download, RefreshCw } from "lucide-react";
import { toast } from "sonner";
import { alertsQuery, blocksQuery, clustersQuery, kpisQuery, nidanKeys } from "@/lib/queries";
import { byPolicyRank } from "@/lib/policy";
import { formatRisk, formatShortDate } from "@/lib/formatters";
import { snapshot } from "@/data/fixtures";
import {
  Chip,
  KpiTile,
  PageHeading,
  PageSkeleton,
  Panel,
  StateShapeLegend,
  AssetLink,
} from "@/components/nidan/primitives";
import { PropagationMap, SignalSpine } from "@/components/nidan/charts";
import { QueueTable, RollingBlockStrip } from "@/components/nidan/domain";
import { Button } from "@/components/ui/button";

export const Route = createFileRoute("/")({
  head: () => ({
    meta: [
      { title: "Command centre · Adra division, next 7 days — NIDAN" },
      {
        name: "description",
        content:
          "Ranked, explainable track-circuit advisories for Adra division: signal spine, propagation, common cause and Rolling Block fit.",
      },
      { property: "og:title", content: "NIDAN command centre — Adra division, next 7 days" },
      {
        property: "og:description",
        content: "What needs attention across Adra division this week, and in what order.",
      },
      { property: "og:type", content: "website" },
      { name: "twitter:card", content: "summary_large_image" },
    ],
  }),
  loader: ({ context }) =>
    Promise.all([
      context.queryClient.ensureQueryData(alertsQuery),
      context.queryClient.ensureQueryData(kpisQuery),
      context.queryClient.ensureQueryData(clustersQuery),
      context.queryClient.ensureQueryData(blocksQuery),
    ]),
  pendingComponent: PageSkeleton,
  component: CommandCentre,
});

function CommandCentre() {
  const { data: alerts } = useSuspenseQuery(alertsQuery);
  const { data: kpis } = useSuspenseQuery(kpisQuery);
  const { data: clusters } = useSuspenseQuery(clustersQuery);
  const { data: blocks } = useSuspenseQuery(blocksQuery);
  const queryClient = useQueryClient();
  const navigate = useNavigate();
  const ranked = byPolicyRank(alerts.filter((a) => !a.deferral));
  const cluster = clusters[0];

  return (
    <div className="space-y-5 lg:space-y-6">
      <PageHeading
        eyebrow="SER / ADRA / ADRA YARD"
        title="Adra division, next 7 days"
        titleHi="आद्रा मंडल, अगले 7 दिन"
        action={
          <>
            <Button
              variant="outline"
              onClick={() =>
                toast.success("Export pack prepared", {
                  description: "PDF + CSV of this snapshot, demo data.",
                })
              }
            >
              <Download aria-hidden="true" />
              Export pack
            </Button>
            <Button
              variant="ghost"
              onClick={() => {
                void queryClient.invalidateQueries({ queryKey: nidanKeys.all });
                toast("New snapshot requested", {
                  description: "Risk is never recomputed in the browser.",
                });
              }}
            >
              <RefreshCw aria-hidden="true" />
              Refresh
            </Button>
          </>
        }
      >
        <Chip tone="mono">Scope ADRA Yard</Chip>
        <Chip>Horizon 7 days</Chip>
        <Chip tone="mono">Snapshot {snapshot.label}</Chip>
      </PageHeading>

      <div className="grid grid-cols-2 gap-3 lg:grid-cols-4 lg:gap-4">
        <KpiTile
          label="Open alerts"
          value={String(kpis.openAlerts.value)}
          delta={kpis.openAlerts.delta}
          note="In scope, all levels"
        />
        <KpiTile
          label="Critical this shift"
          value={String(kpis.criticalShift.value)}
          delta={kpis.criticalShift.delta}
          note="Needs a special block"
          tone="critical"
          glyph="critical"
        />
        <KpiTile
          label="Cluster-adjusted work"
          value={String(kpis.clusterAdjusted.value)}
          delta={kpis.clusterAdjusted.delta}
          note="Decisions after folding causes"
          tone="watch"
        />
        <KpiTile
          label="Rolling Block fit"
          value={formatRisk(kpis.blockFit.value)}
          delta={kpis.blockFit.delta}
          note="Jobs inside published windows"
          tone="watch"
        />
      </div>

      <div className="grid gap-4 lg:grid-cols-12 lg:gap-5">
        <Panel
          className="lg:col-span-5"
          eyebrow="Pūrvarūpa · early signs"
          title="Section spine"
          action={
            <Link
              to="/alerts"
              className="inline-flex min-h-11 items-center text-xs font-semibold text-accent-text hover:underline"
            >
              All {alerts.length}
            </Link>
          }
        >
          <SignalSpine alerts={ranked} />
          <div className="mt-3 border-t border-border-subtle pt-3">
            <StateShapeLegend />
          </div>
        </Panel>
        <Panel
          className="lg:col-span-7"
          eyebrow="Samprāpti · course"
          title="Propagation map"
          action={<Chip tone="mono">c-9917</Chip>}
        >
          <PropagationMap />
        </Panel>
      </div>

      {cluster && (
        <div className="grid gap-4 lg:grid-cols-12 lg:gap-5">
          <Panel
            className="lg:col-span-5"
            eyebrow="Common cause"
            title={`${cluster.id} · ${cluster.title}`}
            action={
              <Link
                to="/clusters"
                className="inline-flex min-h-11 items-center text-xs font-semibold text-accent-text hover:underline"
              >
                Open cluster
              </Link>
            }
          >
            <p className="text-sm leading-6 text-text-mid">
              <strong className="font-data text-text-hi">{cluster.alertsFolded}</strong> alerts fold
              into <strong className="font-data text-text-hi">{cluster.decisions.length}</strong>{" "}
              decisions. Estimated{" "}
              <strong className="font-data text-text-hi">{cluster.savedBlockHours}</strong>{" "}
              block-hours saved.
            </p>
            <ul className="mt-3 flex flex-wrap gap-2">
              {cluster.members.map((member) => (
                <li key={member}>
                  <AssetLink
                    assetId={member}
                    className="min-h-9 rounded-sm border border-border px-2 text-xs"
                  />
                </li>
              ))}
            </ul>
          </Panel>
          <Panel
            className="lg:col-span-7"
            eyebrow="Shared evidence"
            title="Why these circuits move together"
          >
            <dl className="grid gap-3 sm:grid-cols-3">
              {cluster.sharedEdges.map((edge) => (
                <div
                  key={edge.id}
                  className="min-w-0 rounded-sm border border-border-subtle bg-bg-raised p-3"
                >
                  <dt className="text-xs text-text-lo">{edge.kind}</dt>
                  <dd className="mt-1 break-words font-data text-[13px] font-semibold text-text-hi">
                    {edge.id}
                  </dd>
                  <dd className="mt-1 text-xs leading-5 text-text-mid">{edge.note}</dd>
                </div>
              ))}
            </dl>
            {cluster.predictedCascade && (
              <p className="mt-3 text-sm text-text-mid">
                Predicted cascade to{" "}
                <span className="font-data font-semibold text-text-hi">
                  {cluster.predictedCascade.assetId}
                </span>{" "}
                in {cluster.predictedCascade.inDays.min}–{cluster.predictedCascade.inDays.max} days
                if the drain is not cleared.
              </p>
            )}
          </Panel>
        </div>
      )}

      <Panel
        eyebrow="Ordered by policy rank"
        title="Priority queue"
        action={
          <Link
            to="/alerts"
            className="inline-flex min-h-11 items-center text-xs font-semibold text-accent-text hover:underline"
          >
            Open alert queue
          </Link>
        }
      >
        <QueueTable
          variant="compact"
          caption="Priority queue, top 8 alerts"
          alerts={ranked.slice(0, 8)}
          onOpen={(alert) => navigate({ to: "/alerts/$alertId", params: { alertId: alert.id } })}
        />
      </Panel>

      <Panel
        eyebrow="Upaśaya · response"
        title={`Rolling Block · week ${snapshot.week}`}
        action={
          <Link
            to="/blocks"
            className="inline-flex min-h-11 items-center text-xs font-semibold text-accent-text hover:underline"
          >
            Open planner
          </Link>
        }
      >
        <p className="mb-3 text-sm text-text-mid">
          Work fitted into already-published windows. RB-28 on {formatShortDate("2026-07-16")}{" "}
          02:10–03:40 absorbs the 12T fix.
        </p>
        <RollingBlockStrip windows={blocks.windows} jobs={blocks.jobs} highlight="RB-28" />
      </Panel>
    </div>
  );
}
