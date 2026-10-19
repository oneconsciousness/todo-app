const sizes = {
  band: "border-y-3 py-1 text-lead",
  cover: "border-y-4 py-3 text-display",
} as const;

/** Props for `LedgerTitle`. */
export interface LedgerTitleProps {
  readonly size: keyof typeof sizes;
}

/** The app's name tooled in gilt between double rules, the way a ledger's title sits on its spine and cover. */
export function LedgerTitle({ size }: LedgerTitleProps) {
  return (
    <span
      className={`inline-block border-double border-gilt font-display font-medium tracking-caps text-gilt uppercase ${sizes[size]}`}
    >
      To Do
    </span>
  );
}
