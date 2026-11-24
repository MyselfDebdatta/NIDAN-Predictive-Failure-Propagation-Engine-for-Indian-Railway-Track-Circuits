import { describe, expect, it } from "vitest";
import { alertFixtures } from "@/data/fixtures";
import { blockInsideP10, blockWhenLabel, daysUntilBlock } from "@/lib/blocks";

const byAsset = (assetId: string) => alertFixtures.find((alert) => alert.assetId === assetId)!;

describe("block scheduling", () => {
  it("counts calendar days from the snapshot", () => {
    expect(daysUntilBlock(byAsset("ADRA/TC/12T"))).toBe(2);
    expect(daysUntilBlock(byAsset("ADRA/TC/05T"))).toBe(1);
  });

  it("returns null when there is no published block", () => {
    expect(daysUntilBlock(byAsset("KGP/TC/31T"))).toBeNull();
  });

  it("labels today and tomorrow in words, not '0 d'", () => {
    expect(blockWhenLabel(0)).toBe("today");
    expect(blockWhenLabel(1)).toBe("tomorrow");
    expect(blockWhenLabel(2)).toBe("in 2 d");
  });

  it("flags a block that is already outside the p10 horizon", () => {
    expect(blockInsideP10(byAsset("ADRA/TC/12T"))).toBe(true);
    expect(blockInsideP10(byAsset("ADRA/TC/18T"))).toBe(false);
  });
});
