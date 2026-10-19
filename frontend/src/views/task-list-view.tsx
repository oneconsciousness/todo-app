import { type ReactNode, type SubmitEvent, useState } from "react";
import { Button } from "../components/ui/button.tsx";
import { EmptyState } from "../components/ui/empty-state.tsx";
import { Icon } from "../components/ui/icon.tsx";
import { Notice } from "../components/ui/notice.tsx";
import { SearchBox } from "../components/ui/search-box.tsx";
import { Skeleton } from "../components/ui/skeleton.tsx";
import { SortableList } from "../components/ui/sortable-list.tsx";
import { TextField } from "../components/ui/text-field.tsx";
import { TaskRow, controlCellClass, rowClass, textCellClass } from "../components/ui/task-row.tsx";
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

const columns = {
  reorderable: "grid-cols-[auto_auto_minmax(0,1fr)] @wide:grid-cols-[auto_auto_minmax(0,1fr)_auto]",
  fixed: "grid-cols-[auto_minmax(0,1fr)] @wide:grid-cols-[auto_minmax(0,1fr)_auto]",
} as const;

const placeholderWidths = ["w-3/4", "w-1/2", "w-2/3", "w-2/5"] as const;

/** The task list screen: search, quick add, and the ruled list the user ticks off and reorders. */
export function TaskListView(props: TaskListViewProps) {
  const { content, today, query, searchPending, pendingCreate, failure } = props;
  const [draft, setDraft] = useState("");
  const [draftError, setDraftError] = useState<string | undefined>(undefined);
  const searching = isSearching(query);
  const reorderable = !searching && content.status === "ready";

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
    <div className="@container">
      <section
        aria-labelledby="task-list-heading"
        className="mx-auto flex w-full max-w-measure flex-col gap-6 px-4 py-8 @wide:px-6 @wide:py-12"
      >
        <header className="flex flex-col gap-4 @wide:flex-row @wide:items-end @wide:justify-between">
          <div className="flex flex-col gap-1">
            <p className="text-caption font-medium tracking-caps text-ink-muted uppercase">
              {longDate(today)}
            </p>
            <h1 id="task-list-heading" className="font-display text-display font-medium">
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

        <form noValidate onSubmit={handleSubmit} className="flex items-start gap-2">
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
          <Notice
            tone="alert"
            action={failure.onRetry && { label: "Try again", onAction: failure.onRetry }}
            onDismiss={props.onDismissFailure}
          >
            {failure.message}
          </Notice>
        )}

        <div
          className={`grid ${reorderable ? columns.reorderable : columns.fixed} rounded-sheet border border-b-3 border-double border-rule border-b-rule-strong bg-sheet shadow-sheet`}
        >
          {pendingCreate !== null && <PendingRow title={pendingCreate} reorderable={reorderable} />}
          <ListBody {...props} reorderable={reorderable} />
        </div>
      </section>
    </div>
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
        <FullWidth>
          <EmptyState
            tone="alert"
            title="Couldn't load your tasks"
            action={
              <Button variant="primary" onClick={onRetry}>
                Try again
              </Button>
            }
          >
            {content.message}
          </EmptyState>
        </FullWidth>
      );
    case "ready":
      if (content.tasks.length === 0 && isSearching(query))
        return (
          <FullWidth>
            <EmptyState
              title={`No tasks match “${query.trim()}”`}
              action={
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
          </FullWidth>
        );
      if (content.tasks.length === 0 && pendingCreate === null)
        return (
          <FullWidth>
            <EmptyState title="No tasks yet">
              Add your first task above. New tasks go to the top of the list.
            </EmptyState>
          </FullWidth>
        );
      return (
        <SortableList
          items={content.tasks}
          label="Tasks"
          itemLabel={(task) => task.title}
          disabled={!reorderable}
          onMove={onMove}
          className="col-span-full grid grid-cols-subgrid"
          itemClassName={`${rowClass} transition-colors hover:bg-rule/25 data-dragging:relative data-dragging:z-10 data-dragging:shadow-lifted`}
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

function FullWidth({ children }: { readonly children: ReactNode }) {
  return <div className="col-span-full">{children}</div>;
}

function PendingRow({
  title,
  reorderable,
}: {
  readonly title: string;
  readonly reorderable: boolean;
}) {
  return (
    <div aria-busy="true" className={rowClass}>
      {reorderable && <span className={`${controlCellClass} size-touch`} />}
      <span className={`${controlCellClass} flex size-touch items-center justify-center`}>
        <Skeleton className="size-5" />
      </span>
      <div className={`${textCellClass} @wide:col-span-2`}>
        <span className="leading-(--text-lead--line-height) break-words text-ink-muted">
          {title}
        </span>
        <span className="text-caption text-ink-muted motion-safe:animate-shimmer">Adding…</span>
      </div>
    </div>
  );
}

function LoadingRows() {
  return (
    <div role="status" className="col-span-full grid grid-cols-subgrid">
      <span className="sr-only">Loading your tasks…</span>
      {placeholderWidths.map((width) => (
        <div key={width} aria-hidden="true" className={rowClass}>
          <span className={`${controlCellClass} flex size-touch items-center justify-center`}>
            <Skeleton className="size-5" />
          </span>
          <div className={`${textCellClass} justify-center @wide:col-span-2`}>
            <Skeleton className={`h-3 ${width}`} />
          </div>
        </div>
      ))}
    </div>
  );
}
