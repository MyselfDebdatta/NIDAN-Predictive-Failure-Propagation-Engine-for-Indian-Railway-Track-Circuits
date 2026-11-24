import { Link } from "@tanstack/react-router";
import { AlertTriangle, ArrowUpRight, Check, Clock, RotateCcw } from "lucide-react";
import type { ReactNode } from "react";
import type { Alert, BlockFit, StateLevel } from "@/data/fixtures";
import { formatDecimal, formatRisk } from "@/lib/formatters";
import { blockFitLabel } from "@/lib/policy";
import { useT } from "@/i18n/strings";
import { cn } from "@/lib/utils";

export function SignalMark({ className }: { className?: string }) {
  return (
    <svg
      viewBox="0 0 20 20"
      fill="none"
      stroke="currentColor"
      strokeWidth="1.7"
      strokeLinecap="round"
      strokeLinejoin="round"
      aria-hidden="true"
      className={className}
    >
      <path d="M1.5 11h2.6L6 4.6l2.6 11L11 9.4l1.3 3.2h4.4" />
    </svg>
  );
}

/** State glyph: solid dot = Nominal, hollow ring = Watch, filled triangle = Warning, diamond with dark core = Critical. */
export function LevelGlyph({ level, className }: { level: StateLevel; className?: string }) {
  const color =
    level === "critical"
      ? "text-critical"
      : level === "warning"
        ? "text-warning"
        : level === "watch"
          ? "text-accent"
          : "text-neutral";
  return (
    <svg
      viewBox="0 0 14 14"
      aria-hidden="true"
      className={cn("h-3.5 w-3.5 shrink-0", color, className)}
    >
      {level === "nominal" && <circle cx="7" cy="7" r="4" fill="currentColor" />}
      {level === "watch" && (
        <circle cx="7" cy="7" r="4.6" fill="none" stroke="currentColor" strokeWidth="2" />
      )}
      {level === "warning" && <path d="M7 1.6 12.6 12H1.4Z" fill="currentColor" />}
      {level === "critical" && (
        <>
          <path d="M7 0.8 13.2 7 7 13.2 0.8 7Z" fill="currentColor" />
          <path d="M7 4.9 9.1 7 7 9.1 4.9 7Z" fill="var(--bg-app)" />
        </>
      )}
    </svg>
  );
}

export const levelNames: Record<StateLevel, string> = {
  nominal: "Nominal",
  watch: "Watch",
  warning: "Warning",
  critical: "Critical",
};

export const levelNamesHi: Record<StateLevel, string> = {
  nominal: "सामान्य",
  watch: "निगरानी",
  warning: "चेतावनी",
  critical: "गंभीर",
};

const levelTone: Record<StateLevel, string> = {
  critical: "border-critical/40 bg-critical-wash text-critical",
  warning: "border-warning/40 bg-warning-wash text-warning",
  watch: "border-accent/40 bg-accent-wash text-accent-text",
  nominal: "border-border bg-bg-raised text-text-mid",
};

export function LevelBadge({ level, className }: { level: StateLevel; className?: string }) {
  const { lang } = useT();
  return (
    <span
      className={cn(
        "inline-flex min-h-7 items-center gap-1.5 whitespace-nowrap rounded-sm border px-2 text-xs font-semibold",
        levelTone[level],
        className,
      )}
    >
      <LevelGlyph level={level} />
      {levelNames[level]}
      {lang === "hi" && (
        <span lang="hi" className="font-medium">
          · {levelNamesHi[level]}
        </span>
      )}
    </span>
  );
}

export function Chip({
  children,
  className,
  tone = "neutral",
}: {
  children: ReactNode;
  className?: string;
  tone?: "neutral" | "accent" | "warning" | "critical" | "mono";
}) {
  const toneClass = {
    neutral: "border-border text-text-mid",
    mono: "border-border text-text-mid font-data",
    accent: "border-accent/40 bg-accent-wash text-accent-text",
    warning: "border-warning/40 bg-warning-wash text-warning",
    critical: "border-critical/40 bg-critical-wash text-critical",
  }[tone];
  return (
    <span
      className={cn(
        "inline-flex min-h-7 items-center gap-1.5 whitespace-nowrap rounded-sm border px-2 text-xs",
        toneClass,
        className,
      )}
    >
      {children}
    </span>
  );
}

