import { useState } from "react";
import { useDebouncedValue } from "../hooks/use-debounced-value.ts";
import { localIsoDate } from "../lib/due-date.ts";
import type { ApiError } from "../lib/api/client.ts";
import { useTaskNotices, useTasks, useToggleTask } from "../lib/query/tasks.ts";
import type { Task } from "../lib/schema/task.ts";
import { type TaskListContent, TaskListView } from "../views/task-list-view.tsx";

const searchDelayMs = 250;

const ignore = (): void => undefined;

// Tasks already on screen stay there through a failed refetch; the error screen is only for a first load that failed.
const listContent = (
  tasks: readonly Task[] | undefined,
  error: ApiError | null,
): TaskListContent => {
  if (tasks) return { status: "ready", tasks };
  if (error) return { status: "error", message: error.message };
  return { status: "loading" };
};

/** The task list route: the user's tasks, searched on the server as they type. */
export function TaskListPage() {
  const [query, setQuery] = useState("");
  const term = useDebouncedValue(query.trim(), searchDelayMs);
  const list = useTasks(term);
  const toggle = useToggleTask();
  const { notice, dismiss } = useTaskNotices();

  return (
    <TaskListView
      content={listContent(list.data, list.error)}
      today={localIsoDate(new Date())}
      query={query}
      searchPending={query.trim() !== term || list.isPlaceholderData}
      pendingCreate={null}
      failure={notice === null ? null : { message: notice }}
      onQueryChange={setQuery}
      onCreate={ignore}
      onToggle={(taskId, completed) => {
        toggle.mutate({ taskId, completed });
      }}
      onMove={ignore}
      onRetry={() => {
        void list.refetch();
      }}
      onDismissFailure={dismiss}
    />
  );
}
