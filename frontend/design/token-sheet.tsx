import type { ReactNode } from "react";
import {
  type ColorToken,
  colorTokens,
  contrastChecks,
  contrastPairs,
  parseTokenGroup,
  tokenRoles,
  tokenSource,
  tokenValue,
} from "./tokens.ts";

const textTokens = parseTokenGroup(tokenSource, "text");
const spacingTokens = parseTokenGroup(tokenSource, "spacing").filter(({ value }) => value !== "0");
const radiusTokens = parseTokenGroup(tokenSource, "radius");
const shadowTokens = parseTokenGroup(tokenSource, "shadow");
const durationTokens = parseTokenGroup(tokenSource, "duration");
const easing = tokenValue(tokenSource, "ease-standard");

const displayFaces = new Set(["display", "title"]);

const px = (rem: string): string =>
  rem.endsWith("rem") ? `${String(Number.parseFloat(rem) * 16)}px` : rem;

/** The token sheet: every token in `tokens.css`, read from the file itself, with contrast measured in both themes. */
export function TokenSheet() {
  return (
    <>
      <SheetSection
        title="Colour"
        lead="Each chip shows the light value on the left and the dark value on the right."
      >
        <ul className="grid gap-4 @wide:grid-cols-2">
          {colorTokens.map((token) => (
            <Swatch key={token.name} token={token} />
          ))}
        </ul>
      </SheetSection>

      <SheetSection
        title="Contrast"
        lead="Every pairing the screens use, measured in both themes. Text needs 4.5:1 and controls 3:1 (WCAG AA). A test fails the build if any pairing drops below."
      >
        <ContrastTable />
      </SheetSection>

      <SheetSection
        title="Type"
        lead="Besley sets headings and nothing else. Libre Franklin sets everything read at length, with tabular figures for dates."
      >
        <ul className="flex flex-col divide-y divide-rule rounded-sheet border border-rule bg-sheet">
          {textTokens.map(({ name, value }) => (
            <li
              key={name}
              className="flex flex-col gap-1 px-4 py-4 @wide:flex-row @wide:items-baseline @wide:gap-6"
            >
              <span className="text-caption text-ink-muted tabular-nums @wide:w-1/4">
                {name} · {px(value)}/{px(tokenValue(tokenSource, `text-${name}--line-height`))}
              </span>
              <span
                className={displayFaces.has(name) ? "font-display font-medium" : "font-body"}
                style={{
                  fontSize: `var(--text-${name})`,
                  lineHeight: `var(--text-${name}--line-height)`,
                }}
              >
                {displayFaces.has(name)
                  ? "Renew passport before the Lisbon trip"
                  : "Call the landlord about the boiler service · Due Sat, Oct 24"}
              </span>
            </li>
          ))}
        </ul>
      </SheetSection>

      <SheetSection
        title="Space"
        lead="A 4px grid. Only these steps exist as utilities, so an off-scale gap can't be written. Touch is the 44px minimum target."
      >
        <ul className="flex flex-col gap-2">
          {spacingTokens.map(({ name, value }) => (
            <li key={name} className="flex items-center gap-4">
              <span className="w-1/4 text-caption text-ink-muted tabular-nums">
                {name} · {px(value)}
              </span>
              <span className="h-2 rounded-control bg-primary" style={{ width: value }} />
            </li>
          ))}
        </ul>
      </SheetSection>

      <SheetSection
        title="Shape and depth"
        lead="Corners are nearly square, as paper is. Depth is used by role: the sheet resting on the desk, and a row lifted while it is dragged."
      >
        <div className="grid grid-cols-2 gap-6 @wide:grid-cols-4">
          {radiusTokens.map(({ name, value }) => (
            <Specimen key={name} label={`radius-${name} · ${px(value)}`}>
              <span
                className="block h-16 border border-rule-strong bg-sheet"
                style={{ borderRadius: value }}
              />
            </Specimen>
          ))}
          {shadowTokens.map(({ name }) => (
            <Specimen key={name} label={`shadow-${name}`}>
              <span
                className="block h-16 rounded-sheet bg-sheet"
                style={{ boxShadow: `var(--shadow-${name})` }}
              />
            </Specimen>
          ))}
        </div>
      </SheetSection>

      <SheetSection
        title="Motion"
        lead="Short and calm, with one easing curve. Reduced motion sets every duration to zero, from one place in tokens.css."
      >
        <dl className="grid grid-cols-[auto_minmax(0,1fr)] gap-x-6 gap-y-2 tabular-nums">
          {durationTokens.map(({ name, value }) => (
            <TermRow key={name} term={`duration-${name}`} detail={value} />
          ))}
          <TermRow term="ease-standard" detail={easing} />
        </dl>
      </SheetSection>
    </>
  );
}