export function Panel({
  children,
  className,
  bodyClassName,
  title,
  eyebrow,
  action,
  id,
  titleId,
}: {
  children: ReactNode;
  className?: string;
  bodyClassName?: string;
  title?: string;
  eyebrow?: string;
  action?: ReactNode;
  id?: string;
  titleId?: string;
}) {
  const headingId = titleId ?? (id ? `${id}-title` : undefined);
  return (
    <section
      id={id}
      aria-labelledby={title ? headingId : undefined}
      className={cn("panel-surface min-w-0 scroll-mt-24", className)}
    >
      {(title || eyebrow || action) && (
        <div className="flex min-w-0 flex-wrap items-start justify-between gap-x-3 gap-y-2 border-b border-border-subtle px-4 py-3 sm:px-5">
          <div className="min-w-0">
            {eyebrow && <p className="eyebrow mb-1">{eyebrow}</p>}
            {title && (
              <h2 id={headingId} className="text-[15px] font-semibold leading-5 text-text-hi">
                {title}
              </h2>
            )}
          </div>
          {action && <div className="flex shrink-0 flex-wrap items-center gap-2">{action}</div>}
        </div>
      )}
      <div className={cn("min-w-0 p-4 sm:p-5", bodyClassName)}>{children}</div>
    </section>
  );
}

export function KpiTile({
  label,
  value,
  delta,
  note,
  tone = "neutral",
  glyph,
}: {
  label: string;
  value: string;
  delta: string;
  note: string;
  tone?: "neutral" | "watch" | "warning" | "critical";
  glyph?: StateLevel;
}) {
  const toneClass =
    tone === "critical"
      ? "text-critical"
      : tone === "warning"
        ? "text-warning"
        : tone === "watch"
          ? "text-accent-text"
          : "text-text-mid";
  return (
    <section
      className="panel-surface min-w-0 p-3.5 sm:p-5"
      aria-label={`${label}: ${value}, ${delta}`}
    >
      <p className="flex items-center gap-1.5 text-xs font-medium text-text-lo">
        {glyph && <LevelGlyph level={glyph} />}
        {label}
      </p>
      <div className="mt-2 flex flex-wrap items-baseline justify-between gap-x-2 gap-y-1">
        <strong className="font-display text-[26px] font-semibold leading-8 text-text-hi sm:text-[30px]">
          {value}
        </strong>
        <span className={cn("text-xs font-semibold", toneClass)}>{delta}</span>
      </div>
      <p className="mt-1.5 text-xs leading-4 text-text-lo">{note}</p>
    </section>
  );
}

export function PageHeading({
  eyebrow,
  title,
  titleHi,
  subtitle,
  action,
  children,
}: {
  eyebrow: string;
  title: string;
  titleHi?: string;
  subtitle?: string;
  action?: ReactNode;
  children?: ReactNode;
}) {
  const { lang } = useT();
  return (
    <header className="flex min-w-0 flex-col gap-4 lg:flex-row lg:items-end lg:justify-between">
      <div className="min-w-0">
        <p className="eyebrow">{eyebrow}</p>
        <h1 className="mt-2 font-display text-[24px] font-semibold leading-8 tracking-tight text-text-hi sm:text-[var(--fs-h1)] sm:leading-[var(--lh-h1)] xl:text-[30px] xl:leading-9">
          {title}
        </h1>
        {lang === "hi" && titleHi && (
          <p lang="hi" className="mt-1 text-base font-medium leading-6 text-text-mid">
            {titleHi}
          </p>
        )}
        {subtitle && <p className="mt-2 max-w-3xl text-sm leading-6 text-text-mid">{subtitle}</p>}
        {children && <div className="mt-3 flex flex-wrap gap-2">{children}</div>}
      </div>
      {action && <div className="flex shrink-0 flex-wrap items-center gap-2">{action}</div>}
    </header>
  );
}

/** Risk number. Colour follows the alert level (red is for Critical only), never the raw value. */
export function RiskValue({
  value,
  className,
  level,
}: {
  value: number;
  className?: string;
  level?: StateLevel;
}) {
  const tone =
    level === "critical" ? "text-critical" : level === "warning" ? "text-warning" : "text-text-hi";
  return (
    <span className={cn("number-cell font-semibold", tone, className)}>{formatRisk(value)}</span>
  );
}

export function RiskBar({
  value,
  className,
  level,
}: {
  value: number;
  className?: string;
  level?: StateLevel;
}) {
  const tone =
    level === "critical"
      ? "bg-critical"
      : level === "warning"
        ? "bg-warning"
        : level === "nominal"
          ? "bg-neutral"
          : "bg-accent";
  return (
    <span
      aria-hidden="true"
      className={cn(
        "relative block h-1 w-[54px] overflow-hidden rounded-full bg-bg-inset",
        className,
      )}
    >
      <span
        className={cn("absolute inset-y-0 left-0 rounded-full", tone)}
        style={{ width: `${Math.min(100, Math.round(value * 100))}%` }}
      />
    </span>
  );
}

