import { describe, expect, it } from "vitest";
import { resolveTheme } from "@/lib/theme";

describe("NIDAN theme selection", () => {
  it("keeps the saved choice ahead of system preference", () => {
    expect(resolveTheme("day", true)).toBe("day");
  });

  it("uses the system preference when no saved choice exists", () => {
    expect(resolveTheme(null, true)).toBe("night");
    expect(resolveTheme(null, false)).toBe("day");
  });

  it("falls back to the system preference for an unknown saved value", () => {
    expect(resolveTheme("automatic", false)).toBe("day");
  });
});
