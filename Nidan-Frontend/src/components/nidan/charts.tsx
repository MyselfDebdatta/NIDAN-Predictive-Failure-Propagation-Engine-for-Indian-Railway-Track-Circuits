import { useRef, useState, type KeyboardEvent } from "react";
import { Link } from "@tanstack/react-router";
import type { Alert, SignalSeries } from "@/data/fixtures";
import { formatCount, formatDecimal, formatRisk, formatRul } from "@/lib/formatters";
import { blockWhenLabel, daysUntilBlock } from "@/lib/blocks";
import {
  Chip,
  LevelBadge,
  LevelGlyph,
  Notice,
  RiskBar,
  levelNames,
} from "@/components/nidan/primitives";
import { cn } from "@/lib/utils";

/* ---------------------------------------------------------------- Signal Spine */

export function SignalSpine({ alerts }: { alerts: Alert[] }) {
  const rows = alerts.slice(0, 8);
  return (
    <div className="relative">
      <span aria-hidden="true" className="spine-line absolute bottom-0 left-[15px] top-5 w-px" />
      <ol className="relative" aria-label="Track circuits ordered by policy rank">
        {rows.map((alert) => (
          <li key={alert.id}>
            <Link
              to="/assets/$assetId"
              params={{ assetId: alert.assetId }}
              aria-label={`${alert.assetId}, ${levelNames[alert.level]}, 7 day risk ${formatRisk(alert.risk.h7d)}`}
              className="group grid min-h-14 grid-cols-[32px_minmax(0,1fr)_auto] items-center gap-2 rounded-sm py-2 pr-2 hover:bg-bg-hover"
            >
              <span className="grid place-items-center bg-transparent">
                <span className="grid h-5 w-5 place-items-center rounded-full bg-bg-panel">
                  <LevelGlyph level={alert.level} />
                </span>
              </span>
              <span className="min-w-0">
                <span className="block truncate font-data text-[13px] font-semibold text-text-hi group-hover:text-accent-text">
                  {alert.assetId}
                </span>
                <span className="block truncate text-xs text-text-lo">
                  {levelNames[alert.level]} · {alert.route}
                </span>
              </span>
              <span className="flex flex-col items-end gap-1">
                <span className="number-cell text-sm font-semibold text-text-hi">
                  {formatRisk(alert.risk.h7d)}
                </span>
                <RiskBar value={alert.risk.h7d} level={alert.level} />
              </span>
            </Link>
          </li>
        ))}
      </ol>
    </div>
  );
}

/* ---------------------------------------------------------------- Propagation map */

const mapSummary =
  "Schematic: the drain and weather cell c-9917 links track circuits 12T, 14T and 16T; 12T is the most affected, and a cascade to 21T is predicted in 6 to 11 days.";

function MapNode({
  x,
  y,
  level,
  label,
  sub,
  predicted = false,
}: {
  x: number;
  y: number;
  level: "watch" | "warning" | "critical";
  label: string;
  sub?: string;
  predicted?: boolean;
}) {
  return (
    <g>
      <circle
        cx={x}
        cy={y}
        r="22"
        fill="var(--bg-panel)"
        stroke={
          predicted
            ? "var(--border-strong)"
            : level === "warning"
              ? "var(--warning)"
              : "var(--accent)"
        }
        strokeWidth="2"
        strokeDasharray={predicted ? "4 4" : undefined}
      />
      {level === "watch" && !predicted && (
        <circle cx={x} cy={y} r="7" fill="none" stroke="var(--accent)" strokeWidth="2.5" />
      )}
      {level === "watch" && predicted && (
        <circle cx={x} cy={y} r="6" fill="none" stroke="var(--text-lo)" strokeWidth="2" />
      )}
      {level === "warning" && (
        <path d={`M${x} ${y - 8} L${x + 8} ${y + 6} L${x - 8} ${y + 6}Z`} fill="var(--warning)" />
      )}
      <text
        x={x}
        y={y + 40}
        textAnchor="middle"
        fill="var(--text-hi)"
        fontSize="13"
        fontWeight="600"
        fontFamily="var(--font-code)"
      >
        {label}
      </text>
      {sub && (
        <text
          x={x}
          y={y + 56}
          textAnchor="middle"
          fill="var(--text-lo)"
          fontSize="11"
          fontFamily="var(--font-ui)"
        >
          {sub}
        </text>
      )}
    </g>
  );
}