const fitTone: Record<BlockFit, string> = {
  fits: "border-accent/40 bg-accent-wash text-accent-text",
  extends: "border-warning/40 bg-warning-wash text-warning",
  special: "border-critical/40 bg-critical-wash text-critical",
  none: "border-border bg-bg-raised text-text-mid",
};

export function BlockFitBadge({
  fit,
  label,
  className,
}: {
  fit: BlockFit;
  label?: string;
  className?: string;
}) {
  return (
    <span
      className={cn(
        "inline-flex min-h-7 items-center whitespace-nowrap rounded-sm border px-2 text-xs font-semibold",
        fitTone[fit],
        className,
      )}
    >
      {label ?? blockFitLabel[fit]}
    </span>
  );
}

export function AssetLink({
  assetId,
  children,
  className,
}: {
  assetId: string;
  children?: ReactNode;
  className?: string;
}) {
  return (
    <Link
      to="/assets/$assetId"
      params={{ assetId }}
      className={cn(
        "inline-flex min-h-11 items-center gap-1.5 text-left font-data text-sm font-semibold text-text-hi underline-offset-4 hover:text-accent-text hover:underline",
        className,
      )}
    >
      {children ?? assetId}
      <ArrowUpRight className="h-3.5 w-3.5 shrink-0" aria-hidden="true" />
    </Link>
  );
}

export function MetricLine({
  label,
  value,
  note,
}: {
  label: string;
  value: ReactNode;
  note?: string;
}) {
  return (
    <div className="grid grid-cols-[minmax(0,1fr)_auto] gap-x-4 border-b border-border-subtle py-2 last:border-0">
      <span className="text-sm text-text-mid">{label}</span>
      <span className="text-right font-data text-sm font-semibold text-text-hi">{value}</span>
      {note && <span className="col-span-2 mt-1 text-xs text-text-lo">{note}</span>}
    </div>
  );
}

export function CheckLine({ children }: { children: ReactNode }) {
  return (
    <p className="flex items-start gap-2 text-sm leading-6 text-text-mid">
      <Check className="mt-1 h-4 w-4 shrink-0 text-ok" aria-hidden="true" />
      {children}
    </p>
  );
}

export function StateShapeLegend() {
  return (
    <div className="flex flex-wrap gap-3 text-xs text-text-mid" aria-label="State shape key">
      {(["nominal", "watch", "warning", "critical"] as const).map((level) => (
        <span className="inline-flex items-center gap-1.5" key={level}>
          <LevelGlyph level={level} />
          {levelNames[level]}
        </span>
      ))}
    </div>
  );
}

export function DataTrust({ score, flags }: { score: number; flags: string[] }) {
  const low = score < 0.7;
  return (
    <span
      className={cn(
        "inline-flex min-h-7 items-center gap-1.5 whitespace-nowrap rounded-sm border px-2 text-xs",
        low ? "border-warning/40 bg-warning-wash text-warning" : "border-border text-text-mid",
      )}
    >
      Data trust <span className="font-data font-semibold">{formatDecimal(score)}</span>
      {low && (
        <span className="sr-only">, low trust{flags.length ? `: ${flags.join(", ")}` : ""}</span>
      )}
    </span>
  );
}

export function StaleChip({ asOf }: { asOf: string }) {
  return (
    <Chip tone="warning">
      <Clock className="h-3.5 w-3.5" aria-hidden="true" />
      as of {asOf}
    </Chip>
  );
}

export function Notice({
  tone = "warning",
  title,
  children,
}: {
  tone?: "warning" | "accent" | "critical" | "neutral";
  title: string;
  children: ReactNode;
}) {
  const toneClass = {
    warning: "border-warning bg-warning-wash",
    accent: "border-accent bg-accent-wash",
    critical: "border-critical bg-critical-wash",
    neutral: "border-border-strong bg-bg-raised",
  }[tone];
  const titleClass = {
    warning: "text-warning",
    accent: "text-accent-text",
    critical: "text-critical",
    neutral: "text-text-mid",
  }[tone];
  return (
    <div className={cn("rounded-sm border-l-2 p-3", toneClass)}>
      <p className={cn("eyebrow", titleClass)}>{title}</p>
      <div className="mt-1 text-sm leading-6 text-text-hi">{children}</div>
    </div>
  );
}

