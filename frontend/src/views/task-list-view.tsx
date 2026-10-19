import { type SubmitEvent, useId, useState } from "react";
import { Button } from "../components/ui/button.tsx";
import { EmptyState } from "../components/ui/empty-state.tsx";
import { Icon } from "../components/ui/icon.tsx";
import { Notice } from "../components/ui/notice.tsx";
import { Page } from "../components/ui/page.tsx";
import { SearchBox } from "../components/ui/search-box.tsx";
import { Skeleton } from "../components/ui/skeleton.tsx";
import { SortableList } from "../components/ui/sortable-list.tsx";
import {
  LedgerCells,
  LedgerHead,
  TaskRow,
  ledgerLineClass,
  taskLineClass,
} from "../components/ui/task-row.tsx";
import { TextField } from "../components/ui/text-field.tsx";
import { longDate } from "../lib/due-date.ts";
import { type Task, titleSchema } from "../lib/schema/task.ts";
import { isSearching, listSummary } from "../lib/task-list.ts";

/** What the list area shows: placeholders, a load error, or the tasks the server returned. */
export type TaskListContent =
  | { readonly status: "loading" }
  | { readonly status: "error"; readonly message: string }
  | { readonly status: "ready"; readonly tasks: readonly Task[] };

/** An action that failed and was rolled back, with an optional way to try it again. */
export interface TaskListFailure {
  readonly message: string;
  readonly onRetry?: () => void;
}

/** Props for `TaskListView`. Server data comes in; every user intent goes out as a callback. */
export interface TaskListViewProps {
  readonly content: TaskListContent;
  /** Today as `YYYY-MM-DD`, so due dates read relative to it. */
  readonly today: string;
  /** The search box text. A non-empty term turns reordering off. */
  readonly query: string;
  /** True while the results for `query` are still loading; the previous results stay on screen. */
  readonly searchPending: boolean;
  /** The title of a task the server is still creating, shown at the top of the list. */
  readonly pendingCreate: string | null;
  readonly failure: TaskListFailure | null;
  readonly onQueryChange: (query: string) => void;
  readonly onCreate: (title: string) => void;
  readonly onToggle: (taskId: string, completed: boolean) => void;
  readonly onMove: (taskId: string, afterId: string | null) => void;
  readonly onRetry: () => void;
  readonly onDismissFailure: () => void;
}

const placeholderWidths = ["w-3/4", "w-1/2", "w-2/3", "w-2/5"] as const;

const inset = "px-4 @wide:px-12";

/** The task list screen: one ledger page with search, quick add, and the ruled list the user ticks off and reorders. */
export function TaskListView(props: TaskListViewProps) {
  const { content, today, query, searchPending, pendingCreate, failure } = props;
  const headingId = useId();
  const [draft, setDraft] = useState("");
  const [draftError, setDraftError] = useState<string | undefined>(undefined);
  const reorderable = !isSearching(query) && content.status === "ready";

  const handleSubmit = (event: SubmitEvent<HTMLFormElement>) => {
    event.preventDefault();
    const title = titleSchema.safeParse(draft);
    if (!title.success) {
      setDraftError(title.error.issues[0]?.message);
      return;
    }
    props.onCreate(title.data);
    setDraft("");
  };

  return (
    <Page labelledBy={headingId}>
      <header
        className={`flex flex-col gap-4 @wide:flex-row @wide:items-end @wide:justify-between ${inset}`}
      >
        <div className="flex flex-col gap-1">
          <p className="text-caption font-medium tracking-caps text-ink-muted uppercase">
            {longDate(today)}
          </p>
          <h1 id={headingId} className="font-display text-display font-medium text-balance">
            Tasks
          </h1>
          <p role="status" className="min-h-5 text-caption text-ink-muted tabular-nums">
            {content.status === "ready" && listSummary(content.tasks, query, searchPending)}
          </p>
        </div>
        <SearchBox
          label="Search tasks"
          placeholder="Search titles and notes"
          value={query}
          busy={searchPending}
          onChange={props.onQueryChange}
          className="@wide:w-1/2"
        />
      </header>

      <form noValidate onSubmit={handleSubmit} className={`flex items-start gap-2 ${inset}`}>
        <TextField
          label="New task"
          hideLabel
          placeholder="Add a task"
          value={draft}
          error={draftError}
          onChange={(event) => {
            setDraft(event.target.value);
            setDraftError(undefined);
          }}
          className="flex-1"
        />
        <Button type="submit" variant="primary" disabled={pendingCreate !== null}>
          <Icon name="plus" />
          Add task
        </Button>
      </form>

      {failure && (
        <div className={inset}>
          <Notice
            actions={failure.onRetry && [{ label: "Try again", onAction: failure.onRetry }]}
            onDismiss={props.onDismissFailure}
          >
            {failure.message}
          </Notice>
        </div>
      )}

      <div className="@wide:px-12">
        <div className="border-t border-b-3 border-double border-rule-strong">
          {content.status !== "error" && <LedgerHead reorderable={reorderable} />}
          {pendingCreate !== null && <PendingRow title={pendingCreate} reorderable={reorderable} />}
          <ListBody {...props} reorderable={reorderable} />
        </div>
      </div>
    </Page>
  );
}

