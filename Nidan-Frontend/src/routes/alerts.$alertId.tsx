import { createFileRoute, Link, useNavigate } from "@tanstack/react-router";
import { useSuspenseQuery } from "@tanstack/react-query";
import { useState } from "react";
import { ArrowUpRight, Check, Undo2 } from "lucide-react";
import { toast } from "sonner";
import { alertQuery } from "@/lib/queries";
import { useAcknowledge, useDefer, useUndefer } from "@/lib/mutations";
import { formatAge, formatShortDate } from "@/lib/formatters";
import { failureModes } from "@/data/fixtures";
import { BlockFitBadge, Chip, DataTrust, LevelBadge, Notice } from "@/components/nidan/primitives";
import { ExplanationCard, RiskHorizon, RulBand } from "@/components/nidan/charts";
import { DeferDialog, SheetDialog, WhyThisOrder } from "@/components/nidan/domain";
import { Button } from "@/components/ui/button";
import { blockFitText } from "@/lib/policy";

export const Route = createFileRoute("/alerts/$alertId")({
  loader: ({ context, params }) => context.queryClient.ensureQueryData(alertQuery(params.alertId)),
  head: ({ loaderData }) => ({
    meta: [
      {
        title: loaderData
          ? `Triage ${loaderData.assetId} · ${loaderData.level} — NIDAN`
          : "Alert triage — NIDAN",
      },
      {
        name: "description",
        content: loaderData
          ? `Triage of ${loaderData.assetId} (${loaderData.assetName}): calibrated risk, remaining useful life, explanation and block fit.`
          : "Alert triage drawer.",
      },
      {
        property: "og:title",
        content: loaderData ? `NIDAN triage · ${loaderData.assetId}` : "NIDAN alert triage",
      },
      {
        property: "og:description",
        content: "One alert, its explanation, and the options an SSE has.",
      },
      { property: "og:type", content: "website" },
      { name: "twitter:card", content: "summary_large_image" },
    ],
  }),
  component: TriageDrawer,
  notFoundComponent: () => null,
});

function TriageDrawer() {
  const { alertId } = Route.useParams();
  const { data: alert } = useSuspenseQuery(alertQuery(alertId));
  const navigate = useNavigate();
  const [deferOpen, setDeferOpen] = useState(false);
  const ack = useAcknowledge();
  const defer = useDefer();
  const undefer = useUndefer();

  const close = () => {
    void navigate({ to: "/alerts", search: (prev) => prev });
    window.setTimeout(
      () =>
        document.querySelector<HTMLElement>(`[data-row-id="${alert.id}"]:not([hidden])`)?.focus(),
      50,
    );
  };

  const block = alert.block;
  return (
    <>
      <SheetDialog
        open
        side="right"
        onOpenChange={(open) => {
          if (!open) close();
        }}
        title={`${alert.assetId}`}
        description={`${alert.assetName} · policy rank #${alert.policyRank} · ${formatAge(alert.ageMinutes)} old`}
        footer={
          <>
            <Link
              to="/assets/$assetId"
              params={{ assetId: alert.assetId }}
              className="mr-auto inline-flex min-h-11 items-center gap-1 text-sm font-semibold text-accent-text underline-offset-4 hover:underline"
            >
              Circuit detail
              <ArrowUpRight className="h-4 w-4" aria-hidden="true" />
            </Link>
            <Link
              to="/review"
              search={{ alert: alert.id }}
              className="inline-flex min-h-11 items-center gap-1 text-sm font-semibold text-accent-text underline-offset-4 hover:underline"
            >
              Review evidence
              <ArrowUpRight className="h-4 w-4" aria-hidden="true" />
            </Link>
            {alert.deferral ? (
              <Button
                variant="outline"
                onClick={() => {
                  undefer.mutate([alert.id]);
                  toast.success(`${alert.assetId} returned to triage`);
                }}
              >
                <Undo2 aria-hidden="true" />
                Return to triage
              </Button>
            ) : (
              <Button variant="outline" onClick={() => setDeferOpen(true)}>
                Defer…
              </Button>
            )}
            {alert.acknowledged ? (
              <Button
                variant="secondary"
                onClick={() => ack.mutate({ ids: [alert.id], undo: true })}
              >
                <Undo2 aria-hidden="true" />
                Undo acknowledge
              </Button>
            ) : (
              <Button
                onClick={() => {
                  ack.mutate({ ids: [alert.id] });
                  toast.success(`${alert.assetId} acknowledged`, {
                    description: "Seen, not resolved. It stays open.",
                    action: {
                      label: "Undo",
                      onClick: () => ack.mutate({ ids: [alert.id], undo: true }),
                    },
                  });
                }}
              >
                <Check aria-hidden="true" />
                Acknowledge
              </Button>
            )}
          </>
        }
      >
        <div className="space-y-5">
          <div className="flex flex-wrap items-center gap-2">
            <LevelBadge level={alert.level} />
            <Chip tone="mono">
              {alert.likelyModes.join(", ")} · {failureModes[alert.likelyModes[0] ?? "F12"]}
            </Chip>
            <DataTrust score={alert.dataTrust.score} flags={alert.dataTrust.flags} />
            {alert.clusterId && <Chip tone="mono">{alert.clusterId}</Chip>}
            {alert.acknowledged && (
              <Chip tone="accent">
                <Check className="h-3.5 w-3.5" aria-hidden="true" />
                Acknowledged · still open
              </Chip>
            )}
            {alert.deferral && (
              <Chip tone="warning">Deferred to {formatShortDate(alert.deferral.reviewDate)}</Chip>
            )}
          </div>
          {alert.deferral && <Notice title="Deferral reason">{alert.deferral.reason}</Notice>}
          <p className="text-sm leading-6 text-text-mid">
            Held at <strong className="text-text-hi">{alert.level}</strong> for {alert.persistence}{" "}
            evaluations. {alert.explanation.physics.headline}.
          </p>
          <RiskHorizon alert={alert} />
          <section
            aria-labelledby="drawer-rul"
            className="rounded-md border border-border p-3 sm:p-4"
          >
            <h3 id="drawer-rul" className="mb-3 text-sm font-semibold text-text-hi">
              Remaining useful life
            </h3>
            <RulBand alert={alert} />
          </section>
          {block && (
            <div className="flex flex-wrap items-center justify-between gap-2 rounded-md border border-border p-3">
              <div>
                <p className="text-xs text-text-lo">Rolling Block</p>
                <p className="font-data text-sm font-semibold text-text-hi">
                  {block.window.id} · {formatShortDate(block.window.date)} {block.window.start}–
                  {block.window.end}
                </p>
              </div>
              <BlockFitBadge
                fit={block.fit}
                label={blockFitText(block.fit, block.minutes, block.window.durationMin)}
              />
            </div>
          )}
          <ExplanationCard alert={alert} />
          <WhyThisOrder alert={alert} />
          {alert.level === "critical" && (
            <Notice tone="critical" title="Critical">
              This alert can be deferred only on its own, with a reason and a review date. It never
              arrives as a toast and never pulses.
            </Notice>
          )}
        </div>
      </SheetDialog>
      <DeferDialog
        open={deferOpen}
        onOpenChange={setDeferOpen}
        alerts={[alert]}
        onConfirm={(request) => {
          defer.mutate({ ids: [alert.id], request });
          setDeferOpen(false);
          toast.success(`${alert.assetId} deferred until ${request.reviewDate}`, {
            action: { label: "Undo", onClick: () => undefer.mutate([alert.id]) },
          });
        }}
      />
    </>
  );
}
