/** The only place numbers are formatted for display. */
export function formatRisk(value: number) {
  return `${Math.round(value * 100)}%`;
}

export function formatRiskProse(value: number) {
  return `${(value * 100).toFixed(1)}%`;
}

export function formatRul(value: number) {
  return `${Math.round(value)} d`;
}

export function formatCount(value: number) {
  return new Intl.NumberFormat("en-IN").format(value);
}

export function formatDecimal(value: number, digits = 2) {
  return value.toFixed(digits);
}

export function formatAge(minutes: number) {
  if (minutes < 60) return `${Math.round(minutes)} min`;
  const hours = minutes / 60;
  if (hours < 48) return `${hours.toFixed(1)} h`;
  return `${Math.round(hours / 24)} d`;
}

const months = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"];
const weekdays = ["Sun", "Mon", "Tue", "Wed", "Thu", "Fri", "Sat"];

/** Formats an ISO date (YYYY-MM-DD) as "16 Jul" without timezone drift. */
export function formatShortDate(iso: string) {
  const [y, m, d] = iso.split("-").map(Number);
  if (!y || !m || !d) return iso;
  return `${String(d).padStart(2, "0")} ${months[m - 1] ?? ""}`;
}

export function formatWeekday(iso: string) {
  const [y, m, d] = iso.split("-").map(Number);
  if (!y || !m || !d) return "";
  return weekdays[new Date(Date.UTC(y, m - 1, d)).getUTCDay()] ?? "";
}

export function formatDuration(minutes: number) {
  return `${Math.round(minutes)} min`;
}
