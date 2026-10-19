import type { ReactNode } from "react";

/** Props for `EmptyState`. */
export interface EmptyStateProps {
  readonly title: string;
  readonly children: ReactNode;
  readonly actions?: ReactNode;
  readonly tone?: "quiet" | "alert";
  /** 1 when the message is the whole page, as on not found. */
  readonly level?: 1 | 2;
  readonly headingId?: string | undefined;
  /** A word struck on the page like a ledger clerk's rubber stamp, such as "No entry". */
  readonly stamp?: string | undefined;
}

/** A centred message for something with nothing to show, or that could not load. */
export function EmptyState({
  title,
  children,
  actions,
  tone = "quiet",
  level = 2,
  headingId,
  stamp,
}: EmptyStateProps) {
  const Heading = level === 1 ? "h1" : "h2";
  return (
    <div
      role={tone === "alert" ? "alert" : undefined}
      className="flex flex-col items-center gap-2 px-6 py-12 text-center"
    >
      {stamp && (
        <span
          aria-hidden="true"
          className="mb-4 -rotate-3 rounded-control border-3 border-double border-alert px-3 py-1 font-display text-lead font-medium tracking-caps text-alert uppercase"
        >
          {stamp}
        </span>
      )}
      <Heading
        id={headingId}
        className={`font-display text-balance ${level === 1 ? "text-display" : "text-title"} ${tone === "alert" ? "text-alert" : "text-ink"}`}
      >
        {title}
      </Heading>
      <p className="max-w-measure text-ink-muted">{children}</p>
      {actions && <div className="flex flex-wrap justify-center gap-2 pt-4">{actions}</div>}
    </div>
  );
}
