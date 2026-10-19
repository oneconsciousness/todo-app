import { describe, expect, it } from "vitest";
import {
  colorTokens,
  contrastChecks,
  contrastRatio,
  parseColorTokens,
  tokenRoles,
} from "./tokens.ts";

describe("contrastRatio", () => {
  it("gives 21 for black on white", () => {
    expect(contrastRatio("#000000", "#ffffff")).toBeCloseTo(21, 5);
  });

  it("is symmetric", () => {
    expect(contrastRatio("#1b2333", "#f3f6ec")).toBe(contrastRatio("#f3f6ec", "#1b2333"));
  });
});

describe("parseColorTokens", () => {
  it("reads the light and dark value of each colour token", () => {
    const css = "--color-ink: light-dark(#1b2333, #e4ead9);\n--spacing-1: 0.25rem;";
    expect(parseColorTokens(css)).toEqual([{ name: "ink", light: "#1b2333", dark: "#e4ead9" }]);
  });
});

describe("the token file", () => {
  it("gives every colour token a documented role", () => {
    expect(colorTokens.map((token) => token.name).toSorted()).toEqual(
      Object.keys(tokenRoles).toSorted(),
    );
  });

  it.each(contrastChecks)("$fg on $bg meets $minimum:1 in $theme", ({ ratio, minimum }) => {
    expect(ratio).toBeGreaterThanOrEqual(minimum);
  });
});
