import { readdirSync, readFileSync, statSync } from "node:fs";
import { join } from "node:path";
import { describe, expect, it } from "vitest";

function files(dir: string): string[] {
  return readdirSync(dir).flatMap((name) => {
    const path = join(dir, name);
    return statSync(path).isDirectory() ? files(path) : /\.(tsx?|css)$/.test(name) ? [path] : [];
  });
}

describe("non-vital boundary", () => {
  it("exposes no interlocking, signal, route or points control anywhere in the UI or API", () => {
    const banned =
      /(set route|operate points|apply to interlocking|clear signal|throw points|\/v1\/(interlocking|signals|routes|points|track-circuits)\/[^"`]*command)/i;
    const offenders = files("src").filter(
      (f) =>
        !f.endsWith(".test.ts") &&
        !f.includes("routeTree.gen") &&
        !f.endsWith("design.tsx") &&
        banned.test(readFileSync(f, "utf8")),
    );
    expect(offenders).toEqual([]);
  });
});
