import { describe, expect, it } from "vitest";
import { alertFixtures } from "@/data/fixtures";
import {
  BULK_CAP,
  bulkDeferBlocker,
  byPolicyRank,
  deferValidation,
  filterAlerts,
} from "@/lib/policy";
import { formatRisk, formatRul } from "@/lib/formatters";

const critical = alertFixtures.find((a) => a.level === "critical")!;
const watch = alertFixtures.filter((a) => a.level === "watch");

describe("queue policy", () => {
  it("sorts by server policy rank, not by asset name", () => {
    const ranked = byPolicyRank(alertFixtures).map((a) => a.assetId);
    expect(ranked[0]).toBe("ADRA/TC/07T");
    expect(ranked[1]).toBe("ADRA/TC/12T");
  });

  it("never allows a Critical alert in a bulk defer", () => {
    expect(bulkDeferBlocker([critical, ...watch.slice(0, 2)])).toMatch(/Critical/);
  });

  it("allows bulk defer of non-critical rows", () => {
    expect(bulkDeferBlocker(watch.slice(0, 3))).toBeNull();
  });

  it("caps bulk actions at 50 rows", () => {
    expect(BULK_CAP).toBe(50);
    const many = Array.from({ length: 51 }, (_, i) => ({ ...watch[0]!, id: `x-${i}` }));
    expect(bulkDeferBlocker(many)).toMatch(/50/);
  });

  it("requires a reason and a review date to defer", () => {
    expect(Object.keys(deferValidation({ reason: "", reviewDate: "" }))).toEqual([
      "reason",
      "reviewDate",
    ]);
    expect(deferValidation({ reason: "Crew booked in RB-31", reviewDate: "2026-07-19" })).toEqual(
      {},
    );
  });

  it("keeps deferred alerts out of triage and shows them in the deferred view", () => {
    expect(filterAlerts(alertFixtures, {}).some((a) => a.deferral)).toBe(false);
    expect(filterAlerts(alertFixtures, { view: "deferred" }).every((a) => a.deferral)).toBe(true);
  });
});

describe("demo scenario", () => {
  it("matches the briefed queue counts: 11 open, 1 critical, 7 watch", () => {
    expect(alertFixtures).toHaveLength(11);
    expect(alertFixtures.filter((a) => a.level === "critical")).toHaveLength(1);
    expect(watch).toHaveLength(7);
  });

  it("formats 12T as whole-percent risk and whole-day RUL", () => {
    const a = alertFixtures.find((x) => x.assetId === "ADRA/TC/12T")!;
    expect(formatRisk(a.risk.h7d)).toBe("24%");
    expect(formatRul(a.rul.p10Days)).toBe("9 d");
  });
});
