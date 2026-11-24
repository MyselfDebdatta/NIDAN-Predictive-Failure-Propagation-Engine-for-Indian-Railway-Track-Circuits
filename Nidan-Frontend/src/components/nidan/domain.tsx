import { useMemo, useRef, useState, type KeyboardEvent, type ReactNode } from "react";
import { Link } from "@tanstack/react-router";
import * as Dialog from "@radix-ui/react-dialog";
import { ChevronDown, X } from "lucide-react";
import type { Alert, BlockJob, BlockWindow } from "@/data/fixtures";
import { failureModes } from "@/data/fixtures";
import {
  formatAge,
  formatDecimal,
  formatDuration,
  formatRisk,
  formatRul,
  formatShortDate,
  formatWeekday,
} from "@/lib/formatters";
import { blockFitText, deferValidation } from "@/lib/policy";
import {
  BlockFitBadge,
  Chip,
  LevelBadge,
  LevelGlyph,
  levelNames,
  Notice,
  RiskValue,
} from "@/components/nidan/primitives";
import { Button } from "@/components/ui/button";
import { ThemeToggle } from "@/components/shell/ThemeToggle";
import { cn } from "@/lib/utils";

/* ---------------------------------------------------------------- Queue table */

export interface QueueTableProps {
  alerts: Alert[];
  variant: "full" | "compact";
  selected?: Set<string>;
  onSelectionChange?: (next: Set<string>) => void;
  onOpen: (alert: Alert) => void;
  activeId?: string | null;
  caption: string;
  showBlock?: boolean;
}

function fitLabel(alert: Alert) {
  if (!alert.block) return null;
  return blockFitText(alert.block.fit, alert.block.minutes, alert.block.window.durationMin);
}

function BlockCell({ alert }: { alert: Alert }) {
  if (!alert.block)
    return (
      <span aria-label="no block data" className="text-text-lo">
        —
      </span>
    );
  const label = fitLabel(alert) ?? "";
  return (
    <span className="inline-flex flex-wrap items-center gap-1.5">
      <BlockFitBadge fit={alert.block.fit} label={label} />
      {alert.block.fit !== "none" && alert.block.fit !== "special" && (
        <span className="font-data text-xs text-text-lo">{alert.block.window.id}</span>
      )}
    </span>
  );
}