export function PropagationMap() {
  return (
    <figure className="min-w-0">
      {/* Wide layout */}
      <svg
        viewBox="0 0 680 280"
        role="img"
        aria-label={mapSummary}
        className="hidden h-auto w-full sm:block"
      >
        <rect
          x="24"
          y="24"
          width="470"
          height="232"
          rx="8"
          fill="var(--bg-inset)"
          stroke="var(--border-strong)"
          strokeDasharray="5 5"
        />
        <text x="42" y="50" fill="var(--text-lo)" fontSize="12" fontFamily="var(--font-code)">
          c-9917 · shared drain / weather cell
        </text>
        <path
          d="M124 140 C190 140 200 92 268 92"
          fill="none"
          stroke="var(--accent)"
          strokeWidth="2"
        />
        <path
          d="M124 140 C190 140 200 196 268 196"
          fill="none"
          stroke="var(--accent)"
          strokeWidth="2"
        />
        <path
          d="M312 92 C380 92 392 140 440 140"
          fill="none"
          stroke="var(--warning)"
          strokeWidth="2"
        />
        <path
          d="M312 196 C380 196 392 140 440 140"
          fill="none"
          stroke="var(--accent)"
          strokeWidth="2"
        />
        <path
          d="M462 140 H566"
          fill="none"
          stroke="var(--border-strong)"
          strokeWidth="2"
          strokeDasharray="5 5"
        />
        <MapNode x={102} y={140} level="watch" label="12T" sub="most affected" />
        <MapNode x={290} y={92} level="warning" label="14T" />
        <MapNode x={290} y={196} level="watch" label="16T" />
        <circle cx="452" cy="140" r="5" fill="var(--border-strong)" />
        <MapNode x={590} y={140} level="watch" label="21T" sub="6–11 d predicted" predicted />
      </svg>
      {/* Narrow layout: same graph, vertical */}
      <svg
        viewBox="0 0 300 470"
        role="img"
        aria-label={mapSummary}
        className="mx-auto block h-auto w-full max-w-[340px] sm:hidden"
      >
        <rect
          x="16"
          y="16"
          width="268"
          height="320"
          rx="8"
          fill="var(--bg-inset)"
          stroke="var(--border-strong)"
          strokeDasharray="5 5"
        />
        <text x="30" y="40" fill="var(--text-lo)" fontSize="12" fontFamily="var(--font-code)">
          c-9917 · drain / weather
        </text>
        <path
          d="M150 104 C150 150 80 150 80 196"
          fill="none"
          stroke="var(--accent)"
          strokeWidth="2"
        />
        <path
          d="M150 104 C150 150 220 150 220 196"
          fill="none"
          stroke="var(--accent)"
          strokeWidth="2"
        />
        <path
          d="M80 240 C80 290 150 280 150 330"
          fill="none"
          stroke="var(--warning)"
          strokeWidth="2"
        />
        <path
          d="M220 240 C220 290 150 280 150 330"
          fill="none"
          stroke="var(--accent)"
          strokeWidth="2"
        />
        <path
          d="M150 330 V378"
          fill="none"
          stroke="var(--border-strong)"
          strokeWidth="2"
          strokeDasharray="5 5"
        />
        <MapNode x={150} y={82} level="watch" label="12T" />
        <MapNode x={80} y={218} level="warning" label="14T" />
        <MapNode x={220} y={218} level="watch" label="16T" />
        <MapNode x={150} y={400} level="watch" label="21T" sub="6–11 d predicted" predicted />
      </svg>
      <figcaption className="mt-3 flex flex-wrap items-center gap-x-4 gap-y-2 text-xs text-text-lo">
        <span className="inline-flex items-center gap-1.5">
          <LevelGlyph level="watch" />
          Watch
        </span>
        <span className="inline-flex items-center gap-1.5">
          <LevelGlyph level="warning" />
          Warning
        </span>
        <span className="inline-flex items-center gap-1.5">
          <span
            aria-hidden="true"
            className="h-3 w-3 rounded-full border border-dashed border-border-strong"
          />
          Predicted, not observed
        </span>
        <span>Schematic, not geographic</span>
      </figcaption>
    </figure>
  );
}

