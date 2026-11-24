import { createFileRoute, Outlet, useNavigate, useParams } from "@tanstack/react-router";
import { useSuspenseQuery } from "@tanstack/react-query";
import { useMemo, useRef, useState, type KeyboardEvent, type ReactNode } from "react";
import { Download, GitMerge, Search, SlidersHorizontal, UserPlus, X } from "lucide-react";
import { toast } from "sonner";
import type { Alert, AlertLevel, BlockFit } from "@/data/fixtures";
import { failureModes } from "@/data/fixtures";
import { alertsQuery, kpisQuery } from "@/lib/queries";
import { BULK_CAP, bulkDeferBlocker, filterAlerts, type AlertFilters } from "@/lib/policy";
import { useDefer, useUndefer } from "@/lib/mutations";
import {
  Chip,
  EmptyState,
  KpiTile,
  LevelGlyph,
  PageHeading,
  PageSkeleton,
  Panel,
} from "@/components/nidan/primitives";
import { DeferDialog, QueueTable, SheetDialog, WhyThisOrder } from "@/components/nidan/domain";
import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";

const levels: AlertLevel[] = ["critical", "warning", "watch"];
const fits: BlockFit[] = ["fits", "extends", "special", "none"];
const views = ["triage", "cluster", "block", "deferred"] as const;

function pickEnum<T extends string>(value: unknown, allowed: readonly T[]): T | undefined {
  return typeof value === "string" && (allowed as readonly string[]).includes(value)
    ? (value as T)
    : undefined;
}

/** Filters, view and drawer state live in the URL. All keys optional. */
export function validateAlertSearch(search: Record<string, unknown>): AlertFilters {
  const out: AlertFilters = {};
  const level = pickEnum(search["level"], levels);
  const fit = pickEnum(search["fit"], fits);
  const trust = pickEnum(search["trust"], ["low", "ok"] as const);
  const view = pickEnum(search["view"], views);
  if (level) out.level = level;
  if (fit) out.fit = fit;
  if (trust) out.trust = trust;
  if (view && view !== "triage") out.view = view;
  for (const key of ["mode", "route", "cluster", "q"] as const) {
    const value = search[key];
    if (typeof value === "string" && value.trim()) out[key] = value;
  }
  return out;
}

export const Route = createFileRoute("/alerts")({
  validateSearch: validateAlertSearch,
  head: () => ({
    meta: [
      { title: "Alert queue · what to work next and why — NIDAN" },
      {
        name: "description",
        content:
          "Policy-ranked track-circuit alerts with filters, saved views, safe bulk actions and a persistent explanation of the ranking.",
      },
      { property: "og:title", content: "NIDAN alert queue" },
      {
        property: "og:description",
        content: "What do I work next, and why is it ranked above the row below it?",
      },
      { property: "og:type", content: "website" },
      { name: "twitter:card", content: "summary_large_image" },
    ],
  }),
  loader: ({ context }) =>
    Promise.all([
      context.queryClient.ensureQueryData(alertsQuery),
      context.queryClient.ensureQueryData(kpisQuery),
    ]),
  pendingComponent: PageSkeleton,
  component: AlertQueue,
});

const savedViews: { id: string; label: string; filters: AlertFilters }[] = [
  { id: "default", label: "My section (default)", filters: {} },
  { id: "urgent", label: "Warnings to plan", filters: { level: "warning" } },
  { id: "trust", label: "Low data trust", filters: { trust: "low" } },
  { id: "cluster", label: "Cluster c-9917", filters: { cluster: "c-9917" } },
];

function FilterSelect({
  label,
  value,
  onChange,
  children,
}: {
  label: string;
  value: string;
  onChange: (value: string) => void;
  children: ReactNode;
}) {
  const id = `filter-${label.toLowerCase().replace(/\s+/g, "-")}`;
  return (
    <div className="min-w-0">
      <label htmlFor={id} className="mb-1 block text-[11px] font-medium text-text-lo">
        {label}
      </label>
      <select
        id={id}
        value={value}
        onChange={(e) => onChange(e.target.value)}
        className={cn(
          "min-h-11 w-full min-w-0 rounded-sm border bg-bg-inset px-2.5 text-sm text-text-hi",
          value ? "border-accent" : "border-border",
        )}
      >
        {children}
      </select>
    </div>
  );
}

