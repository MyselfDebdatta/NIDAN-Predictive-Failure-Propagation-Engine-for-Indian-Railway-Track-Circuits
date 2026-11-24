import { createFileRoute } from "@tanstack/react-router";
import { useSuspenseQuery } from "@tanstack/react-query";
import { useState } from "react";
import { Check, X } from "lucide-react";
import { modelsQuery } from "@/lib/queries";
import { failureModes } from "@/data/fixtures";
import { formatCount, formatDecimal, formatRisk } from "@/lib/formatters";
import {
  Chip,
  KpiTile,
  LevelBadge,
  LevelGlyph,
  Notice,
  PageHeading,
  PageSkeleton,
  Panel,
} from "@/components/nidan/primitives";
import { ReliabilityDiagram } from "@/components/nidan/charts";
import { cn } from "@/lib/utils";

export const Route = createFileRoute("/models")({
  head: () => ({
    meta: [
      { title: "Model health & trust — NIDAN" },
      {
        name: "description",
        content:
          "Calibration, conformal coverage, drift, data trust and promotion gates behind every NIDAN score — evidence for a review, not the review.",
      },
      { property: "og:title", content: "NIDAN model health & trust" },
      { property: "og:description", content: "Can I trust the scores I am acting on?" },
      { property: "og:type", content: "website" },
      { name: "twitter:card", content: "summary_large_image" },
    ],
  }),
  loader: ({ context }) => context.queryClient.ensureQueryData(modelsQuery),
  pendingComponent: PageSkeleton,
  component: ModelHealth,
});

