import { describe, expect, it } from "vitest";
import {
  colorTokens,
  contrastChecks,
  contrastRatio,
  parseColorTokens,
  parseTokenGroup,
  tokenRoles,
  tokenValue,
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

describe("parseTokenGroup", () => {
  const css = [
    "--*: initial;",
    "--text-body: 1rem;",
    "--text-body--line-height: 1.5rem;",
    "--spacing-4: 1rem;",
  ].join("\n");

  it("reads the tokens of one group with their values", () => {
    expect(parseTokenGroup(css, "text")).toEqual([{ name: "body", value: "1rem" }]);
  });

  it("reads only the theme block, not later overrides such as reduced motion", () => {
    const withOverride = `@theme {\n  --duration-quick: 120ms;\n}\n:root {\n  --duration-quick: 0ms;\n}`;
    expect(parseTokenGroup(withOverride, "duration")).toEqual([{ name: "quick", value: "120ms" }]);
  });

  it("reads a token's sub-property", () => {
    expect(tokenValue(css, "text-body--line-height")).toBe("1.5rem");
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