interface ListBodyProps extends TaskListViewProps {
  readonly reorderable: boolean;
}

function ListBody({
  content,
  today,
  query,
  pendingCreate,
  reorderable,
  onQueryChange,
  onToggle,
  onMove,
  onRetry,
}: ListBodyProps) {
  switch (content.status) {
    case "loading":
      return <LoadingRows />;
    case "error":
      return (
        <EmptyState
          tone="alert"
          title="Couldn't load your tasks"
          actions={
            <Button variant="primary" onClick={onRetry}>
              Try again
            </Button>
          }
        >
          {content.message}
        </EmptyState>
      );
    case "ready":
      if (content.tasks.length === 0 && isSearching(query))
        return (
          <EmptyState
            title={`No tasks match “${query.trim()}”`}
            actions={
              <Button
                onClick={() => {
                  onQueryChange("");
                }}
              >
                Show all tasks
              </Button>
            }
          >
            Search looks through task titles and notes.
          </EmptyState>
        );
      if (content.tasks.length === 0 && pendingCreate === null)
        return (
          <EmptyState title="No tasks yet">
            Add your first task above. New tasks go to the top of the list.
          </EmptyState>
        );
      return (
        <SortableList
          items={content.tasks}
          label="Tasks"
          itemLabel={(task) => task.title}
          disabled={!reorderable}
          onMove={onMove}
          itemClassName={taskLineClass(reorderable)}
        >
          {(task, handle) => (
            <TaskRow task={task} today={today} handle={handle} onToggle={onToggle} />
          )}
        </SortableList>
      );
    default: {
      const unreachable: never = content;
      return unreachable;
    }
  }
}

function PendingRow({
  title,
  reorderable,
}: {
  readonly title: string;
  readonly reorderable: boolean;
}) {
  return (
    <div aria-busy="true" className={ledgerLineClass(reorderable)}>
      <LedgerCells
        handle={reorderable && <span className="block size-touch" />}
        control={<Skeleton className="size-5" />}
      >
        <span className="leading-(--text-lead--line-height) break-words text-ink-muted">
          {title}
        </span>
        <span className="text-caption text-ink-muted motion-safe:animate-shimmer">Adding…</span>
      </LedgerCells>
    </div>
  );
}

function LoadingRows() {
  return (
    <div role="status">
      <span className="sr-only">Loading your tasks…</span>
      {placeholderWidths.map((width) => (
        <div key={width} aria-hidden="true" className={ledgerLineClass(false)}>
          <LedgerCells handle={null} control={<Skeleton className="size-5" />}>
            <Skeleton className={`my-2 h-3 ${width}`} />
          </LedgerCells>
        </div>
      ))}
    </div>
  );
}