function ModelHealth() {
  const { data } = useSuspenseQuery(modelsQuery);
  const [policyOpen, setPolicyOpen] = useState<string | null>(null);
  const amber = data.drift.filter((d) => d.state !== "nominal");

  return (
    <div className="space-y-5 lg:space-y-6">
      <PageHeading
        eyebrow="Assure · registry"
        title="Model health & trust"
        titleHi="मॉडल स्थिति और विश्वास"
        subtitle="A static snapshot with a stated window. This page is evidence for a review, not the review: promotion, rollback and retraining are governed in the MLOps plane."
      >
        <Chip tone="mono">As of {data.asOf}</Chip>
        <Chip>{data.window}</Chip>
      </PageHeading>

      <div className="grid grid-cols-2 gap-3 lg:grid-cols-4 lg:gap-4">
        <KpiTile
          label="ECE"
          value={formatDecimal(data.ece, 3)}
          delta={`${data.eceBins} bins`}
          note="Expected calibration error"
          tone="watch"
        />
        <KpiTile
          label="Conformal coverage"
          value={formatDecimal(data.coverage, 3)}
          delta="target 0.90"
          note={`${formatCount(data.heldOutN)} held-out outcomes`}
          tone="watch"
        />
        <KpiTile
          label="Registry"
          value={`${data.activeModels} active`}
          delta="0 in shadow"
          note="All gates signed"
        />
        <KpiTile
          label="Drift monitors"
          value={`${data.driftAmber} amber`}
          delta={amber[0]?.name ?? "none"}
          note="Monitor, not a verdict"
          tone="warning"
          glyph="warning"
        />
      </div>

      <section aria-labelledby="registry-title" className="panel-surface">
        <h2
          id="registry-title"
          className="border-b border-border-subtle px-4 py-3 text-[15px] font-semibold text-text-hi sm:px-5"
        >
          Registry
        </h2>
        <ul className="grid divide-y divide-border-subtle sm:grid-cols-2 sm:divide-y-0 lg:grid-cols-5">
          {data.models.map((m) => (
            <li
              key={m.name}
              className="min-w-0 border-border-subtle p-4 sm:border-b lg:border-b-0 lg:border-r lg:last:border-r-0"
            >
              <p className="text-sm font-semibold text-text-hi">{m.name}</p>
              <p className="mt-0.5 font-data text-lg font-semibold text-accent-text">{m.version}</p>
              <p className="mt-1 text-xs text-text-lo">Trained {m.trained}</p>
              <p className="text-xs text-text-lo">Data {m.window}</p>
              <p className="text-xs text-text-lo">
                {m.owner} · {m.state}
              </p>
            </li>
          ))}
        </ul>
      </section>

      <div className="grid gap-4 lg:grid-cols-12 lg:gap-5">
        <Panel
          className="lg:col-span-5"
          eyebrow={`${data.eceBins} bins · ${data.window.split(" · ")[0]}`}
          title="Reliability diagram"
        >
          <ReliabilityDiagram bins={data.reliability} />
        </Panel>
        <Panel
          className="lg:col-span-7"
          eyebrow="Predicted vs observed"
          title="Calibration by level"
        >
          <div className="overflow-x-auto">
            <table className="w-full min-w-[420px] text-left text-sm">
              <thead>
                <tr className="border-b border-border text-xs text-text-lo">
                  <th scope="col" className="py-2 font-medium">
                    Level
                  </th>
                  <th scope="col" className="py-2 text-right font-medium">
                    Predicted
                  </th>
                  <th scope="col" className="py-2 text-right font-medium">
                    Observed
                  </th>
                  <th scope="col" className="py-2 text-right font-medium">
                    n
                  </th>
                  <th scope="col" className="py-2 pl-4 font-medium">
                    Lead time
                  </th>
                </tr>
              </thead>
              <tbody>
                {data.byLevel.map((row) => (
                  <tr key={row.level} className="border-b border-border-subtle">
                    <th scope="row" className="py-2 font-normal">
                      <LevelBadge level={row.level} />
                    </th>
                    <td className="py-2 text-right font-data text-text-hi">
                      {formatRisk(row.predicted)}
                    </td>
                    <td className="py-2 text-right font-data text-text-hi">
                      {formatRisk(row.observed)}
                    </td>
                    <td className="py-2 text-right font-data text-text-mid">
                      {formatCount(row.n)}
                    </td>
                    <td className="py-2 pl-4 text-text-mid">{row.leadTime}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          <div className="mt-4">
            <Notice tone="neutral" title="Deliberate conservatism">
              The Critical band over-predicts on purpose (56% predicted, 47% observed): a missed
              wrong-side failure costs far more than an extra inspection. This is policy, not
              miscalibration.
            </Notice>
          </div>
        </Panel>

        <Panel
          className="lg:col-span-7"
          eyebrow="Held-out · F1–F6"
          title="Performance by failure mode"
        >
          <ul className="space-y-3">
            {data.byMode.map((row) => {
              const weak = row.recall < 0.65;
              return (
                <li
                  key={row.code}
                  className="grid gap-1.5 sm:grid-cols-[minmax(0,220px)_minmax(0,1fr)_auto] sm:items-center sm:gap-4"
                >
                  <span className="min-w-0 text-sm text-text-hi">
                    <span className="font-data font-semibold">{row.code}</span>{" "}
                    <span className="text-text-mid">{failureModes[row.code]}</span>
                  </span>
                  <span aria-hidden="true" className="grid gap-1">
                    <span className="h-1.5 rounded-full bg-bg-inset">
                      <span
                        className="block h-full rounded-full bg-accent"
                        style={{ width: `${row.precision * 100}%` }}
                      />
                    </span>
                    <span className="h-1.5 rounded-full bg-bg-inset">
                      <span
                        className={cn(
                          "block h-full rounded-full",
                          weak ? "bg-warning" : "bg-text-lo",
                        )}
                        style={{ width: `${row.recall * 100}%` }}
                      />
                    </span>
                  </span>
                  <span className="font-data text-xs text-text-mid">
                    P {formatDecimal(row.precision)} · R {formatDecimal(row.recall)} · n{" "}
                    {formatCount(row.n)}
                    {weak && (
                      <span className="ml-1 font-sans font-semibold text-warning">weak recall</span>
                    )}
                  </span>
                </li>
              );
            })}
          </ul>
          <p className="mt-3 text-xs text-text-lo">
            Top bar precision, bottom bar recall. Weak modes are shown, never hidden.
          </p>
        </Panel>

        <Panel className="lg:col-span-5" eyebrow="PSI per feature group" title="Drift monitors">
          <ul className="space-y-3">
            {data.drift.map((d) => (
              <li key={d.name} className="text-sm">
                <div className="flex items-center justify-between gap-2">
                  <span className="flex items-center gap-2 text-text-hi">
                    <LevelGlyph level={d.state} />
                    {d.name}
                  </span>
                  <span className="font-data text-text-hi">
                    {formatDecimal(d.psi)}{" "}
                    <span className="text-text-lo">/ {formatDecimal(d.threshold)}</span>
                  </span>
                </div>
                <div aria-hidden="true" className="relative mt-1.5 h-1.5 rounded-full bg-bg-inset">
                  <span
                    className={cn(
                      "absolute inset-y-0 left-0 rounded-full",
                      d.state === "nominal" ? "bg-accent" : "bg-warning",
                    )}
                    style={{ width: `${(d.psi / 0.3) * 100}%` }}
                  />
                  <span
                    className="absolute -inset-y-1 w-0.5 bg-text-mid"
                    style={{ left: `${(d.threshold / 0.3) * 100}%` }}
                  />
                </div>
                <span className="sr-only">
                  {d.state === "nominal" ? "Stable" : "Approaching threshold"}
                </span>
              </li>
            ))}
          </ul>
          <p className="mt-3 text-xs text-text-lo">
            Rainfall PSI is near threshold after the 96 mm event; the monitor flags it, a reviewer
            decides.
          </p>
        </Panel>

        <Panel id="data-trust" className="lg:col-span-5" eyebrow="Division ADRA" title="Data trust">
          <p className="flex items-baseline gap-2">
            <span className="font-data text-2xl font-semibold text-text-hi">
              {formatDecimal(data.dataTrust.division)}
            </span>
            <span className="text-sm text-text-mid">
              division score · {data.dataTrust.lowTrustAssets} low-trust assets
            </span>
          </p>
          <ul className="mt-3 divide-y divide-border-subtle">
            {data.dataTrust.flags.map((f) => (
              <li key={f.flag} className="flex justify-between gap-2 py-2 text-sm">
                <span className="break-all font-data text-text-mid">{f.flag}</span>
                <span className="font-data text-text-hi">{f.count}</span>
              </li>
            ))}
          </ul>
          <p className="mt-3 text-xs text-text-lo">
            Low-trust assets are shown with their flag and discounted in the ranking — never
            suppressed. ADRA/TC/12T scores 0.62 because its age does not match its electrical
            signature.
          </p>
        </Panel>

        <Panel className="lg:col-span-7" eyebrow="Before any promotion" title="Promotion gates">
          <ul className="divide-y divide-border-subtle">
            {data.gates.map((g) => (
              <li key={g.name} className="py-3">
                <div className="flex flex-wrap items-center justify-between gap-2">
                  <span className="flex items-center gap-2 text-sm font-semibold text-text-hi">
                    {g.pass ? (
                      <Check className="h-4 w-4 text-ok" aria-hidden="true" />
                    ) : (
                      <X className="h-4 w-4 text-critical" aria-hidden="true" />
                    )}
                    {g.name}
                    <span
                      className={cn("text-xs font-semibold", g.pass ? "text-ok" : "text-critical")}
                    >
                      {g.pass ? "Pass" : "Fail"}
                    </span>
                  </span>
                  <span className="font-data text-sm text-text-hi">{g.value}</span>
                </div>
                <button
                  type="button"
                  aria-expanded={policyOpen === g.name}
                  onClick={() => setPolicyOpen((p) => (p === g.name ? null : g.name))}
                  className="mt-1 min-h-11 text-xs font-semibold text-accent-text underline underline-offset-4"
                >
                  Why this threshold?
                </button>
                {policyOpen === g.name && (
                  <p className="text-xs leading-5 text-text-mid">
                    Policy NIDAN-MLOPS-04 §{data.gates.indexOf(g) + 2}: {g.rule}. Thresholds are
                    governed, versioned and signed; this screen can show them but not edit them.
                  </p>
                )}
              </li>
            ))}
          </ul>
          <p className="mt-3 border-t border-border-subtle pt-3 font-data text-xs text-text-mid">
            {data.signature}
          </p>
        </Panel>
      </div>
    </div>
  );
}