function AlertQueue() {
  const { data: alerts } = useSuspenseQuery(alertsQuery);
  const { data: kpis } = useSuspenseQuery(kpisQuery);
  const search = Route.useSearch();
  const navigate = useNavigate({ from: "/alerts" });
  const params = useParams({ strict: false }) as { alertId?: string };
  const [selected, setSelected] = useState<Set<string>>(new Set());
  const [deferOpen, setDeferOpen] = useState(false);
  const [mergeOpen, setMergeOpen] = useState(false);
  const [filtersOpen, setFiltersOpen] = useState(false);
  const defer = useDefer();
  const undefer = useUndefer();

  const visible = useMemo(() => filterAlerts(alerts, search), [alerts, search]);
  const routes = useMemo(() => [...new Set(alerts.map((a) => a.route))].sort(), [alerts]);
  const clusters = useMemo(
    () => [...new Set(alerts.map((a) => a.clusterId).filter((c): c is string => !!c))],
    [alerts],
  );
  const modes = useMemo(
    () =>
      [...new Set(alerts.flatMap((a) => a.likelyModes))].sort(
        (a, b) => Number(a.slice(1)) - Number(b.slice(1)),
      ),
    [alerts],
  );
  const selectedAlerts = alerts.filter((a) => selected.has(a.id));
  const deferBlocker = bulkDeferBlocker(selectedAlerts);
  const view = search.view ?? "triage";
  const deferredCount = alerts.filter((a) => a.deferral).length;
  const activeFilterCount = (
    ["level", "mode", "route", "cluster", "fit", "trust", "q"] as const
  ).filter((k) => search[k]).length;

  // Roving tabindex + arrow keys, as expected of a real tablist.
  const tabRefs = useRef<(HTMLButtonElement | null)[]>([]);
  const onTabKeyDown = (event: KeyboardEvent<HTMLButtonElement>, index: number) => {
    const nextIndex =
      event.key === "Home"
        ? 0
        : event.key === "End"
          ? views.length - 1
          : event.key === "ArrowRight"
            ? (index + 1) % views.length
            : event.key === "ArrowLeft"
              ? (index - 1 + views.length) % views.length
              : null;
    if (nextIndex === null) return;
    event.preventDefault();
    tabRefs.current[nextIndex]?.focus();
    setSelected(new Set());
    void navigate({
      search: (prev) => validateAlertSearch({ ...prev, view: views[nextIndex] }),
      replace: true,
    });
  };

  const setFilter = (key: keyof AlertFilters, value: string) => {
    setSelected(new Set());
    void navigate({
      search: (prev) => validateAlertSearch({ ...prev, [key]: value || undefined }),
      replace: true,
    });
  };

  const openAlert = (alert: Alert) =>
    void navigate({
      to: "/alerts/$alertId",
      params: { alertId: alert.id },
      search: (prev) => prev,
    });

  const groups: { key: string; title: string; rows: Alert[] }[] =
    view === "cluster"
      ? [...new Set(visible.map((a) => a.clusterId ?? "none"))].map((key) => ({
          key,
          title: key === "none" ? "No cluster" : `Cluster ${key}`,
          rows: visible.filter((a) => (a.clusterId ?? "none") === key),
        }))
      : view === "block"
        ? [
            ...new Set(
              visible.map((a) =>
                a.block && a.block.fit !== "none" && a.block.fit !== "special"
                  ? a.block.window.id
                  : "unplanned",
              ),
            ),
          ]
            .sort()
            .map((key) => ({
              key,
              title: key === "unplanned" ? "Needs a special block or none published" : key,
              rows: visible.filter(
                (a) =>
                  (a.block && a.block.fit !== "none" && a.block.fit !== "special"
                    ? a.block.window.id
                    : "unplanned") === key,
              ),
            }))
        : [{ key: "all", title: "", rows: visible }];

  return (
    <div className="space-y-5 lg:space-y-6">
      <PageHeading
        eyebrow="SER / ADRA · queue"
        title="Alert queue"
        titleHi="अलर्ट कतार"
        subtitle="Ranked by policy, not by alphabet. Open a row to triage it; acknowledge means seen, not resolved."
      >
        <Chip tone="mono">Snapshot 00:20 IST · fresh</Chip>
        <Chip>
          <LevelGlyph level="critical" />1 Critical
        </Chip>
        <Chip>
          <LevelGlyph level="warning" />3 Warning
        </Chip>
        <Chip>
          <LevelGlyph level="watch" />7 Watch
        </Chip>
      </PageHeading>

      <div className="grid grid-cols-2 gap-3 lg:grid-cols-4 lg:gap-4">
        <KpiTile
          label="Open"
          value={String(kpis.queue.open)}
          delta={`${deferredCount} deferred`}
          note="All levels in scope"
        />
        <KpiTile
          label="Critical"
          value={String(kpis.queue.critical)}
          delta="21 min old"
          note="Cannot be bulk-deferred"
          tone="critical"
          glyph="critical"
        />
        <KpiTile
          label="Watch"
          value={String(kpis.queue.watch)}
          delta="3 evaluations"
          note="7 d risk > 20% or RUL p10 < 30 d"
          tone="watch"
          glyph="watch"
        />
        <KpiTile
          label="Median age"
          value={`${kpis.queue.medianAgeHours} h`}
          delta="−0.4 h"
          note="Since first evaluation"
        />
      </div>

      <button
        type="button"
        aria-expanded={filtersOpen}
        aria-controls="queue-filters"
        onClick={() => setFiltersOpen((v) => !v)}
        className="flex min-h-11 w-full items-center justify-between gap-2 rounded-md border border-border bg-bg-panel px-4 text-sm font-semibold text-text-hi md:hidden"
      >
        <span className="inline-flex items-center gap-2">
          <SlidersHorizontal className="h-4 w-4" aria-hidden="true" />
          Filters &amp; saved views
        </span>
        <span className="font-data text-xs text-text-lo">
          {activeFilterCount ? `${activeFilterCount} active` : "none"}
        </span>
      </button>
      <section
        id="queue-filters"
        aria-label="Filters"
        className={cn("panel-surface p-4 md:block", filtersOpen ? "block" : "hidden")}
      >
        <div className="grid grid-cols-2 gap-3 sm:grid-cols-3 lg:grid-cols-4 xl:grid-cols-8">
          <div className="col-span-2 sm:col-span-3 lg:col-span-4 xl:col-span-2">
            <label
              htmlFor="queue-search"
              className="mb-1 block text-[11px] font-medium text-text-lo"
            >
              Search{" "}
              <kbd className="ml-1 rounded-xs border border-border px-1 font-data text-[10px]">
                /
              </kbd>
            </label>
            <div className="relative">
              <Search
                className="pointer-events-none absolute left-2.5 top-1/2 h-4 w-4 -translate-y-1/2 text-text-lo"
                aria-hidden="true"
              />
              <input
                id="queue-search"
                data-page-search
                type="search"
                defaultValue={search.q ?? ""}
                onKeyDown={(e) => {
                  if (e.key === "Enter") setFilter("q", e.currentTarget.value);
                }}
                onBlur={(e) => setFilter("q", e.currentTarget.value)}
                placeholder="Asset, alert or cluster"
                className="min-h-11 w-full rounded-sm border border-border bg-bg-inset pl-8 pr-2 text-sm text-text-hi placeholder:text-text-lo"
              />
            </div>
          </div>
          <FilterSelect
            label="Level"
            value={search.level ?? ""}
            onChange={(v) => setFilter("level", v)}
          >
            <option value="">All levels</option>
            <option value="critical">Critical</option>
            <option value="warning">Warning</option>
            <option value="watch">Watch</option>
          </FilterSelect>
          <FilterSelect
            label="Failure mode"
            value={search.mode ?? ""}
            onChange={(v) => setFilter("mode", v)}
          >
            <option value="">All modes</option>
            {modes.map((m) => (
              <option key={m} value={m}>
                {m} · {failureModes[m]}
              </option>
            ))}
          </FilterSelect>
          <FilterSelect
            label="Route"
            value={search.route ?? ""}
            onChange={(v) => setFilter("route", v)}
          >
            <option value="">All routes</option>
            {routes.map((r) => (
              <option key={r} value={r}>
                {r}
              </option>
            ))}
          </FilterSelect>
          <FilterSelect
            label="Cluster"
            value={search.cluster ?? ""}
            onChange={(v) => setFilter("cluster", v)}
          >
            <option value="">Any cluster</option>
            {clusters.map((c) => (
              <option key={c} value={c}>
                {c}
              </option>
            ))}
          </FilterSelect>
          <FilterSelect
            label="Block fit"
            value={search.fit ?? ""}
            onChange={(v) => setFilter("fit", v)}
          >
            <option value="">Any fit</option>
            <option value="fits">Fits</option>
            <option value="extends">Extends</option>
            <option value="special">Special</option>
            <option value="none">No published block</option>
          </FilterSelect>
          <FilterSelect
            label="Data trust"
            value={search.trust ?? ""}
            onChange={(v) => setFilter("trust", v)}
          >
            <option value="">Any trust</option>
            <option value="low">Low (&lt; 0.70)</option>
            <option value="ok">0.70 and above</option>
          </FilterSelect>
        </div>
        <div className="mt-3 flex flex-wrap items-end justify-between gap-3 border-t border-border-subtle pt-3">
          <div className="w-full min-w-0 sm:w-64">
            <FilterSelect
              label="Saved view"
              value=""
              onChange={(id) => {
                const v = savedViews.find((s) => s.id === id);
                if (v) void navigate({ search: v.filters, replace: true });
              }}
            >
              <option value="">Apply a saved view…</option>
              {savedViews.map((v) => (
                <option key={v.id} value={v.id}>
                  {v.label}
                </option>
              ))}
            </FilterSelect>
          </div>
          {activeFilterCount > 0 && (
            <Button
              variant="ghost"
              onClick={() =>
                void navigate({ search: view === "triage" ? {} : { view }, replace: true })
              }
            >
              <X aria-hidden="true" />
              Clear {activeFilterCount} {activeFilterCount === 1 ? "filter" : "filters"}
            </Button>
          )}
        </div>
      </section>

      <div className="grid gap-5 2xl:grid-cols-[minmax(0,1fr)_340px]">
        <div className="min-w-0 space-y-3">
          <div
            role="tablist"
            aria-label="Queue view"
            className="flex gap-1 overflow-x-auto border-b border-border"
          >
            {views.map((v, index) => {
              const label = {
                triage: "Triage",
                cluster: "By cluster",
                block: "By block",
                deferred: `Deferred (${deferredCount})`,
              }[v];
              const selected = view === v;
              return (
                <button
                  key={v}
                  ref={(node) => {
                    tabRefs.current[index] = node;
                  }}
                  id={`queue-view-tab-${v}`}
                  type="button"
                  role="tab"
                  aria-selected={selected}
                  aria-controls="queue-view-panel"
                  tabIndex={selected ? 0 : -1}
                  onKeyDown={(event) => onTabKeyDown(event, index)}
                  onClick={() => {
                    setSelected(new Set());
                    void navigate({
                      search: (prev) => validateAlertSearch({ ...prev, view: v }),
                      replace: true,
                    });
                  }}
                  className={cn(
                    "min-h-11 shrink-0 border-b-2 px-3 text-sm font-semibold",
                    selected
                      ? "border-accent text-text-hi"
                      : "border-transparent text-text-lo hover:text-text-hi",
                  )}
                >
                  {label}
                </button>
              );
            })}
          </div>

          {selected.size > 0 && (
            <div
              role="region"
              aria-label="Bulk actions"
              className="sticky top-16 z-20 flex flex-wrap items-center gap-2 rounded-md border border-accent bg-bg-panel p-2 shadow-float"
            >
              <span className="px-2 text-sm font-semibold text-text-hi">
                <span className="font-data">{selected.size}</span> selected
                <span className="text-text-lo"> · max {BULK_CAP}</span>
              </span>
              <Button
                size="sm"
                variant="outline"
                onClick={() =>
                  toast.success(`${selected.size} alerts assigned to ESM gang 1`, {
                    description: "Assignment is a draft until the SSE confirms.",
                  })
                }
              >
                <UserPlus aria-hidden="true" />
                Assign
              </Button>
              <Button size="sm" variant="outline" onClick={() => setMergeOpen(true)}>
                <GitMerge aria-hidden="true" />
                Merge to cluster
              </Button>
              {view === "deferred" ? (
                <Button
                  size="sm"
                  variant="outline"
                  onClick={() => {
                    undefer.mutate([...selected]);
                    toast.success(`${selected.size} returned to triage`);
                    setSelected(new Set());
                  }}
                >
                  Return to triage
                </Button>
              ) : (
                <Button
                  size="sm"
                  variant="outline"
                  disabled={!!deferBlocker}
                  aria-describedby={deferBlocker ? "defer-blocker" : undefined}
                  onClick={() => setDeferOpen(true)}
                >
                  Defer
                </Button>
              )}
              <Button
                size="sm"
                variant="ghost"
                onClick={() =>
                  toast.success(`Exported ${selected.size} rows`, {
                    description: "CSV with policy rank and evidence.",
                  })
                }
              >
                <Download aria-hidden="true" />
                Export
              </Button>
              <Button size="sm" variant="ghost" onClick={() => setSelected(new Set())}>
                Clear
              </Button>
              {deferBlocker && view !== "deferred" && (
                <p id="defer-blocker" className="w-full px-2 text-xs text-critical">
                  {deferBlocker}
                </p>
              )}
            </div>
          )}

          <div
            role="tabpanel"
            id="queue-view-panel"
            aria-labelledby={`queue-view-tab-${view}`}
            tabIndex={0}
            className="panel-surface p-2 sm:p-3"
          >
            {visible.length === 0 ? (
              <EmptyState title="Nothing matches these filters">
                <button
                  className="mt-1 min-h-11 font-semibold text-accent-text underline"
                  onClick={() => void navigate({ search: {}, replace: true })}
                >
                  Clear filters
                </button>
              </EmptyState>
            ) : (
              groups.map((group) => (
                <div key={group.key} className={cn(group.title && "mb-4 last:mb-0")}>
                  {group.title && (
                    <h3 className="eyebrow px-2 pb-2 pt-1">
                      {group.title} · {group.rows.length}
                    </h3>
                  )}
                  <QueueTable
                    variant="full"
                    caption={group.title || "Alert queue"}
                    alerts={group.rows}
                    selected={selected}
                    onSelectionChange={(next) => setSelected(new Set([...next].slice(0, BULK_CAP)))}
                    onOpen={openAlert}
                    activeId={params.alertId ?? null}
                  />
                </div>
              ))
            )}
          </div>
          <p className="px-1 text-xs text-text-lo">
            Keyboard: ↑/↓ move · Enter open · Space select · Shift+Space range · / search · Ctrl K
            palette
          </p>
        </div>
        <aside className="grid min-w-0 gap-4 lg:grid-cols-2 2xl:sticky 2xl:top-20 2xl:grid-cols-1 2xl:self-start">
          <WhyThisOrder />
          <Panel title="Queue discipline" eyebrow="Safety">
            <ul className="space-y-2 text-sm leading-6 text-text-mid">
              <li>Bulk actions state their count and cap at {BULK_CAP} rows.</li>
              <li>A Critical alert can never be deferred in bulk.</li>
              <li>Every defer needs a reason and a review date.</li>
              <li>Nothing here closes an alert or touches interlocking.</li>
            </ul>
          </Panel>
        </aside>
      </div>

      <DeferDialog
        open={deferOpen}
        onOpenChange={setDeferOpen}
        alerts={selectedAlerts}
        onConfirm={(request) => {
          defer.mutate({ ids: selectedAlerts.map((a) => a.id), request });
          toast.success(`${selectedAlerts.length} deferred until ${request.reviewDate}`, {
            action: {
              label: "Undo",
              onClick: () => undefer.mutate(selectedAlerts.map((a) => a.id)),
            },
          });
          setDeferOpen(false);
          setSelected(new Set());
        }}
      />
      <SheetDialog
        open={mergeOpen}
        onOpenChange={setMergeOpen}
        title="Preview cluster merge"
        description="Nothing changes until you confirm. Membership is reviewed by the GNN on the next evaluation."
        footer={
          <>
            <Button variant="outline" onClick={() => setMergeOpen(false)}>
              Cancel
            </Button>
            <Button
              onClick={() => {
                toast.success("Merge proposal drafted", {
                  description: `${selectedAlerts.length} alerts proposed for c-9917. Awaiting SSE review.`,
                });
                setMergeOpen(false);
                setSelected(new Set());
              }}
            >
              Propose merge
            </Button>
          </>
        }
      >
        <p className="text-sm text-text-mid">
          Resulting membership of{" "}
          <span className="font-data font-semibold text-text-hi">c-9917</span>:
        </p>
        <ul className="mt-3 space-y-1.5">
          {[
            ...new Set([
              "ADRA/TC/12T",
              "ADRA/TC/14T",
              "ADRA/TC/16T",
              ...selectedAlerts.map((a) => a.assetId),
            ]),
          ].map((id) => (
            <li
              key={id}
              className="flex items-center justify-between gap-2 rounded-sm border border-border-subtle px-3 py-2 text-sm"
            >
              <span className="font-data text-text-hi">{id}</span>
              <span className="text-xs text-text-lo">
                {["ADRA/TC/12T", "ADRA/TC/14T", "ADRA/TC/16T"].includes(id)
                  ? "existing"
                  : "proposed"}
              </span>
            </li>
          ))}
        </ul>
      </SheetDialog>

      <Outlet />
    </div>
  );
}
