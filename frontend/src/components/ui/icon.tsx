import type { ReactNode } from "react";

const glyphs = {
  search: (
    <>
      <circle cx="11" cy="11" r="6.25" />
      <path d="m15.75 15.75 4 4" />
    </>
  ),
  grip: (
    <g fill="currentColor" stroke="none">
      {[6, 12, 18].flatMap((y) =>
        [9, 15].map((x) => <circle key={`${String(x)}-${String(y)}`} cx={x} cy={y} r="1.5" />),
      )}
    </g>
  ),
  check: <path d="m5.5 12.5 4.25 4.25L18.5 7.5" strokeWidth="2.25" />,
  plus: <path d="M12 5.5v13M5.5 12h13" />,
  close: <path d="m7 7 10 10M17 7 7 17" />,
  alert: (
    <>
      <circle cx="12" cy="12" r="8.25" />
      <path d="M12 7.75v5" />
      <circle cx="12" cy="16" r="0.5" fill="currentColor" />
    </>
  ),
} satisfies Record<string, ReactNode>;

/** The names of the glyphs `Icon` can draw. */
export type IconName = keyof typeof glyphs;

/** Props for `Icon`. */
export interface IconProps {
  readonly name: IconName;
  readonly className?: string;
}

/** A decorative line glyph drawn in the current text colour; the control around it carries the name. */
export function Icon({ name, className = "size-5" }: IconProps) {
  return (
    <svg
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="1.75"
      strokeLinecap="round"
      strokeLinejoin="round"
      aria-hidden="true"
      focusable="false"
      className={className}
    >
      {glyphs[name]}
    </svg>
  );
}
