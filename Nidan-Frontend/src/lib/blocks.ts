import { snapshot, type Alert } from "@/data/fixtures";

const DAY_MS = 86_400_000;

/**
 * Whole calendar days from the demo snapshot to the alert's published block.
 * Returns null when the alert has no published block, so callers render a
 * "no block" state instead of inventing a date.
 */
export function daysUntilBlock(alert: Alert): number | null {
  const date = alert.block?.window.date;
  if (!date) return null;
  const from = Date.parse(`${snapshot.date}T00:00:00Z`);
  const to = Date.parse(`${date}T00:00:00Z`);
  if (Number.isNaN(from) || Number.isNaN(to)) return null;
  return Math.round((to - from) / DAY_MS);
}

/** Short, human label for a block offset: "today", "tomorrow", "in 2 d". */
export function blockWhenLabel(days: number): string {
  if (days <= 0) return "today";
  if (days === 1) return "tomorrow";
  return `in ${days} d`;
}

/** True when the block falls inside the p10 planning horizon. */
export function blockInsideP10(alert: Alert, days: number | null = daysUntilBlock(alert)): boolean {
  return days !== null && days <= alert.rul.p10Days;
}
