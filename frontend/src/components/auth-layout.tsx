import { type ReactNode, useId } from "react";
import { LedgerTitle } from "./ui/ledger-title.tsx";

/** Props for `AuthLayout`. */
export interface AuthLayoutProps {
  readonly title: string;
  readonly children: ReactNode;
  readonly footer: ReactNode;
}

/**
 * The ledger opened at its title page: the cloth cover with the title tooled in gilt inside a blind-stamped double
 * frame, and beside it (below it on a phone) the first page, which holds the form.
 */
export function AuthLayout({ title, children, footer }: AuthLayoutProps) {
  const headingId = useId();
  return (
    <div className="@container flex min-h-dvh items-center bg-binding text-on-binding">
      <div className="mx-auto grid w-full max-w-book gap-6 px-4 py-6 @wide:grid-cols-2 @wide:gap-12 @wide:px-8 @wide:py-16">
        <div className="flex flex-col items-center justify-center gap-4 border-3 border-double border-gilt/60 px-6 py-8 text-center @wide:aspect-3/4 @wide:gap-6 @wide:py-16">
          <LedgerTitle size="cover" />
          <span aria-hidden="true" className="h-px w-12 bg-gilt/60" />
          <p className="text-caption font-medium tracking-caps uppercase">
            A ledger for the things you mean to do
          </p>
        </div>
        <article
          aria-labelledby={headingId}
          className="flex flex-col gap-6 rounded-sheet bg-sheet px-6 py-8 text-ink shadow-sheet @wide:justify-center @wide:px-12 @wide:py-12"
        >
          <h1 id={headingId} className="font-display text-title font-medium">
            {title}
          </h1>
          {children}
          <p className="text-ink-muted">{footer}</p>
        </article>
      </div>
    </div>
  );
}