function SheetSection({
  title,
  lead,
  children,
}: {
  readonly title: string;
  readonly lead: string;
  readonly children: ReactNode;
}) {
  return (
    <section className="flex flex-col gap-4">
      <div className="flex flex-col gap-1">
        <h3 className="text-lead font-semibold">{title}</h3>
        <p className="max-w-measure text-ink-muted">{lead}</p>
      </div>
      {children}
    </section>
  );
}

function Swatch({ token }: { readonly token: ColorToken }) {
  return (
    <li className="flex items-center gap-4 rounded-sheet border border-rule bg-sheet p-3">
      <span
        aria-hidden="true"
        className="flex size-16 shrink-0 overflow-hidden rounded-control border border-rule"
      >
        <span className="flex-1" style={{ backgroundColor: token.light }} />
        <span className="flex-1" style={{ backgroundColor: token.dark }} />
      </span>
      <span className="flex min-w-0 flex-col gap-1">
        <span className="font-medium">--color-{token.name}</span>
        <span className="text-caption text-ink-muted">{tokenRoles[token.name]}</span>
        <span className="text-caption text-ink-muted tabular-nums">
          {token.light} · {token.dark}
        </span>
      </span>
    </li>
  );
}

const colorOf = new Map(colorTokens.map((token) => [token.name, token]));

function ContrastTable() {
  return (
    <div className="overflow-x-auto rounded-sheet border border-rule bg-sheet">
      <table className="w-full text-left tabular-nums">
        <thead className="text-caption tracking-caps text-ink-muted uppercase">
          <tr className="border-b border-rule">
            <th scope="col" className="px-4 py-2 font-medium">
              Pairing
            </th>
            <th scope="col" className="px-4 py-2 font-medium">
              Needs
            </th>
            <th scope="col" className="px-4 py-2 font-medium">
              Light
            </th>
            <th scope="col" className="px-4 py-2 font-medium">
              Dark
            </th>
          </tr>
        </thead>
        <tbody>
          {contrastPairs.map((pair) => (
            <tr key={`${pair.fg}-${pair.bg}`} className="border-b border-rule last:border-b-0">
              <th scope="row" className="px-4 py-2 font-normal whitespace-nowrap">
                {pair.fg} on {pair.bg}
              </th>
              <td className="px-4 py-2 text-ink-muted">{pair.minimum}:1</td>
              {(["light", "dark"] as const).map((theme) => {
                const check = contrastChecks.find(
                  (c) => c.theme === theme && c.fg === pair.fg && c.bg === pair.bg,
                );
                return (
                  <td key={theme} className="px-4 py-2">
                    <span className="flex items-center gap-3 whitespace-nowrap">
                      <span
                        aria-hidden="true"
                        className="inline-flex size-touch items-center justify-center rounded-control border border-rule font-display font-medium"
                        style={{
                          color: colorOf.get(pair.fg)?.[theme],
                          backgroundColor: colorOf.get(pair.bg)?.[theme],
                        }}
                      >
                        Aa
                      </span>
                      {check?.ratio.toFixed(2)}:1
                    </span>
                  </td>
                );
              })}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

function Specimen({ label, children }: { readonly label: string; readonly children: ReactNode }) {
  return (
    <figure className="flex flex-col gap-2">
      {children}
      <figcaption className="text-caption text-ink-muted">{label}</figcaption>
    </figure>
  );
}

function TermRow({ term, detail }: { readonly term: string; readonly detail: string }) {
  return (
    <>
      <dt className="font-medium">{term}</dt>
      <dd className="text-ink-muted">{detail}</dd>
    </>
  );
}
