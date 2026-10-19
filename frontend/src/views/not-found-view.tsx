import { useId } from "react";
import { buttonClass } from "../components/ui/button.tsx";
import { EmptyState } from "../components/ui/empty-state.tsx";
import { Link } from "../components/ui/link.tsx";
import { Page } from "../components/ui/page.tsx";
import { routes } from "../lib/routes.ts";

/** Props for `NotFoundView`. */
export interface NotFoundViewProps {
  /** A missing page (any unknown route), or a task that is gone or belongs to someone else. */
  readonly subject: "page" | "task";
}

const copy = {
  page: {
    title: "This page isn't in the ledger",
    body: "The address may be mistyped, or the page has moved.",
  },
  task: {
    title: "This task isn't in your ledger",
    body: "It may have been deleted, or the link may be wrong.",
  },
} as const;

/** Not found, for a route that doesn't exist or a task the user can't see. It never says which of the two. */
export function NotFoundView({ subject }: NotFoundViewProps) {
  const headingId = useId();
  return (
    <Page labelledBy={headingId}>
      <EmptyState
        level={1}
        headingId={headingId}
        stamp="No entry"
        title={copy[subject].title}
        actions={
          <Link href={routes.tasks} className={buttonClass("primary")}>
            Go to your tasks
          </Link>
        }
      >
        {copy[subject].body}
      </EmptyState>
    </Page>
  );
}