export function QueueTable({
  alerts,
  variant,
  selected,
  onSelectionChange,
  onOpen,
  activeId,
  caption,
  showBlock = true,
}: QueueTableProps) {
  const rowRefs = useRef<Record<string, HTMLElement | null>>({});
  const [anchor, setAnchor] = useState<number | null>(null);
  const [focusIndex, setFocusIndex] = useState(0);
  const selectable = !!selected && !!onSelectionChange;

  const toggle = (index: number, range: boolean) => {
    if (!selected || !onSelectionChange) return;
    const next = new Set(selected);
    const alert = alerts[index];
    if (!alert) return;
    if (range && anchor !== null) {
      const [from, to] = anchor < index ? [anchor, index] : [index, anchor];
      alerts.slice(from, to + 1).forEach((a) => next.add(a.id));
    } else if (next.has(alert.id)) next.delete(alert.id);
    else next.add(alert.id);
    setAnchor(index);
    onSelectionChange(next);
  };

  const onRowKey = (event: KeyboardEvent<HTMLElement>, index: number) => {
    const alert = alerts[index];
    if (!alert) return;
    if (event.target !== event.currentTarget) return;
    if (event.key === "ArrowDown" || event.key === "ArrowUp") {
      event.preventDefault();
      const nextIndex = Math.max(
        0,
        Math.min(alerts.length - 1, index + (event.key === "ArrowDown" ? 1 : -1)),
      );
      setFocusIndex(nextIndex);
      const next = alerts[nextIndex];
      if (next) rowRefs.current[`${variant}-${next.id}`]?.focus();
    } else if (event.key === "Enter") {
      event.preventDefault();
      onOpen(alert);
    } else if (event.key === " " && selectable) {
      event.preventDefault();
      toggle(index, event.shiftKey);
    }
  };

  const allSelected = selectable && alerts.length > 0 && alerts.every((a) => selected?.has(a.id));

  return (
    <div className="min-w-0">
      {/* ≥720px: real table */}
      <div className="hidden min-[720px]:block">
        <table className="w-full table-fixed border-collapse text-left text-sm">
          <caption className="sr-only">
            {caption}. Use up and down arrows to move, Enter to open
            {selectable ? ", Space to select, Shift+Space to select a range" : ""}.
          </caption>
          <thead>
            <tr className="border-b border-border text-xs text-text-lo">
              {selectable && (
                <th scope="col" className="w-11 py-2 pl-2 font-medium">
                  <input
                    type="checkbox"
                    aria-label="Select all visible rows"
                    checked={allSelected}
                    onChange={() =>
                      onSelectionChange?.(
                        allSelected ? new Set() : new Set(alerts.map((a) => a.id)),
                      )
                    }
                    className="h-4 w-4 accent-[var(--accent)]"
                  />
                </th>
              )}
              <th scope="col" className="w-[112px] py-2 font-medium">
                Level
              </th>
              <th scope="col" className="py-2 font-medium">
                Asset
              </th>
              <th scope="col" className="hidden w-[110px] py-2 font-medium 2xl:table-cell">
                Route
              </th>
              <th scope="col" className="hidden w-[70px] py-2 font-medium lg:table-cell">
                Mode
              </th>
              <th scope="col" className="w-[92px] py-2 text-right font-medium">
                {variant === "full" ? "Risk 24 h / 72 h" : "Risk 7 d"}
              </th>
              <th scope="col" className="w-[72px] py-2 text-right font-medium">
                RUL p10
              </th>
              {variant === "full" && (
                <th scope="col" className="hidden w-[80px] py-2 pl-4 font-medium xl:table-cell">
                  Cluster
                </th>
              )}
              {showBlock && (
                <th scope="col" className="hidden w-[150px] py-2 pl-4 font-medium md:table-cell">
                  Block fit
                </th>
              )}
              {variant === "full" && (
                <th
                  scope="col"
                  className="hidden w-[64px] py-2 text-right font-medium lg:table-cell"
                >
                  Age
                </th>
              )}
              {variant === "compact" && (
                <th scope="col" className="w-[84px] py-2 text-right font-medium">
                  <span className="sr-only">Action</span>
                </th>
              )}
            </tr>
          </thead>
          <tbody>
            {alerts.map((alert, index) => {
              const isSelected = selected?.has(alert.id) ?? false;
              const isActive = activeId === alert.id;
              return (
                <tr
                  key={alert.id}
                  ref={(node) => {
                    rowRefs.current[`${variant}-${alert.id}`] = node;
                  }}
                  data-row-id={alert.id}
                  tabIndex={index === focusIndex ? 0 : -1}
                  aria-current={isActive ? "true" : undefined}
                  data-selected={isSelected || undefined}
                  aria-label={`${levelNames[alert.level]} ${alert.assetId}`}
                  onFocus={() => setFocusIndex(index)}
                  onKeyDown={(event) => onRowKey(event, index)}
                  onClick={(event) => {
                    if ((event.target as HTMLElement).closest("input,a,button")) return;
                    onOpen(alert);
                  }}
                  className={cn(
                    "h-11 cursor-pointer border-b border-border-subtle outline-none transition-colors duration-[var(--dur-1)] hover:bg-bg-hover focus-visible:bg-bg-hover focus-visible:outline-2 focus-visible:-outline-offset-2 focus-visible:outline-focus-ring",
                    (isSelected || isActive) && "bg-bg-active",
                    alert.acknowledged && "text-text-mid",
                  )}
                >
                  {selectable && (
                    <td className="py-1.5 pl-2">
                      <input
                        type="checkbox"
                        aria-label={`Select ${alert.assetId}`}
                        checked={isSelected}
                        onChange={() => toggle(index, false)}
                        className="h-4 w-4 accent-[var(--accent)]"
                      />
                    </td>
                  )}
                  <td className="py-1.5">
                    <LevelBadge level={alert.level} />
                  </td>
                  <td className="min-w-0 py-1.5">
                    <span className="block truncate font-data text-[13px] font-semibold text-text-hi">
                      {alert.assetId}
                    </span>
                    <span className="block truncate text-xs text-text-lo 2xl:hidden">
                      {alert.route} · {alert.likelyModes.join(", ")}
                      {alert.acknowledged ? " · acknowledged" : ""}
                    </span>
                    {alert.acknowledged && (
                      <span className="hidden text-xs text-text-lo 2xl:block">
                        Acknowledged · still open
                      </span>
                    )}
                  </td>
                  <td className="hidden truncate py-1.5 text-text-mid 2xl:table-cell">
                    {alert.route}
                  </td>
                  <td
                    className="hidden py-1.5 font-data text-text-mid lg:table-cell"
                    title={failureModes[alert.likelyModes[0] ?? "F12"]}
                  >
                    {alert.likelyModes.join(", ")}
                  </td>
                  <td className="py-1.5 text-right">
                    {variant === "full" ? (
                      <span className="whitespace-nowrap">
                        <RiskValue value={alert.risk.h24} level={alert.level} />{" "}
                        <span className="text-text-lo">/</span>{" "}
                        <RiskValue
                          value={alert.risk.h72}
                          level={alert.level}
                          className="font-normal"
                        />
                      </span>
                    ) : (
                      <RiskValue value={alert.risk.h7d} level={alert.level} />
                    )}
                  </td>
                  <td
                    className="py-1.5 text-right font-data font-semibold text-text-hi"
                    title={`Median ${formatRul(alert.rul.medianDays)}`}
                  >
                    {formatRul(alert.rul.p10Days)}
                  </td>
                  {variant === "full" && (
                    <td className="hidden py-1.5 pl-4 font-data text-xs text-text-mid xl:table-cell">
                      {alert.clusterId ?? <span aria-label="no cluster">—</span>}
                    </td>
                  )}
                  {showBlock && (
                    <td className="hidden py-1.5 pl-4 md:table-cell">
                      <BlockCell alert={alert} />
                    </td>
                  )}
                  {variant === "full" && (
                    <td className="hidden py-1.5 text-right font-data text-xs text-text-lo lg:table-cell">
                      {formatAge(alert.ageMinutes)}
                    </td>
                  )}
                  {variant === "compact" && (
                    <td className="py-1.5 text-right">
                      <Link
                        to="/alerts/$alertId"
                        params={{ alertId: alert.id }}
                        className="inline-flex min-h-11 items-center px-2 text-xs font-semibold text-accent-text underline-offset-4 hover:underline"
                      >
                        Triage<span className="sr-only"> {alert.assetId}</span>
                      </Link>
                    </td>
                  )}
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>

      {/* <720px: definition-list cards with the same accessible names */}
      <ul className="space-y-2 min-[720px]:hidden" aria-label={caption}>
        {alerts.map((alert, index) => {
          const isSelected = selected?.has(alert.id) ?? false;
          return (
            <li
              key={alert.id}
              className={cn(
                "flex items-stretch gap-1 rounded-md border border-border bg-bg-panel",
                (isSelected || activeId === alert.id) && "border-accent bg-bg-active",
              )}
            >
              {selectable && (
                <label className="flex min-w-11 items-start justify-center pt-4">
                  <span className="sr-only">Select {alert.assetId}</span>
                  <input
                    type="checkbox"
                    checked={isSelected}
                    onChange={() => toggle(index, false)}
                    className="h-5 w-5 accent-[var(--accent)]"
                  />
                </label>
              )}
              <button
                type="button"
                ref={(node) => {
                  rowRefs.current[`card-${alert.id}`] = node;
                }}
                data-row-id={alert.id}
                aria-label={`${levelNames[alert.level]} ${alert.assetId}`}
                onClick={() => onOpen(alert)}
                className={cn("min-w-0 flex-1 p-3 text-left", !selectable && "pl-3")}
              >
                <div className="flex flex-wrap items-center justify-between gap-2">
                  <span className="font-data text-sm font-semibold text-text-hi">
                    {alert.assetId}
                  </span>
                  <LevelBadge level={alert.level} />
                </div>
                <p className="mt-0.5 truncate text-xs text-text-lo">
                  {alert.assetName} · {alert.likelyModes.join(", ")}
                  {alert.acknowledged ? " · acknowledged" : ""}
                </p>
                <dl className="mt-3 grid grid-cols-3 gap-2 text-xs">
                  <div>
                    <dt className="text-text-lo">
                      {variant === "full" ? "Risk 24 h" : "Risk 7 d"}
                    </dt>
                    <dd className="mt-0.5 text-sm">
                      <RiskValue
                        value={variant === "full" ? alert.risk.h24 : alert.risk.h7d}
                        level={alert.level}
                      />
                    </dd>
                  </div>
                  <div>
                    <dt className="text-text-lo">RUL p10</dt>
                    <dd className="mt-0.5 font-data text-sm font-semibold text-text-hi">
                      {formatRul(alert.rul.p10Days)}
                    </dd>
                  </div>
                  <div>
                    <dt className="text-text-lo">{variant === "full" ? "Age" : "Risk 72 h"}</dt>
                    <dd className="mt-0.5 font-data text-sm text-text-hi">
                      {variant === "full"
                        ? formatAge(alert.ageMinutes)
                        : formatRisk(alert.risk.h72)}
                    </dd>
                  </div>
                </dl>
                {showBlock && (
                  <div className="mt-3">
                    <BlockCell alert={alert} />
                  </div>
                )}
              </button>
            </li>
          );
        })}
      </ul>
    </div>
  );
}

/* ---------------------------------------------------------------- Why this order */

export function WhyThisOrder({
  alert,
  defaultOpen = true,
}: {
  alert?: Alert;
  defaultOpen?: boolean;
}) {
  const [open, setOpen] = useState(defaultOpen);
  return (
    <section className="panel-surface min-w-0" aria-labelledby="why-order-title">
      <button
        type="button"
        aria-expanded={open}
        onClick={() => setOpen((v) => !v)}
        className="flex min-h-12 w-full items-center justify-between gap-3 px-4 py-3 text-left sm:px-5"
      >
        <span>
          <span className="eyebrow block">Ranking policy</span>
          <span id="why-order-title" className="mt-1 block text-[15px] font-semibold text-text-hi">
            Why this order
          </span>
        </span>
        <ChevronDown
          className={cn(
            "h-4 w-4 shrink-0 text-text-lo transition-transform duration-[var(--dur-2)]",
            open && "rotate-180",
          )}
          aria-hidden="true"
        />
      </button>
      {open && (
        <div className="space-y-3 border-t border-border-subtle px-4 py-4 text-sm leading-6 text-text-mid sm:px-5">
          <p>
            Rank ={" "}
            <strong className="text-text-hi">calibrated risk × consequence × exposure</strong>,
            discounted by <strong className="text-text-hi">data trust</strong>.{" "}
            <strong className="text-text-hi">Block fit</strong> breaks ties. The ranking comes from
            the server policy (v2026.07); this screen does not compute it.
          </p>
          {alert && (
            <dl className="grid gap-2 rounded-sm border border-border-subtle bg-bg-raised p-3 text-xs">
              <div className="flex justify-between gap-3">
                <dt>Policy rank</dt>
                <dd className="font-data font-semibold text-text-hi">#{alert.policyRank}</dd>
              </div>
              <div className="flex justify-between gap-3">
                <dt>Calibrated risk</dt>
                <dd className="font-data font-semibold text-text-hi">
                  {formatRisk(alert.ranking.calibratedRisk)}
                </dd>
              </div>
              <div className="flex justify-between gap-3">
                <dt>Consequence</dt>
                <dd className="text-right text-text-hi">
                  {alert.ranking.consequence} · {alert.ranking.consequenceNote}
                </dd>
              </div>
              <div className="flex justify-between gap-3">
                <dt>Exposure</dt>
                <dd className="text-right text-text-hi">{alert.ranking.exposure}</dd>
              </div>
              <div className="flex justify-between gap-3">
                <dt>Data-trust discount</dt>
                <dd className="font-data font-semibold text-text-hi">
                  × {formatDecimal(alert.ranking.trustDiscount)}
                </dd>
              </div>
              <div className="flex justify-between gap-3">
                <dt>Tie-breaker</dt>
                <dd className="text-right text-text-hi">{alert.ranking.tieBreaker}</dd>
              </div>
            </dl>
          )}
          <p className="text-xs text-text-lo">
            Levels persist for 3 evaluations before they change. Acknowledge means “seen”, not
            “resolved”: alerts close only through a technician outcome or an attributed SSE
            decision.
          </p>
        </div>
      )}
    </section>
  );
}

/* ---------------------------------------------------------------- Dialog frame */

export function SheetDialog({
  open,
  onOpenChange,
  title,
  description,
  children,
  footer,
  side = "center",
}: {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  title: string;
  description?: string;
  children: ReactNode;
  footer?: ReactNode;
  side?: "center" | "right";
}) {
  return (
    <Dialog.Root open={open} onOpenChange={onOpenChange}>
      <Dialog.Portal>
        <Dialog.Overlay className="fixed inset-0 z-50 bg-text-hi/25 data-[state=open]:animate-in data-[state=open]:fade-in-0" />
        <Dialog.Content
          className={cn(
            "fixed z-50 flex flex-col overflow-hidden border-border-strong bg-bg-panel text-text-hi shadow-float outline-none",
            side === "right"
              ? "inset-0 md:inset-y-0 md:left-auto md:right-0 md:w-[min(560px,92vw)] md:border-l drawer-in"
              : "inset-0 sm:inset-auto sm:left-1/2 sm:top-[10dvh] sm:max-h-[84dvh] sm:w-[min(560px,94vw)] sm:-translate-x-1/2 sm:rounded-md sm:border fade-in",
          )}
        >
          <div className="flex shrink-0 items-start justify-between gap-3 border-b border-border px-4 py-3 sm:px-5">
            <div className="min-w-0">
              <Dialog.Title className="text-base font-semibold leading-6 text-text-hi">
                {title}
              </Dialog.Title>
              {description ? (
                <Dialog.Description className="mt-0.5 text-sm text-text-mid">
                  {description}
                </Dialog.Description>
              ) : (
                <Dialog.Description className="sr-only">{title}</Dialog.Description>
              )}
            </div>
            <div className="flex shrink-0 items-center gap-2">
              {/* The drawer is modal, so the theme stays reachable from inside it. */}
              {side === "right" && <ThemeToggle compact className="max-[359px]:hidden" />}
              <Dialog.Close
                className="grid min-h-11 min-w-11 shrink-0 place-items-center rounded-sm border border-border hover:bg-bg-hover"
                aria-label="Close"
              >
                <X className="h-4 w-4" aria-hidden="true" />
              </Dialog.Close>
            </div>
          </div>
          <div className="scrollbar-thin min-h-0 flex-1 overflow-y-auto px-4 py-4 sm:px-5">
            {children}
          </div>
          {footer && (
            <div className="flex shrink-0 flex-wrap items-center justify-end gap-2 border-t border-border bg-bg-chrome px-4 py-3 pb-[max(0.75rem,env(safe-area-inset-bottom))] sm:px-5">
              {footer}
            </div>
          )}
        </Dialog.Content>
      </Dialog.Portal>
    </Dialog.Root>
  );
}

/* ---------------------------------------------------------------- Defer dialog */

export function DeferDialog({
  open,
  onOpenChange,
  alerts,
  onConfirm,
}: {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  alerts: Alert[];
  onConfirm: (request: { reason: string; reviewDate: string }) => void;
}) {
  const [reason, setReason] = useState("");
  const [reviewDate, setReviewDate] = useState("");
  const [errors, setErrors] = useState<{ reason?: string; reviewDate?: string }>({});
  const [summary, setSummary] = useState<{ reason?: string; reviewDate?: string }>({});
  const [submitted, setSubmitted] = useState(false);
  const summaryRef = useRef<HTMLDivElement | null>(null);
  const submit = () => {
    const next = deferValidation({ reason, reviewDate });
    setErrors(next);
    setSummary(next);
    setSubmitted(true);
    if (Object.keys(next).length) {
      window.setTimeout(() => summaryRef.current?.focus(), 0);
      return;
    }
    onConfirm({ reason, reviewDate });
    setReason("");
    setReviewDate("");
    setSubmitted(false);
    setSummary({});
  };
  // The summary only changes on submit, so validating on blur never shifts the layout under the pointer.
  const errorList = Object.entries(summary);
  return (
    <SheetDialog
      open={open}
      onOpenChange={onOpenChange}
      title={`Defer ${alerts.length === 1 ? (alerts[0]?.assetId ?? "alert") : `${alerts.length} alerts`}`}
      description="A deferral needs a reason and a review date. It is attributed to you and reversible."
      footer={
        <>
          <Button variant="outline" onClick={() => onOpenChange(false)}>
            Cancel
          </Button>
          <Button onClick={submit}>
            Defer {alerts.length > 1 ? `${alerts.length} alerts` : "alert"}
          </Button>
        </>
      }
    >
      <div className="space-y-4">
        {submitted && errorList.length > 0 && (
          <div
            ref={summaryRef}
            tabIndex={-1}
            role="alert"
            className="rounded-sm border border-critical bg-critical-wash p-3 text-sm"
          >
            <p className="font-semibold text-critical">
              Fix {errorList.length} {errorList.length === 1 ? "field" : "fields"} to defer
            </p>
            <ul className="mt-1 list-disc pl-5 text-text-hi">
              {errorList.map(([key, message]) => (
                <li key={key}>
                  <a href={`#defer-${key}`} className="underline">
                    {message}
                  </a>
                </li>
              ))}
            </ul>
          </div>
        )}
        <ul className="flex flex-wrap gap-2">
          {alerts.map((a) => (
            <li key={a.id}>
              <Chip tone="mono">
                <LevelGlyph level={a.level} />
                {a.assetId}
              </Chip>
            </li>
          ))}
        </ul>
        <div>
          <label htmlFor="defer-reason" className="text-sm font-semibold text-text-hi">
            Reason
          </label>
          <textarea
            id="defer-reason"
            value={reason}
            onChange={(e) => setReason(e.target.value)}
            onBlur={() => submitted && setErrors(deferValidation({ reason, reviewDate }))}
            rows={3}
            aria-invalid={!!errors.reason}
            aria-describedby={errors.reason ? "defer-reason-error" : undefined}
            className="mt-1.5 w-full rounded-sm border border-border-strong bg-bg-inset p-3 text-sm text-text-hi"
            placeholder="e.g. Crew booked for the same circuit in RB-31"
          />
          <p id="defer-reason-error" className="mt-1 min-h-4 text-xs text-critical">
            {errors.reason ?? ""}
          </p>
        </div>
        <div>
          <label htmlFor="defer-reviewDate" className="text-sm font-semibold text-text-hi">
            Review date
          </label>
          <input
            id="defer-reviewDate"
            type="date"
            min="2026-07-14"
            max="2026-08-14"
            value={reviewDate}
            onChange={(e) => setReviewDate(e.target.value)}
            onBlur={() => submitted && setErrors(deferValidation({ reason, reviewDate }))}
            aria-invalid={!!errors.reviewDate}
            aria-describedby={errors.reviewDate ? "defer-reviewDate-error" : undefined}
            className="mt-1.5 min-h-11 w-full rounded-sm border border-border-strong bg-bg-inset px-3 text-sm text-text-hi"
          />
          <p id="defer-reviewDate-error" className="mt-1 min-h-4 text-xs text-critical">
            {errors.reviewDate ?? ""}
          </p>
        </div>
        <p className="text-xs text-text-lo">
          Deferral does not change risk, RUL, level or cluster membership. The alert returns to
          Triage on the review date.
        </p>
      </div>
    </SheetDialog>
  );
}

/* ---------------------------------------------------------------- Draft SMMS dialog */

export function DraftSmmsDialog({
  open,
  onOpenChange,
  alert,
  action,
  onSave,
  pending,
}: {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  alert: Alert;
  action: string;
  onSave: () => void;
  pending?: boolean;
}) {
  const block = alert.block?.window;
  const rows: [string, string][] = [
    ["Asset", alert.assetId],
    ["Location", alert.assetName],
    [
      "Suspected mode",
      `${alert.likelyModes.join(", ")} · ${failureModes[alert.likelyModes[0] ?? "F12"]}`,
    ],
    ["Proposed work", action],
    [
      "Block",
      block
        ? `${block.id} · ${formatShortDate(block.date)} ${block.start}–${block.end}`
        : "No published block",
    ],
    [
      "Evidence",
      `NIDAN ${alert.id} · risk 7 d ${formatRisk(alert.risk.h7d)} · RUL p10 ${formatRul(alert.rul.p10Days)}`,
    ],
    [
      "Model versions",
      `twin ${alert.modelVersions.twin} · GNN ${alert.modelVersions.gnn} · survival ${alert.modelVersions.survival}`,
    ],
  ];
  return (
    <SheetDialog
      open={open}
      onOpenChange={onOpenChange}
      title="Draft SMMS entry"
      description="Creates a draft for SSE (Sig) review. It does not submit or schedule work."
      footer={
        <>
          <Button variant="outline" onClick={() => onOpenChange(false)}>
            Cancel
          </Button>
          <Button onClick={onSave} disabled={pending}>
            Save draft
          </Button>
        </>
      }
    >
      <dl className="divide-y divide-border-subtle rounded-sm border border-border">
        {rows.map(([label, value]) => (
          <div
            key={label}
            className="grid gap-1 px-3 py-2.5 sm:grid-cols-[140px_minmax(0,1fr)] sm:gap-3"
          >
            <dt className="text-xs text-text-lo">{label}</dt>
            <dd className="break-words text-sm text-text-hi">{value}</dd>
          </div>
        ))}
      </dl>
      <div className="mt-4">
        <Notice tone="neutral" title="System of record">
          SMMS remains the system of record. The draft is attributed to you and waits for SSE (Sig)
          confirmation.
        </Notice>
      </div>
    </SheetDialog>
  );
}

/* ---------------------------------------------------------------- Rolling Block */

export function BlockFitRow({ job, window }: { job: BlockJob; window?: BlockWindow }) {
  const label =
    job.fit === "extends" && window ? `+${job.durationMin - window.durationMin} min` : undefined;
  return (
    <li className="grid min-w-0 gap-2 border-b border-border-subtle py-3 last:border-0 sm:grid-cols-[minmax(0,1fr)_auto] sm:items-center sm:gap-4">
      <div className="min-w-0">
        <p className="text-sm font-semibold text-text-hi">{job.title}</p>
        <p className="mt-0.5 flex flex-wrap gap-x-2 text-xs text-text-lo">
          {job.assets.map((a) => (
            <span key={a} className="font-data">
              {a}
            </span>
          ))}
          <span>· {formatDuration(job.durationMin)}</span>
          <span>· {job.crew}</span>
        </p>
      </div>
      <div className="flex flex-wrap items-center gap-2">
        {window && (
          <span className="font-data text-xs text-text-mid">
            {window.id} · {formatShortDate(window.date)} {window.start}–{window.end}
          </span>
        )}
        <BlockFitBadge fit={job.fit} {...(label ? { label } : {})} />
      </div>
    </li>
  );
}

export function RollingBlockStrip({
  windows,
  jobs,
  highlight,
}: {
  windows: BlockWindow[];
  jobs: BlockJob[];
  highlight?: string;
}) {
  const unfitted = jobs.filter((j) => !j.blockId);
  return (
    <div className="space-y-4">
      <ol className="grid grid-cols-1 gap-2 min-[480px]:grid-cols-2 md:grid-cols-4 xl:grid-cols-7">
        {windows.map((window) => {
          const dayJobs = jobs.filter((j) => j.blockId === window.id);
          const used = dayJobs.reduce((sum, j) => sum + j.durationMin, 0);
          const pct = Math.min(100, Math.round((used / window.durationMin) * 100));
          const over = used > window.durationMin;
          return (
            <li
              key={window.id}
              className={cn(
                "flex min-w-0 flex-col rounded-sm border border-border bg-bg-raised p-3",
                highlight === window.id && "border-accent bg-bg-active",
              )}
            >
              <div className="flex items-baseline justify-between gap-2">
                <span className="text-xs font-semibold text-text-hi">
                  {formatWeekday(window.date)} {formatShortDate(window.date)}
                </span>
                <span className="font-data text-[11px] text-text-lo">{window.id}</span>
              </div>
              <p className="mt-0.5 font-data text-xs text-text-mid">
                {window.start}–{window.end}
              </p>
              <div
                className="mt-2 h-1.5 overflow-hidden rounded-full bg-bg-inset"
                aria-hidden="true"
              >
                <div
                  className={cn("h-full rounded-full", over ? "bg-warning" : "bg-accent")}
                  style={{ width: `${pct}%` }}
                />
              </div>
              <p className="mt-1 text-[11px] text-text-lo">
                {used} of {window.durationMin} min
                {over ? " · over by " + (used - window.durationMin) + " min" : ""}
              </p>
              <ul className="mt-2 space-y-1.5">
                {dayJobs.length === 0 && <li className="text-xs text-text-lo">No job fitted</li>}
                {dayJobs.map((job) => (
                  <li key={job.id} className="min-w-0 text-xs">
                    <span className="block truncate font-data font-semibold text-text-hi">
                      {job.assets.join(", ").replace(/ADRA\/TC\//g, "")}
                    </span>
                    <span className="block truncate text-text-mid">{job.title}</span>
                    <BlockFitBadge
                      fit={job.fit}
                      className="mt-1 min-h-6 px-1.5 text-[11px]"
                      {...(job.fit === "extends"
                        ? { label: `+${job.durationMin - window.durationMin} min` }
                        : {})}
                    />
                  </li>
                ))}
              </ul>
            </li>
          );
        })}
      </ol>
      {unfitted.length > 0 && (
        <div className="rounded-sm border border-dashed border-border-strong p-3">
          <p className="eyebrow">Not in a published block</p>
          <ul className="mt-2 space-y-2">
            {unfitted.map((job) => (
              <li
                key={job.id}
                className="flex flex-wrap items-center justify-between gap-2 text-sm"
              >
                <span className="min-w-0">
                  <span className="font-data font-semibold text-text-hi">
                    {job.assets.join(", ")}
                  </span>{" "}
                  <span className="text-text-mid">
                    · {job.title} · {formatDuration(job.durationMin)}
                  </span>
                </span>
                <BlockFitBadge fit={job.fit} />
              </li>
            ))}
          </ul>
        </div>
      )}
    </div>
  );
}

/* ---------------------------------------------------------------- Asset record */

export function AssetRecordList({
  record,
  trust,
}: {
  record: {
    lengthM: number;
    circuitType: string;
    installed: string;
    codalLifeYears: number;
    relay: string;
    supply: string;
    cable: string;
    relayRoom: string;
    weatherCell: string;
    provenance: string;
  };
  trust: { score: number; flags: string[] };
}) {
  const installedYear = Number(record.installed.slice(0, 4));
  const age = 2026 - installedYear;
  const rows: [string, string, boolean?][] = [
    ["Length · type", `${record.lengthM} m · ${record.circuitType}`],
    ["Installed", `${formatShortDate(record.installed)} ${installedYear} · ${age} y`],
    [
      "Codal life",
      `${record.codalLifeYears} y${age > record.codalLifeYears ? ` · exceeded by ${age - record.codalLifeYears} y` : ""}`,
    ],
    ["Track relay", record.relay, true],
    ["Power supply", record.supply, true],
    ["Cable", record.cable, true],
    ["Relay room", record.relayRoom, true],
    ["Weather cell", record.weatherCell, true],
  ];
  return (
    <div className="space-y-3">
      <dl className="divide-y divide-border-subtle">
        {rows.map(([label, value, mono]) => (
          <div key={label} className="grid grid-cols-[minmax(0,110px)_minmax(0,1fr)] gap-3 py-2">
            <dt className="text-xs text-text-lo">{label}</dt>
            <dd
              className={cn(
                "break-words text-right text-sm text-text-hi",
                mono && "font-data text-[13px]",
              )}
            >
              {value}
            </dd>
          </div>
        ))}
        <div className="grid grid-cols-[minmax(0,110px)_minmax(0,1fr)] gap-3 py-2">
          <dt className="text-xs text-text-lo">Data trust</dt>
          <dd className="text-right text-sm text-text-hi">
            <Link
              to="/models"
              hash="data-trust"
              className="font-data font-semibold text-warning underline underline-offset-4"
            >
              {formatDecimal(trust.score)}
            </Link>
            {trust.flags.map((flag) => (
              <span key={flag} className="mt-1 block font-data text-[11px] text-text-lo">
                {flag}
              </span>
            ))}
          </dd>
        </div>
      </dl>
      <p className="text-xs text-text-lo">
        Provenance: {record.provenance}. Read-only; SMMS is the system of record.
      </p>
    </div>
  );
}

export function useSelection() {
  const [selected, setSelected] = useState<Set<string>>(new Set());
  return useMemo(
    () => ({ selected, setSelected, clear: () => setSelected(new Set()) }),
    [selected],
  );
}