/* ---------------------------------------------------------------- RUL band */

export function RulBand({ alert }: { alert: Alert }) {
  const [showTable, setShowTable] = useState(false);
  const max = Math.max(45, Math.ceil(alert.rul.p90Days / 15) * 15);
  const pct = (value: number) => `${(Math.min(value, max) / max) * 100}%`;
  const blockInDays = daysUntilBlock(alert);
  const blockId = alert.block?.window.id ?? null;
  const inside = blockInDays !== null && blockInDays <= alert.rul.p10Days;
  const summary = [
    `Remaining useful life: p10 ${alert.rul.p10Days} days, median ${alert.rul.medianDays} days, p90 ${alert.rul.p90Days} days.`,
    blockInDays === null || blockId === null
      ? "No published block this week."
      : `${blockId} is ${blockWhenLabel(blockInDays)}, ${inside ? "inside" : "outside"} the 10th percentile.`,
  ].join(" ");
  const ticks = Array.from({ length: max / 15 + 1 }, (_, i) => i * 15);
  /** Keep direct labels inside the plot when a marker sits on an edge. */
  const labelStyle = (value: number) => {
    const percent = (Math.min(value, max) / max) * 100;
    return {
      left: `${percent}%`,
      transform: percent < 8 ? "none" : percent > 92 ? "translateX(-100%)" : "translateX(-50%)",
    };
  };
  return (
    <figure className="min-w-0">
      <div role="img" aria-label={summary} className="relative mx-2 h-[136px] sm:mx-4">
        {/* labels above */}
        {blockInDays !== null && blockId !== null && (
          <>
            <span
              className="absolute top-0 whitespace-nowrap text-xs font-semibold text-accent-text"
              style={labelStyle(blockInDays)}
            >
              {blockId} · {blockWhenLabel(blockInDays)}
            </span>
            <span
              aria-hidden="true"
              className="absolute top-[18px] h-0 w-0 -translate-x-1/2 border-x-[6px] border-t-[8px] border-x-transparent border-t-accent"
              style={{ left: pct(blockInDays) }}
            />
          </>
        )}
        {/* band */}
        <div className="absolute inset-x-0 top-[52px] h-px bg-border-strong" />
        <div
          className="absolute top-[38px] h-7 rounded-sm border border-accent bg-accent-wash"
          style={{
            left: pct(alert.rul.p10Days),
            width: `calc(${pct(alert.rul.p90Days)} - ${pct(alert.rul.p10Days)})`,
          }}
        />
        <div
          className="absolute top-[30px] h-11 w-0.5 -translate-x-1/2 bg-text-hi"
          style={{ left: pct(alert.rul.medianDays) }}
        />
        <div
          className="absolute top-[24px] h-14 w-0 -translate-x-1/2 border-l-2 border-dashed border-warning"
          style={{ left: pct(30) }}
        />
        {blockInDays !== null && (
          <div
            className="absolute top-[26px] h-12 w-0 -translate-x-1/2 border-l-2 border-accent-text"
            style={{ left: pct(blockInDays) }}
          />
        )}
        {/* direct labels below */}
        <span
          className="absolute top-[78px] whitespace-nowrap font-data text-xs font-semibold text-text-hi"
          style={labelStyle(alert.rul.p10Days)}
        >
          p10 {formatRul(alert.rul.p10Days)}
        </span>
        <span
          className="absolute top-[94px] whitespace-nowrap font-data text-xs font-semibold text-text-hi"
          style={labelStyle(alert.rul.medianDays)}
        >
          median {formatRul(alert.rul.medianDays)}
        </span>
        <span
          className="absolute top-[78px] whitespace-nowrap font-data text-xs font-semibold text-text-hi"
          style={labelStyle(alert.rul.p90Days)}
        >
          p90 {formatRul(alert.rul.p90Days)}
        </span>
        <span
          className="absolute top-[4px] whitespace-nowrap text-[11px] text-warning max-sm:hidden"
          style={labelStyle(30)}
        >
          30 d threshold
        </span>
        {/* axis */}
        <div className="absolute inset-x-0 top-[118px] border-t border-border-subtle" />
        {ticks.map((tick) => (
          <span
            key={tick}
            className={cn(
              "absolute top-[120px] -translate-x-1/2 font-data text-[10px] text-text-lo",
              tick !== 0 && tick !== 30 && tick !== max && "max-sm:hidden",
            )}
            style={{ left: pct(tick) }}
          >
            {tick}
          </span>
        ))}
      </div>
      <figcaption className="mt-3 flex flex-wrap items-center justify-between gap-3">
        <p className="text-xs text-text-lo">
          Days from now · conformal coverage{" "}
          <span className="font-data text-text-mid">{formatDecimal(alert.rul.coverage, 3)}</span> on{" "}
          {formatCount(alert.rul.heldOutN)} held-out outcomes
          <span className="sm:hidden"> · dashed line = 30 d threshold</span>
        </p>
        <button
          className="min-h-11 px-2 text-xs font-semibold text-accent-text underline underline-offset-4"
          onClick={() => setShowTable((value) => !value)}
          aria-expanded={showTable}
        >
          {showTable ? "Hide table" : "Show as table"}
        </button>
      </figcaption>
      {showTable && (
        <table className="mt-2 w-full border-t border-border-subtle text-left text-sm">
          <caption className="sr-only">Remaining useful life quantiles</caption>
          <tbody>
            {[
              ["p10 (planning number)", formatRul(alert.rul.p10Days)],
              ["Median", formatRul(alert.rul.medianDays)],
              ["p90", formatRul(alert.rul.p90Days)],
              ["Threshold", "30 d"],
              ...(blockInDays !== null && blockId !== null
                ? [
                    [
                      blockId,
                      `${blockWhenLabel(blockInDays)} · ${inside ? "inside" : "outside"} p10`,
                    ] as [string, string],
                  ]
                : []),
            ].map(([label, value]) => (
              <tr key={label} className="border-b border-border-subtle">
                <th scope="row" className="py-2 font-normal text-text-mid">
                  {label}
                </th>
                <td className="py-2 text-right font-data font-semibold text-text-hi">{value}</td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </figure>
  );
}

/* ---------------------------------------------------------------- Risk horizon */

export function RiskHorizon({ alert }: { alert: Alert }) {
  const items = [
    ["24 h", alert.risk.h24],
    ["72 h", alert.risk.h72],
    ["7 d", alert.risk.h7d],
  ] as const;
  return (
    <dl className="grid grid-cols-3 gap-2">
      {items.map(([label, value]) => (
        <div key={label} className="rounded-sm border border-border-subtle bg-bg-raised px-3 py-2">
          <dt className="text-xs text-text-lo">Risk {label}</dt>
          <dd className="mt-1 flex items-center justify-between gap-2">
            <span className="number-cell text-base font-semibold text-text-hi">
              {formatRisk(value)}
            </span>
            <RiskBar value={value} level={alert.level} className="w-10" />
          </dd>
        </div>
      ))}
    </dl>
  );
}

/* ---------------------------------------------------------------- Sparkline */

export function Sparkline({ series }: { series: SignalSeries }) {
  const { values, baseline, label, unit, normalBand } = series;
  const lo = Math.min(...values, baseline);
  const hi = Math.max(...values, baseline);
  const pad = (hi - lo || 1) * 0.15;
  const min = lo - pad;
  const max = hi + pad;
  const y = (value: number) => 56 - ((value - min) / (max - min)) * 48;
  const step = 168 / Math.max(1, values.length - 1);
  const points = values.map((value, index) => `${6 + index * step},${y(value)}`).join(" ");
  const latest = values.at(-1) ?? 0;
  const first = values[0] ?? 0;
  const change = first ? ((latest - first) / first) * 100 : 0;
  return (
    <figure className="min-w-0 rounded-sm border border-border-subtle bg-bg-raised p-3">
      <figcaption className="flex min-w-0 items-baseline justify-between gap-2">
        <span className="truncate text-xs font-medium text-text-mid">{label}</span>
        <span className="number-cell shrink-0 text-sm font-semibold text-text-hi">
          {latest} {unit}
        </span>
      </figcaption>
      <svg
        viewBox="0 0 180 62"
        role="img"
        aria-label={`${label}, 12 days: from ${first} to ${latest} ${unit}, ${change >= 0 ? "up" : "down"} ${Math.abs(Math.round(change))}%. Dry baseline ${baseline} ${unit}.`}
        className="mt-2 h-14 w-full"
        preserveAspectRatio="none"
      >
        <line
          x1="2"
          y1={y(baseline)}
          x2="178"
          y2={y(baseline)}
          stroke="var(--text-lo)"
          strokeDasharray="3 4"
          vectorEffect="non-scaling-stroke"
        />
        <polyline
          points={points}
          fill="none"
          stroke="var(--accent)"
          strokeWidth="2"
          strokeLinecap="round"
          strokeLinejoin="round"
          vectorEffect="non-scaling-stroke"
        />
      </svg>
      <p className="mt-1 flex flex-wrap justify-between gap-x-2 text-[11px] text-text-lo">
        <span>
          Dry baseline {baseline} {unit}
        </span>
        <span>Normal {normalBand}</span>
      </p>
    </figure>
  );
}

/* ---------------------------------------------------------------- SHAP */

export function ShapBars({
  features,
}: {
  features: { feature: string; label: string; value: number }[];
}) {
  const maxAbs = Math.max(...features.map((f) => Math.abs(f.value)), 0.1);
  return (
    <ul className="space-y-3" aria-label="Signed feature contributions in log-odds">
      {features.map((feature) => {
        const width = `${(Math.abs(feature.value) / maxAbs) * 50}%`;
        const negative = feature.value < 0;
        return (
          <li
            key={feature.feature}
            className="grid gap-1.5 sm:grid-cols-[minmax(0,200px)_minmax(0,1fr)_auto] sm:items-center sm:gap-3"
          >
            <div className="min-w-0">
              <p className="text-sm text-text-hi">{feature.label}</p>
              <p className="truncate font-data text-[11px] text-text-lo">{feature.feature}</p>
            </div>
            <div aria-hidden="true" className="relative h-3 rounded-sm bg-bg-inset">
              <span className="absolute inset-y-[-3px] left-1/2 w-px bg-border-strong" />
              <span
                className={cn(
                  "absolute inset-y-0 rounded-sm",
                  negative ? "right-1/2 bg-warning" : "left-1/2 bg-accent",
                )}
                style={{ width }}
              />
            </div>
            <p className="font-data text-xs text-text-mid sm:text-right">
              <span className="font-semibold text-text-hi">
                {feature.value > 0 ? "+" : "−"}
                {formatDecimal(Math.abs(feature.value))}
              </span>{" "}
              · {negative ? "increases risk" : "lowers risk"}
            </p>
          </li>
        );
      })}
    </ul>
  );
}

/* ---------------------------------------------------------------- Explanation card */

const lenses = ["Physics", "Model", "Precedents"] as const;
type Lens = (typeof lenses)[number];

export function ExplanationCard({ alert, id }: { alert: Alert; id?: string }) {
  const [lens, setLens] = useState<Lens>("Physics");
  const [visited, setVisited] = useState<Set<Lens>>(() => new Set(["Physics"]));
  const tabRefs = useRef<Record<string, HTMLButtonElement | null>>({});
  const baseId = `lens-${alert.id}`;
  const select = (next: Lens) => {
    setLens(next);
    setVisited((prev) => new Set(prev).add(next));
    tabRefs.current[next]?.focus();
  };
  const onKeyDown = (event: KeyboardEvent<HTMLDivElement>) => {
    const current = lenses.indexOf(lens);
    let next: Lens | undefined;
    if (event.key === "ArrowRight") next = lenses[(current + 1) % lenses.length];
    if (event.key === "ArrowLeft") next = lenses[(current + lenses.length - 1) % lenses.length];
    if (event.key === "Home") next = "Physics";
    if (event.key === "End") next = "Precedents";
    if (next) {
      event.preventDefault();
      select(next);
    }
  };
  const { physics, model, precedents } = alert.explanation;
  return (
    <section
      id={id}
      aria-labelledby={`${baseId}-title`}
      className="panel-surface min-w-0 scroll-mt-24"
    >
      <div className="border-b border-border-subtle px-4 pt-3 sm:px-5">
        <p className="eyebrow">Nidāna · cause</p>
        <h2
          id={`${baseId}-title`}
          className="mt-1 text-[15px] font-semibold leading-5 text-text-hi"
        >
          Explanation
        </h2>
        <div
          role="tablist"
          aria-label="Explanation lens"
          onKeyDown={onKeyDown}
          className="mt-2 flex gap-1 overflow-x-auto"
        >
          {lenses.map((item) => (
            <button
              key={item}
              ref={(node) => {
                tabRefs.current[item] = node;
              }}
              id={`${baseId}-tab-${item}`}
              role="tab"
              aria-selected={lens === item}
              aria-controls={`${baseId}-panel-${item}`}
              tabIndex={lens === item ? 0 : -1}
              onClick={() => select(item)}
              className={cn(
                "min-h-11 shrink-0 border-b-2 px-3 text-sm font-semibold transition-colors duration-[var(--dur-2)]",
                lens === item
                  ? "border-accent text-text-hi"
                  : "border-transparent text-text-lo hover:text-text-hi",
              )}
            >
              {item}
            </button>
          ))}
        </div>
      </div>
      <div className="p-4 sm:p-5">
        {visited.has("Physics") && (
          <div
            role="tabpanel"
            id={`${baseId}-panel-Physics`}
            aria-labelledby={`${baseId}-tab-Physics`}
            hidden={lens !== "Physics"}
            className="space-y-4"
          >
            <p className="text-sm font-semibold leading-6 text-text-hi">{physics.headline}</p>
            <div className="grid gap-2 sm:grid-cols-3">
              {physics.state.map((item) => (
                <div
                  className="rounded-sm border border-border-subtle bg-bg-raised p-3"
                  key={item.label}
                >
                  <p className="text-xs text-text-lo">{item.label}</p>
                  <p className="mt-1 font-data text-sm font-semibold text-text-hi">{item.value}</p>
                  <p className="mt-1 text-xs text-text-lo">Baseline {item.baseline}</p>
                </div>
              ))}
            </div>
            <Notice title="Falsifier">{physics.falsifier}</Notice>
          </div>
        )}
        {visited.has("Model") && (
          <div
            role="tabpanel"
            id={`${baseId}-panel-Model`}
            aria-labelledby={`${baseId}-tab-Model`}
            hidden={lens !== "Model"}
            className="space-y-4"
          >
            <ShapBars features={model.shapTop} />
            <p className="text-xs leading-5 text-text-mid">
              Signed SHAP contributions to the log-odds of failure. Negative values mean the signal
              increases risk (falling relay current). {model.calibrationNote}
            </p>
            <div className="flex flex-wrap gap-2">
              <Chip tone="mono">
                Conformal set {`{${model.modeSet.join(", ")}}`} at{" "}
                {formatDecimal(model.modeSetCoverage)}
              </Chip>
              <Chip>Lens agreement {model.agreement}</Chip>
            </div>
            <Notice title="Falsifier" tone="neutral">
              {physics.falsifier}
            </Notice>
          </div>
        )}
        {visited.has("Precedents") && (
          <div
            role="tabpanel"
            id={`${baseId}-panel-Precedents`}
            aria-labelledby={`${baseId}-tab-Precedents`}
            hidden={lens !== "Precedents"}
            className="space-y-3"
          >
            {precedents.length === 0 && (
              <p className="text-sm text-text-mid">
                No confirmed precedents above 0.6 similarity. The other lenses still apply.
              </p>
            )}
            {precedents.map((item) => (
              <article
                className="border-b border-border-subtle pb-3 last:border-0 last:pb-0"
                key={item.smmsId}
              >
                <div className="flex flex-wrap items-center justify-between gap-2">
                  <span className="font-data text-sm font-semibold text-text-hi">
                    {item.smmsId}
                  </span>
                  <Chip tone="mono">similarity {formatDecimal(item.similarity)}</Chip>
                </div>
                <p className="mt-1 text-xs text-text-lo">
                  <span className="font-data">{item.assetId}</span> · confirmed {item.confirmedMode}{" "}
                  · {item.daysAgo} days ago
                </p>
                <p className="mt-1 text-sm text-text-mid">{item.outcome}</p>
              </article>
            ))}
            <p className="text-xs text-text-lo">
              Feedback on precedents writes to the retrieval index only — it does not change any
              score.
            </p>
          </div>
        )}
      </div>
    </section>
  );
}

/* ---------------------------------------------------------------- Reliability diagram */

export function ReliabilityDiagram({
  bins,
}: {
  bins: { predicted: number; observed: number; n: number }[];
}) {
  const [showTable, setShowTable] = useState(false);
  const size = 260;
  const p = 30;
  const s = (v: number) => p + v * (size - p * 2);
  const yv = (v: number) => size - p - v * (size - p * 2);
  const maxN = Math.max(...bins.map((b) => b.n));
  return (
    <figure className="min-w-0">
      <svg
        viewBox={`0 0 ${size} ${size}`}
        role="img"
        aria-label={`Reliability diagram over ${bins.length} bins. Observed frequency tracks predicted probability closely, slightly below the diagonal at high scores.`}
        className="mx-auto block h-auto w-full max-w-[360px]"
      >
        {[0, 0.25, 0.5, 0.75, 1].map((t) => (
          <g key={t}>
            <line x1={s(t)} y1={yv(0)} x2={s(t)} y2={yv(1)} stroke="var(--border-subtle)" />
            <line x1={s(0)} y1={yv(t)} x2={s(1)} y2={yv(t)} stroke="var(--border-subtle)" />
            <text
              x={s(t)}
              y={size - 12}
              textAnchor="middle"
              fontSize="10"
              fill="var(--text-lo)"
              fontFamily="var(--font-code)"
            >
              {t}
            </text>
            <text
              x={18}
              y={yv(t) + 3}
              textAnchor="middle"
              fontSize="10"
              fill="var(--text-lo)"
              fontFamily="var(--font-code)"
            >
              {t}
            </text>
          </g>
        ))}
        <line
          x1={s(0)}
          y1={yv(0)}
          x2={s(1)}
          y2={yv(1)}
          stroke="var(--text-lo)"
          strokeDasharray="4 4"
        />
        {bins.map((b) => (
          <rect
            key={b.predicted}
            x={s(b.predicted) - 6}
            y={yv(0) - (b.n / maxN) * 26}
            width="12"
            height={(b.n / maxN) * 26}
            fill="var(--bg-raised)"
            stroke="var(--border)"
          />
        ))}
        <polyline
          points={bins.map((b) => `${s(b.predicted)},${yv(b.observed)}`).join(" ")}
          fill="none"
          stroke="var(--accent)"
          strokeWidth="2"
        />
        {bins.map((b) => (
          <circle
            key={b.predicted}
            cx={s(b.predicted)}
            cy={yv(b.observed)}
            r="3.5"
            fill="var(--accent)"
          />
        ))}
      </svg>
      <figcaption className="mt-2 flex flex-wrap items-center justify-between gap-2 text-xs text-text-lo">
        <span>x: predicted · y: observed · bars: bin count · dashed: perfect calibration</span>
        <button
          className="min-h-11 px-2 font-semibold text-accent-text underline underline-offset-4"
          onClick={() => setShowTable((v) => !v)}
          aria-expanded={showTable}
        >
          {showTable ? "Hide table" : "Show as table"}
        </button>
      </figcaption>
      {showTable && (
        <table className="w-full text-left text-sm">
          <thead>
            <tr className="border-b border-border-subtle text-xs text-text-lo">
              <th scope="col" className="py-2 font-medium">
                Predicted
              </th>
              <th scope="col" className="py-2 font-medium">
                Observed
              </th>
              <th scope="col" className="py-2 text-right font-medium">
                n
              </th>
            </tr>
          </thead>
          <tbody>
            {bins.map((b) => (
              <tr key={b.predicted} className="border-b border-border-subtle font-data">
                <td className="py-1.5">{formatDecimal(b.predicted)}</td>
                <td className="py-1.5">{formatDecimal(b.observed)}</td>
                <td className="py-1.5 text-right">{formatCount(b.n)}</td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </figure>
  );
}

export function AlertMiniLink({ alert }: { alert: Alert }) {
  return (
    <Link
      to="/alerts/$alertId"
      params={{ alertId: alert.id }}
      className="inline-flex min-h-11 items-center gap-2 text-left"
    >
      <LevelBadge level={alert.level} />
      <span className="font-data text-xs text-text-hi">{alert.assetId}</span>
    </Link>
  );
}