export function ErrorPanel({
  title = "This panel didn't load",
  detail,
  traceId,
  onRetry,
}: {
  title?: string;
  detail: string;
  traceId?: string;
  onRetry?: () => void;
}) {
  return (
    <div role="alert" className="panel-surface flex flex-col items-start gap-3 p-5">
      <p className="flex items-center gap-2 text-sm font-semibold text-text-hi">
        <AlertTriangle className="h-4 w-4 text-warning" aria-hidden="true" />
        {title}
      </p>
      <p className="text-sm text-text-mid">{detail}</p>
      <div className="flex flex-wrap items-center gap-2">
        {onRetry && (
          <button
            onClick={onRetry}
            className="inline-flex min-h-11 items-center gap-2 rounded-sm border border-border px-3 text-sm font-semibold text-text-hi hover:bg-bg-hover"
          >
            <RotateCcw className="h-4 w-4" aria-hidden="true" />
            Retry
          </button>
        )}
        {traceId && <Chip tone="mono">trace {traceId}</Chip>}
      </div>
    </div>
  );
}

export function EmptyState({ title, children }: { title: string; children?: ReactNode }) {
  return (
    <div className="flex flex-col items-start gap-2 rounded-md border border-dashed border-border-strong p-6">
      <p className="text-sm font-semibold text-text-hi">{title}</p>
      {children && <div className="text-sm text-text-mid">{children}</div>}
    </div>
  );
}

export function Skeleton({ className }: { className?: string }) {
  return <div aria-hidden="true" className={cn("skeleton", className)} />;
}

export function PageSkeleton() {
  return (
    <div className="space-y-5" aria-busy="true" aria-label="Loading">
      <Skeleton className="h-4 w-40" />
      <Skeleton className="h-8 w-72 max-w-full" />
      <div className="grid grid-cols-2 gap-3 lg:grid-cols-4">
        {[0, 1, 2, 3].map((i) => (
          <Skeleton key={i} className="h-28" />
        ))}
      </div>
      <div className="grid gap-4 lg:grid-cols-12">
        <Skeleton className="h-72 lg:col-span-5" />
        <Skeleton className="h-72 lg:col-span-7" />
      </div>
    </div>
  );
}

export const stageNames = [
  { key: "purvarupa", sanskrit: "Pūrvarūpa", english: "Early signs", hi: "पूर्वरूप" },
  { key: "nidana", sanskrit: "Nidāna", english: "Cause", hi: "निदान" },
  { key: "samprapti", sanskrit: "Samprāpti", english: "Course", hi: "सम्प्राप्ति" },
  { key: "upasaya", sanskrit: "Upaśaya", english: "Response", hi: "उपशय" },
] as const;

export type StageKey = (typeof stageNames)[number]["key"];

/** Diagnostic spine rail. In-page navigation, always paired with English. */
export function StageRail({
  current,
  targets,
}: {
  current: StageKey;
  targets: Record<StageKey, string>;
}) {
  const currentIndex = stageNames.findIndex((stage) => stage.key === current);
  return (
    <nav aria-label="Diagnostic stage" className="panel-surface overflow-hidden">
      <ol className="grid grid-cols-2 md:grid-cols-4">
        {stageNames.map((stage, index) => {
          const isCurrent = stage.key === current;
          const done = index < currentIndex;
          return (
            <li
              key={stage.key}
              className="min-w-0 border-b border-r border-border-subtle last:border-r-0 md:border-b-0 [&:nth-child(2)]:border-r-0 md:[&:nth-child(2)]:border-r"
            >
              <a
                href={`#${targets[stage.key]}`}
                aria-current={isCurrent ? "step" : undefined}
                className={cn(
                  "flex min-h-16 flex-col justify-center gap-0.5 px-4 py-3 hover:bg-bg-hover",
                  isCurrent && "bg-bg-active",
                )}
              >
                <span className="flex items-center gap-2">
                  <span
                    className={cn(
                      "grid h-5 w-5 shrink-0 place-items-center rounded-full border text-[10px] font-semibold",
                      isCurrent
                        ? "border-accent bg-accent text-on-accent"
                        : done
                          ? "border-accent text-accent-text"
                          : "border-border-strong text-text-lo",
                    )}
                  >
                    {done ? <Check className="h-3 w-3" aria-hidden="true" /> : index + 1}
                  </span>
                  <span className="truncate text-sm font-semibold text-text-hi">
                    {stage.sanskrit}
                  </span>
                </span>
                <span className="pl-7 text-xs text-text-lo">
                  {stage.english}
                  {isCurrent && <span className="font-semibold text-accent-text"> · current</span>}
                </span>
              </a>
            </li>
          );
        })}
      </ol>
    </nav>
  );
}

export function FieldLabelValue({
  label,
  value,
  mono = false,
}: {
  label: string;
  value: ReactNode;
  mono?: boolean;
}) {
  return (
    <div className="min-w-0">
      <dt className="text-xs text-text-lo">{label}</dt>
      <dd
        className={cn("mt-0.5 break-words text-sm font-semibold text-text-hi", mono && "font-data")}
      >
        {value}
      </dd>
    </div>
  );
}

export type { Alert };
