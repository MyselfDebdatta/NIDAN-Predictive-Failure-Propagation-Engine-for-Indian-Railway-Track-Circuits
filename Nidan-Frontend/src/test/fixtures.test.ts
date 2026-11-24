import { describe, expect, it } from "vitest";
import {
  alertFixtures,
  assetRecords,
  clusterFixtures,
  fieldTaskFixtures,
  modeDistributionByAsset,
  signalFixtures,
  signalFixturesByAsset,
} from "@/data/fixtures";
import { daysUntilBlock } from "@/lib/blocks";

const byAsset = (assetId: string) => alertFixtures.find((alert) => alert.assetId === assetId)!;

describe("demo fixtures", () => {
  it("gives every alert its own explanation instead of a shared fallback", () => {
    expect(new Set(alertFixtures.map((alert) => alert.explanation)).size).toBe(
      alertFixtures.length,
    );
    for (const alert of alertFixtures) {
      expect(alert.explanation.physics.headline.length).toBeGreaterThan(20);
      expect(alert.explanation.model.modeSet).toContain(alert.likelyModes[0]);
      expect(alert.explanation.precedents.length).toBeGreaterThan(0);
    }
  });

  it("derives cluster membership and counts from alert.clusterId", () => {
    for (const cluster of clusterFixtures) {
      const expected = alertFixtures
        .filter((alert) => alert.clusterId === cluster.id)
        .map((alert) => alert.assetId);
      expect(cluster.members).toEqual(expected);
      expect(cluster.alertsFolded).toBe(expected.length);
      expect(cluster.members.length).toBeGreaterThan(0);
    }
  });

  it("keeps levels inside the policy thresholds the spec publishes", () => {
    for (const alert of alertFixtures) {
      if (alert.level === "critical") expect(alert.risk.h24).toBeGreaterThan(0.5);
      if (alert.level === "warning") expect(alert.risk.h72).toBeGreaterThan(0.3);
      if (alert.level === "watch") {
        expect(alert.risk.h24).toBeLessThanOrEqual(0.5);
        expect(alert.risk.h72).toBeLessThanOrEqual(0.3);
      }
    }
  });

  it("matches the field task's last reading to the end of the signal series", () => {
    const task = fieldTaskFixtures.find((item) => item.assetId === "ADRA/TC/12T")!;
    const last = Object.fromEntries(
      signalFixtures.map((series) => [series.key, String(series.values.at(-1))]),
    );
    expect(task.lastReadings.relayCurrent).toBe(last["relay_i"]);
    expect(task.lastReadings.ballastConductance).toBe(last["ballast_g"]);
    expect(task.lastReadings.cableInsulation).toBe(last["cable_ir"]);
    expect(task.lastReadings.feedVoltage).toBe(last["feed_v"]);
  });

  it("matches every field task's last reading to its asset's signal series", () => {
    const keyByReading = {
      relayCurrent: "relay_i",
      ballastConductance: "ballast_g",
      cableInsulation: "cable_ir",
      feedVoltage: "feed_v",
    } as const;
    for (const task of fieldTaskFixtures) {
      const series = signalFixturesByAsset[task.assetId] ?? [];
      for (const [reading, key] of Object.entries(keyByReading)) {
        const match = series.find((item) => item.key === key);
        if (!match) continue;
        expect(String(match.values.at(-1)), `${task.assetId} ${reading}`).toBe(
          task.lastReadings[reading as keyof typeof task.lastReadings],
        );
      }
    }
  });

  it("computes block offsets from the snapshot date", () => {
    expect(daysUntilBlock(byAsset("ADRA/TC/12T"))).toBe(2);
    expect(daysUntilBlock(byAsset("ADRA/TC/09T"))).toBe(0);
    expect(daysUntilBlock(byAsset("ADRA/TC/18T"))).toBe(5);
    expect(daysUntilBlock(byAsset("KGP/TC/31T"))).toBeNull();
  });

  it("gives every asset a record, a signal history and a mode distribution", () => {
    for (const alert of alertFixtures) {
      expect(assetRecords[alert.assetId], `${alert.assetId} record`).toBeDefined();
      expect(
        signalFixturesByAsset[alert.assetId]?.length,
        `${alert.assetId} signals`,
      ).toBeGreaterThan(0);
      expect(
        modeDistributionByAsset[alert.assetId]?.length,
        `${alert.assetId} modes`,
      ).toBeGreaterThan(0);
    }
  });

  it("ends a generated series at the value its explanation states", () => {
    const cable = signalFixturesByAsset["ADRA/TC/18T"]?.find((series) => series.key === "cable_ir");
    expect(cable?.values.at(-1)).toBe(0.42);
    const feed = signalFixturesByAsset["KGP/TC/31T"]?.find((series) => series.key === "feed_v");
    expect(feed?.values.at(-1)).toBe(5.7);
  });

  it("sums each generated mode distribution to one", () => {
    for (const [assetId, rows] of Object.entries(modeDistributionByAsset)) {
      if (assetId === "ADRA/TC/12T") continue; // hand-authored, carries explicit exclusions
      const total = rows.reduce((sum, row) => sum + row.probability, 0);
      expect(total, assetId).toBeCloseTo(1, 6);
    }
  });

  it("leaves the Critical alert without a published block it does not fit", () => {
    const critical = alertFixtures.find((alert) => alert.level === "critical")!;
    expect(critical.block).toBeUndefined();
  });
});
