import { Command } from "cmdk";
import { useNavigate } from "@tanstack/react-router";
import { useQuery } from "@tanstack/react-query";
import { FileText, ListOrdered, Network, CircuitBoard, CornerDownLeft } from "lucide-react";
import { alertsQuery, clustersQuery } from "@/lib/queries";
import { searchIndex } from "@/data/fixtures";
import { useUi } from "@/stores/ui";
import { useT } from "@/i18n/strings";
import { LevelGlyph, levelNames } from "@/components/nidan/primitives";

const groupClass =
  "[&_[cmdk-group-heading]]:eyebrow [&_[cmdk-group-heading]]:px-3 [&_[cmdk-group-heading]]:pb-1 [&_[cmdk-group-heading]]:pt-3";
const itemClass =
  "flex min-h-11 cursor-pointer items-center gap-3 rounded-sm px-3 text-sm text-text-mid data-[selected=true]:bg-bg-active data-[selected=true]:text-text-hi";

/** Global Ctrl/⌘ K palette. It only navigates; it never executes a command. */
export function CommandPalette() {
  const open = useUi((s) => s.paletteOpen);
  const setOpen = useUi((s) => s.setPaletteOpen);
  const navigate = useNavigate();
  const { t } = useT();
  const { data: alerts = [] } = useQuery(alertsQuery);
  const { data: clusters = [] } = useQuery(clustersQuery);

  const go = (fn: () => void) => {
    setOpen(false);
    fn();
  };

  return (
    <Command.Dialog
      open={open}
      onOpenChange={setOpen}
      label="Search NIDAN"
      overlayClassName="fixed inset-0 z-50 bg-text-hi/25"
      contentClassName="fixed inset-x-3 top-[8dvh] z-50 mx-auto max-w-xl overflow-hidden rounded-md border border-border-strong bg-bg-panel text-text-hi shadow-float sm:inset-x-6"
    >
      <div className="flex items-center gap-2 border-b border-border px-3">
        <Command.Input
          placeholder={t("search.placeholder")}
          className="min-h-12 w-full bg-transparent text-[15px] text-text-hi outline-none placeholder:text-text-lo"
        />
        <kbd className="hidden rounded-xs border border-border px-1.5 font-data text-[11px] text-text-lo sm:inline">
          Esc
        </kbd>
      </div>
      <Command.List className="scrollbar-thin max-h-[60dvh] overflow-y-auto p-1.5">
        <Command.Empty className="px-3 py-6 text-sm text-text-mid">
          No asset, alert, cluster or SMMS ID matches.
        </Command.Empty>
        <Command.Group heading="Assets" className={groupClass}>
          {alerts.map((alert) => (
            <Command.Item
              key={`asset-${alert.assetId}`}
              value={`asset ${alert.assetId} ${alert.assetName}`}
              onSelect={() =>
                go(() => navigate({ to: "/assets/$assetId", params: { assetId: alert.assetId } }))
              }
              className={itemClass}
            >
              <CircuitBoard className="h-4 w-4 shrink-0 text-text-lo" aria-hidden="true" />
              <span className="font-data text-text-hi">{alert.assetId}</span>
              <span className="truncate text-xs text-text-lo">{alert.assetName}</span>
            </Command.Item>
          ))}
        </Command.Group>
        <Command.Group heading="Alerts" className={groupClass}>
          {alerts.map((alert) => (
            <Command.Item
              key={`alert-${alert.id}`}
              value={`alert ${alert.id} ${alert.assetId} ${alert.level}`}
              onSelect={() =>
                go(() => navigate({ to: "/alerts/$alertId", params: { alertId: alert.id } }))
              }
              className={itemClass}
            >
              <ListOrdered className="h-4 w-4 shrink-0 text-text-lo" aria-hidden="true" />
              <LevelGlyph level={alert.level} />
              <span className="text-text-hi">{levelNames[alert.level]}</span>
              <span className="truncate font-data text-xs text-text-lo">
                {alert.id} · {alert.assetId}
              </span>
            </Command.Item>
          ))}
        </Command.Group>
        <Command.Group heading="Clusters" className={groupClass}>
          {clusters.map((cluster) => (
            <Command.Item
              key={cluster.id}
              value={`cluster ${cluster.id} ${cluster.title}`}
              onSelect={() => go(() => navigate({ to: "/clusters", hash: cluster.id }))}
              className={itemClass}
            >
              <Network className="h-4 w-4 shrink-0 text-text-lo" aria-hidden="true" />
              <span className="font-data text-text-hi">{cluster.id}</span>
              <span className="truncate text-xs text-text-lo">{cluster.title}</span>
            </Command.Item>
          ))}
        </Command.Group>
        <Command.Group heading="SMMS records" className={groupClass}>
          {searchIndex.smms.map((id) => (
            <Command.Item
              key={id}
              value={`smms ${id}`}
              onSelect={() =>
                go(() =>
                  navigate({
                    to: "/assets/$assetId",
                    params: { assetId: "ADRA/TC/12T" },
                    hash: "explanation",
                  }),
                )
              }
              className={itemClass}
            >
              <FileText className="h-4 w-4 shrink-0 text-text-lo" aria-hidden="true" />
              <span className="font-data text-text-hi">{id}</span>
              <span className="truncate text-xs text-text-lo">Precedent · read-only</span>
            </Command.Item>
          ))}
        </Command.Group>
      </Command.List>
      <div className="flex items-center gap-3 border-t border-border px-3 py-2 text-[11px] text-text-lo">
        <span className="inline-flex items-center gap-1">
          <CornerDownLeft className="h-3 w-3" aria-hidden="true" />
          open
        </span>
        <span>↑↓ move</span>
        <span className="ml-auto">Navigates only · never executes a command</span>
      </div>
    </Command.Dialog>
  );
}
