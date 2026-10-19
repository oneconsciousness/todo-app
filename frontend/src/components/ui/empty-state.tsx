import type { ReactNode } from "react";

/** Props for `EmptyState`. */
export interface EmptyStateProps {
  readonly title: string;
  readonly children: ReactNode;
  readonly action?: ReactNode;
  readonly tone?: "quiet" | "alert";
}

/** A centred message for a list with nothing to show, or one that could not load. */
export function EmptyState({ title, children, action, tone = "quiet" }: EmptyStateProps) {
  return (
    <div
      role={tone === "alert" ? "alert" : undefined}
      className="flex flex-col items-center gap-2 px-6 py-12 text-center"
    >
      <h2
        className={`font-display text-title text-balance ${tone === "alert" ? "text-alert" : "text-ink"}`}
      >
        {title}
      </h2>
      <p className="max-w-measure text-ink-muted">{children}</p>
      {action && <div className="pt-4">{action}</div>}
    </div>
  );
}
