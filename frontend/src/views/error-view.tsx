import { useId } from "react";
import { Button } from "../components/ui/button.tsx";
import { EmptyState } from "../components/ui/empty-state.tsx";
import { Page } from "../components/ui/page.tsx";

/** Props for `ErrorView`. */
export interface ErrorViewProps {
  /** What went wrong, in words a user can act on; a general line is shown without one. */
  readonly message?: string | undefined;
  readonly onRetry: () => void;
  readonly onGoToTasks: () => void;
}

/** The route error boundary's screen: what went wrong, and two ways forward. */
export function ErrorView({ message, onRetry, onGoToTasks }: ErrorViewProps) {
  const headingId = useId();
  return (
    <Page labelledBy={headingId}>
      <EmptyState
        level={1}
        headingId={headingId}
        title="Something went wrong"
        actions={
          <>
            <Button variant="primary" onClick={onRetry}>
              Try again
            </Button>
            <Button onClick={onGoToTasks}>Go to tasks</Button>
          </>
        }
      >
        {message ?? "This page hit a problem it couldn't recover from. Your tasks are safe."}
      </EmptyState>
    </Page>
  );
}
