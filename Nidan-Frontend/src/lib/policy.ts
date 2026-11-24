import type { Alert, AlertLevel, BlockFit } from "@/data/fixtures";

/** Bulk selection cap (§9.3). */
export const BULK_CAP = 50;

export const levelRank: Record<AlertLevel, number> = { critical: 0, warning: 1, watch: 2 };

/** Policy rank is produced by the server; the browser only sorts by it. */
export function byPolicyRank(alerts: Alert[]) {
  return [...alerts].sort((a, b) => a.policyRank - b.policyRank);
}

export function bulkDeferBlocker(selected: Alert[]): string | null {
  if (selected.length === 0) return "Select at least one alert.";
  if (selected.length > BULK_CAP) return `Bulk actions are capped at ${BULK_CAP} rows.`;
  if (selected.some((alert) => alert.level === "critical"))
    return "A Critical alert cannot be deferred in bulk. Open it and defer it on its own.";
  return null;
}

export function deferValidation(request: { reason: string; reviewDate: string }) {
  const errors: { reason?: string; reviewDate?: string } = {};
  if (request.reason.trim().length < 10) errors.reason = "Give a reason of at least 10 characters.";
  if (!/^\d{4}-\d{2}-\d{2}$/.test(request.reviewDate)) errors.reviewDate = "Choose a review date.";
  return errors;
}

export const blockFitLabel: Record<BlockFit, string> = {
  fits: "Fits",
  extends: "+20 min",
  special: "Special",
  none: "No published block",
};

export function blockFitText(fit: BlockFit, minutes: number, windowMinutes: number) {
  if (fit === "extends") return `+${Math.max(0, minutes - windowMinutes)} min`;
  return blockFitLabel[fit];
}

export interface AlertFilters {
  level?: AlertLevel;
  mode?: string;
  route?: string;
  cluster?: string;
  fit?: BlockFit;
  trust?: "low" | "ok";
  q?: string;
  view?: "triage" | "cluster" | "block" | "deferred";
}

export function filterAlerts(alerts: Alert[], filters: AlertFilters) {
  const q = filters.q?.trim().toLowerCase();
  return byPolicyRank(alerts).filter((alert) => {
    const isDeferred = Boolean(alert.deferral);
    if ((filters.view ?? "triage") === "deferred" ? !isDeferred : isDeferred) return false;
    if (filters.level && alert.level !== filters.level) return false;
    if (filters.mode && !alert.likelyModes.includes(filters.mode as Alert["likelyModes"][number]))
      return false;
    if (filters.route && alert.route !== filters.route) return false;
    if (filters.cluster && alert.clusterId !== filters.cluster) return false;
    if (filters.fit && alert.block?.fit !== filters.fit) return false;
    if (filters.trust === "low" && alert.dataTrust.score >= 0.7) return false;
    if (filters.trust === "ok" && alert.dataTrust.score < 0.7) return false;
    if (
      q &&
      !`${alert.assetId} ${alert.assetName} ${alert.id} ${alert.clusterId ?? ""}`
        .toLowerCase()
        .includes(q)
    )
      return false;
    return true;
  });
}
