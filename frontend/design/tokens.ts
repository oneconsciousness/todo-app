import tokensCss from "../src/styles/tokens.css?raw";

/** A colour token with its light (open page) and dark (cloth binding) value. */
export interface ColorToken {
  readonly name: string;
  readonly light: string;
  readonly dark: string;
}

/** The two themes the token file defines. */
export type Theme = "light" | "dark";

/** One foreground and background pairing the design relies on, with its WCAG minimum. */
export interface ContrastPair {
  readonly fg: string;
  readonly bg: string;
  readonly minimum: 3 | 4.5;
}

/** A contrast pair measured in one theme. */
export interface ContrastCheck extends ContrastPair {
  readonly theme: Theme;
  readonly ratio: number;
}

const colorTokenPattern =
  /--color-([a-z-]+):\s*light-dark\((#[0-9a-f]{6}(?:[0-9a-f]{2})?),\s*(#[0-9a-f]{6}(?:[0-9a-f]{2})?)\)/g;

/** Read every `--color-*: light-dark(…, …)` declaration from a stylesheet. */
export const parseColorTokens = (css: string): readonly ColorToken[] =>
  [...css.matchAll(colorTokenPattern)].map(([, name = "", light = "", dark = ""]) => ({
    name,
    light,
    dark,
  }));

const channel = (hex: string, offset: number): number => {
  const value = Number.parseInt(hex.slice(offset, offset + 2), 16) / 255;
  return value <= 0.04045 ? value / 12.92 : ((value + 0.055) / 1.055) ** 2.4;
};

const luminance = (hex: string): number =>
  0.2126 * channel(hex, 1) + 0.7152 * channel(hex, 3) + 0.0722 * channel(hex, 5);

/** WCAG 2 contrast ratio between two opaque `#rrggbb` colours. */
export const contrastRatio = (a: string, b: string): number => {
  const [lighter = 0, darker = 0] = [luminance(a), luminance(b)].toSorted((x, y) => y - x);
  return (lighter + 0.05) / (darker + 0.05);
};

/** A non-colour token: its name within its group, and its value as written. */
export interface Token {
  readonly name: string;
  readonly value: string;
}

// The theme block ends at the first closing brace in column 0; overrides such as reduced motion come after it.
const themeBlock = (css: string): string => css.slice(0, css.search(/^\}/m) + 1 || undefined);

/** Read every `--<group>-<name>: value;` declaration in the theme block, skipping sub-properties such as `--text-body--line-height`. */
export const parseTokenGroup = (css: string, group: string): readonly Token[] =>
  [...themeBlock(css).matchAll(new RegExp(`--${group}-([a-z0-9-]+?):\\s*([^;]+);`, "g"))]
    .map(([, name = "", value = ""]) => ({ name, value: value.trim() }))
    .filter(({ name }) => !name.includes("--"));

/** The value of one custom property, such as `text-body--line-height`, or an empty string. */
export const tokenValue = (css: string, property: string): string =>
  new RegExp(`--${property}:\\s*([^;]+);`).exec(css)?.[1]?.trim() ?? "";

/** The raw token file, for the gallery's type, space, shape and motion sections. */
export const tokenSource = tokensCss;

/** Every colour token in `src/styles/tokens.css`, in file order. */
export const colorTokens = parseColorTokens(tokensCss);

/** What each colour token is for. The token sheet shows this; a test keeps it in step with the file. */
export const tokenRoles: Readonly<Record<string, string>> = {
  canvas: "The green desk blotter under the page. App background.",
  sheet: "The ledger page. Lists, panels and fields.",
  ink: "Blue-black iron-gall ink. Body text and headings.",
  "ink-muted": "Faded ink. Secondary text, completed tasks, placeholders.",
  rule: "Feint blue ruling. Row dividers and quiet borders.",
  "rule-strong": "Pressed ruling. Field and control borders.",
  margin: "The red money-column rule. The ledger margin, used only as ruling.",
  alert: "Red ink for what needs attention: overdue dates and errors.",
  primary: "Bottle-green binding cloth; gilt tooling in dark. The main action.",
  "primary-strong": "The main action when pressed or hovered.",
  "on-primary": "Text and icons on the main action.",
  focus: "Gilt. The keyboard focus ring.",
  binding: "The cloth binding. The masthead band and the sign-in cover.",
  gilt: "Gold tooling on the binding: the ledger title, and focus on the band.",
  "on-binding": "Text on the binding that is not tooled in gilt.",
  shade: "Shadow under the page and under a lifted row.",
};

/** The pairings the screens use. Text needs 4.5:1, controls and focus rings 3:1 (WCAG AA). */
export const contrastPairs: readonly ContrastPair[] = [
  { fg: "ink", bg: "sheet", minimum: 4.5 },
  { fg: "ink", bg: "canvas", minimum: 4.5 },
  { fg: "ink-muted", bg: "sheet", minimum: 4.5 },
  { fg: "ink-muted", bg: "canvas", minimum: 4.5 },
  { fg: "alert", bg: "sheet", minimum: 4.5 },
  { fg: "alert", bg: "canvas", minimum: 4.5 },
  { fg: "on-primary", bg: "primary", minimum: 4.5 },
  { fg: "on-primary", bg: "primary-strong", minimum: 4.5 },
  { fg: "on-primary", bg: "alert", minimum: 4.5 },
  { fg: "gilt", bg: "binding", minimum: 4.5 },
  { fg: "on-binding", bg: "binding", minimum: 4.5 },
  { fg: "rule-strong", bg: "sheet", minimum: 3 },
  { fg: "primary", bg: "sheet", minimum: 3 },
  { fg: "focus", bg: "sheet", minimum: 3 },
  { fg: "focus", bg: "canvas", minimum: 3 },
];

const tokensByName = new Map(colorTokens.map((token) => [token.name, token]));

const valueOf = (name: string, theme: Theme): string => {
  const token = tokensByName.get(name);
  if (!token) throw new Error(`No colour token named ${name} in tokens.css`);
  return token[theme];
};

/** Every contrast pair measured in both themes. */
export const contrastChecks: readonly ContrastCheck[] = (["light", "dark"] as const).flatMap(
  (theme) =>
    contrastPairs.map((pair) => ({
      ...pair,
      theme,
      ratio: contrastRatio(valueOf(pair.fg, theme), valueOf(pair.bg, theme)),
    })),
);
