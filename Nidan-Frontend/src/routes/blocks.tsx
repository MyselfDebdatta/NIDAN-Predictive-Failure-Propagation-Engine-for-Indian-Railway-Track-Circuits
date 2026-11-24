import { createFileRoute } from "@tanstack/react-router";
import { useSuspenseQuery } from "@tanstack/react-query";
import { useState } from "react";
import { FilePlus2 } from "lucide-react";
import { toast } from "sonner";
import { blocksQuery } from "@/lib/queries";
import { snapshot, type BlockJob } from "@/data/fixtures";
import { formatShortDate, formatWeekday } from "@/lib/formatters";
import {
  BlockFitBadge,
  KpiTile,
  Notice,
  PageHeading,
  PageSkeleton,
  Panel,
} from "@/components/nidan/primitives";
import { BlockFitRow, RollingBlockStrip, SheetDialog } from "@/components/nidan/domain";
import { Button } from "@/components/ui/button";

export const Route = createFileRoute("/blocks")({
  head: () => ({
    meta: [
      { title: `Rolling Block planner · week ${snapshot.week} — NIDAN` },
      {
        name: "description",
        content:
          "Which advisory work fits the Rolling Block windows already published for Adra division this week.",
      },
      { property: "og:title", content: "NIDAN Rolling Block planner" },
      { property: "og:description", content: "What work fits the blocks already published?" },
      { property: "og:type", content: "website" },
      { name: "twitter:card", content: "summary_large_image" },
    ],
  }),
  loader: ({ context }) => context.queryClient.ensureQueryData(blocksQuery),
  pendingComponent: PageSkeleton,
  component: Blocks,
});

function Blocks() {
  const { data } = useSuspenseQuery(blocksQuery);
  const [draftJob, setDraftJob] = useState<BlockJob | null>(null);
  const [confirmed, setConfirmed] = useState(false);
  const fitted = data.jobs.filter((j) => j.blockId);
  const fits = data.jobs.filter((j) => j.fit === "fits").length;
  const extendsCount = data.jobs.filter((j) => j.fit === "extends").length;
  const unplanned = data.jobs.filter((j) => !j.blockId);

  return (
    <div className="space-y-5 lg:space-y-6">
      <PageHeading
        eyebrow="SER / ADRA · Upaśaya"
        title={`Rolling Block · week ${snapshot.week}`}
        titleHi={`रोलिंग ब्लॉक · सप्ताह ${snapshot.week}`}
        subtitle="The best intervention is the one that needs no special block. Windows below are already published; NIDAN only fits work into them."
      />
      <div className="grid grid-cols-2 gap-3 lg:grid-cols-4 lg:gap-4">
        <KpiTile
          label="Published windows"
          value={String(data.windows.length)}
          delta="14–20 Jul"
          note="90 min each, Adra Yard"
        />
        <KpiTile
          label="Jobs that fit"
          value={String(fits)}
          delta="no extension"
          note="Inside a published window"
          tone="watch"
        />
        <KpiTile
          label="Need extension"
          value={String(extendsCount)}
          delta="+15 to +20 min"
          note="Needs SSE agreement"
          tone="warning"
          glyph="warning"
        />
        <KpiTile
          label="Not in a block"
          value={String(unplanned.length)}
          delta="1 special"
          note="Special block or none published"
          tone="critical"
          glyph="critical"
        />
      </div>

      <Panel title="Seven-day strip" eyebrow="Published windows">
        <RollingBlockStrip windows={data.windows} jobs={data.jobs} highlight="RB-28" />
      </Panel>

      <div className="grid gap-4 lg:grid-cols-12 lg:gap-5">
        <Panel className="lg:col-span-7" title="Fitted work" eyebrow={`${fitted.length} jobs`}>
          <ul>
            {data.windows.flatMap((w) =>
              data.jobs
                .filter((j) => j.blockId === w.id)
                .map((job) => <BlockFitRow key={job.id} job={job} window={w} />),
            )}
          </ul>
        </Panel>
        <Panel
          className="lg:col-span-5"
          title="Needs a decision"
          eyebrow="No published window fits"
        >
          <ul className="space-y-3">
            {unplanned.map((job) => (
              <li key={job.id} className="rounded-sm border border-border p-3">
                <div className="flex flex-wrap items-center justify-between gap-2">
                  <span className="font-data text-sm font-semibold text-text-hi">
                    {job.assets.join(", ")}
                  </span>
                  <BlockFitBadge fit={job.fit} />
                </div>
                <p className="mt-1 text-sm text-text-mid">
                  {job.title} · {job.durationMin} min · {job.crew}
                </p>
                {job.fit === "special" && (
                  <Button
                    variant="outline"
                    className="mt-3"
                    onClick={() => {
                      setConfirmed(false);
                      setDraftJob(job);
                    }}
                  >
                    <FilePlus2 aria-hidden="true" />
                    Prepare block draft
                  </Button>
                )}
                {job.fit === "none" && (
                  <p className="mt-2 text-xs text-text-lo">
                    KGP has no published block this week. Shown for awareness; out of ADRA scope.
                  </p>
                )}
              </li>
            ))}
          </ul>
        </Panel>
      </div>

      <SheetDialog
        open={!!draftJob}
        onOpenChange={(o) => {
          if (!o) setDraftJob(null);
        }}
        title="Special block draft"
        description="Pre-filled from the alert. It is not a request until SSE (Sig) confirms and the operating department publishes it."
        footer={
          <>
            <Button variant="outline" onClick={() => setDraftJob(null)}>
              Cancel
            </Button>
            <Button
              disabled={!confirmed}
              onClick={() => {
                toast.success("Block draft saved", {
                  description: "Awaiting SSE (Sig) confirmation. Nothing has been requested.",
                });
                setDraftJob(null);
              }}
            >
              Save draft
            </Button>
          </>
        }
      >
        {draftJob && (
          <div className="space-y-4">
            <dl className="divide-y divide-border-subtle rounded-sm border border-border text-sm">
              {[
                ["Assets", draftJob.assets.join(", ")],
                ["Work", draftJob.title],
                ["Duration", `${draftJob.durationMin} min`],
                [
                  "Earliest",
                  `${formatWeekday("2026-07-14")} ${formatShortDate("2026-07-14")}, after RB-26`,
                ],
                ["Crew", draftJob.crew],
              ].map(([k, v]) => (
                <div key={k} className="grid gap-1 px-3 py-2.5 sm:grid-cols-[120px_minmax(0,1fr)]">
                  <dt className="text-xs text-text-lo">{k}</dt>
                  <dd className="text-text-hi">{v}</dd>
                </div>
              ))}
            </dl>
            <Notice tone="critical" title="Why special">
              The Critical F9 hypothesis on ADRA/TC/07T needs 120 min; the next published window is
              90 min.
            </Notice>
            <label className="flex min-h-11 items-start gap-3 text-sm text-text-hi">
              <input
                type="checkbox"
                checked={confirmed}
                onChange={(e) => setConfirmed(e.target.checked)}
                className="mt-1 h-4 w-4 accent-[var(--accent)]"
              />
              I understand this is a draft for SSE (Sig) confirmation and does not request or
              publish a block.
            </label>
          </div>
        )}
      </SheetDialog>
    </div>
  );
}
