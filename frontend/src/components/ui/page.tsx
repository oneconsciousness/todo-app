import type { ReactNode } from "react";

/** Props for `Page`. */
export interface PageProps {
  /** The id of the heading that names the page; a placeholder page has none yet. */
  readonly labelledBy?: string | undefined;
  readonly children: ReactNode;
}

/**
 * A ledger page lying on the desk: one sheet at the reading width, with a second sheet peeking beneath it. It is
 * also the container its contents' `@wide` layout responds to.
 */
export function Page({ labelledBy, children }: PageProps) {
  return (
    <div className="@container">
      <article
        aria-labelledby={labelledBy}
        className="mx-auto flex w-full max-w-measure flex-col gap-6 rounded-sheet bg-sheet py-6 shadow-sheet @wide:gap-8 @wide:py-12"
      >
        {children}
      </article>
    </div>
  );
}
