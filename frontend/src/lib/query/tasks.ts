import {
  type MutationKey,
  type QueryClient,
  type QueryKey,
  keepPreviousData,
  skipToken,
  useMutation,
  useMutationState,
  useQuery,
  useQueryClient,
} from "@tanstack/react-query";
import { useState } from "react";
import { type ApiError, ApiErrorCode } from "../api/client.ts";
import { createTask, deleteTask, getTask, listTasks, moveTask, updateTask } from "../api/tasks.ts";
import type { Task } from "../schema/task.ts";
import type { TaskChanges } from "../task-draft.ts";
import { moveAfter } from "../tasks/order.ts";
import { taskKeys } from "./keys.ts";

/**
 * The user's tasks, or the matches for `q`. Each term is cached on its own, so a late answer for an older term never
 * replaces a newer one; the previous results stay on screen while the next load; and a superseded request is
 * aborted ([query cancellation](https://tanstack.com/query/v5/docs/framework/react/guides/query-cancellation)).
 */
export const useTasks = (q: string) =>
  useQuery({
    queryKey: taskKeys.list(q),
    queryFn: ({ signal }) => listTasks(q, signal),
    placeholderData: keepPreviousData,
  });

/**
 * One task, or nothing to fetch when `taskId` is null. A 404 (missing, or someone else's) is an answer the page shows;
 * any other failure goes to the route error boundary.
 */
export const useTask = (taskId: string | null) =>
  useQuery({
    queryKey: taskKeys.detail(taskId ?? ""),
    queryFn: taskId === null ? skipToken : ({ signal }) => getTask(taskId, signal),
    throwOnError: (error) => !isNotFound(error),
  });

/** A save from the detail screen: the changed fields, and the version the edit started from. */
export interface UpdateVariables {
  readonly taskId: string;
  readonly changes: TaskChanges;
  readonly version: number;
}

/**
 * Save a task's edited fields with `If-Match`, so a save made against an older version is refused (412) rather than
 * overwriting someone else's change. A 412 reloads the task, so the screen can show what changed.
 */
export const useUpdateTask = () => {
  const client = useQueryClient();
  return useMutation({
    mutationKey: taskKeys.mutations.update,
    mutationFn: ({ taskId, changes, version }: UpdateVariables) =>
      updateTask(taskId, changes, version),
    onSuccess: (task) => {
      client.setQueryData(taskKeys.detail(task.id), task);
      void client.invalidateQueries({ queryKey: taskKeys.lists() });
    },
    onError: (error, { taskId }) => {
      if (error.code === ApiErrorCode.VersionMismatch)
        void client.invalidateQueries({ queryKey: taskKeys.detail(taskId) });
    },
  });
};

/** Every cached task list as it was before an optimistic change, to put back if the change fails. */
export type ListSnapshot = readonly (readonly [QueryKey, readonly Task[] | undefined])[];

/**
 * Build the first step of an optimistic change from a pure list transform: stop list fetches that would overwrite it,
 * keep a snapshot, apply `apply` to every cached list, and hand back the snapshot for a rollback.
 */
export const optimisticListUpdate =
  <V>(client: QueryClient, apply: (items: readonly Task[], vars: V) => readonly Task[]) =>
  async (vars: V): Promise<ListSnapshot> => {
    await client.cancelQueries({ queryKey: taskKeys.lists() });
    const snapshot = client.getQueriesData<readonly Task[]>({ queryKey: taskKeys.lists() });
    client.setQueriesData<readonly Task[]>(
      { queryKey: taskKeys.lists() },
      (items) => items && apply(items, vars),
    );
    return snapshot;
  };

/** Put every cached list back as the snapshot had it. */
export const restoreLists = (client: QueryClient, snapshot: ListSnapshot): void => {
  snapshot.forEach(([key, items]) => {
    client.setQueryData(key, items);
  });
};

/** A tick or untick from a list or the detail screen. */
export interface ToggleVariables {
  readonly taskId: string;
  readonly completed: boolean;
}

const toggleIn = (items: readonly Task[], { taskId, completed }: ToggleVariables) =>
  items.map((task) => (task.id === taskId ? { ...task, completed } : task));

// A task the server no longer has leaves every list and its detail entry.
const forgetTask = (client: QueryClient, taskId: string): void => {
  client.setQueriesData<readonly Task[]>({ queryKey: taskKeys.lists() }, (items) =>
    items?.filter((task) => task.id !== taskId),
  );
  client.removeQueries({ queryKey: taskKeys.detail(taskId) });
};

const isNotFound = (error: ApiError): boolean => error.code === ApiErrorCode.NotFound;

/**
 * Tick a task off, or reopen it, at once: every cached list and the detail show the change before the server answers.
 * A failure puts them back; a 404 means the task was deleted elsewhere, so it leaves the screen instead. No `If-Match`
 * is sent, because a tick sets an absolute value and the latest one should win.
 */
export const useToggleTask = () => {
  const client = useQueryClient();
  const updateLists = optimisticListUpdate(client, toggleIn);
  return useMutation({
    mutationKey: taskKeys.mutations.toggle,
    mutationFn: ({ taskId, completed }: ToggleVariables) => updateTask(taskId, { completed }),
    onMutate: async (vars) => {
      const detailKey = taskKeys.detail(vars.taskId);
      await client.cancelQueries({ queryKey: detailKey });
      const detail = client.getQueryData<Task>(detailKey);
      const lists = await updateLists(vars);
      client.setQueryData<Task>(
        detailKey,
        (task) => task && { ...task, completed: vars.completed },
      );
      return { lists, detail };
    },
    onSuccess: (task) => {
      client.setQueryData(taskKeys.detail(task.id), task);
    },
    onError: (error, { taskId }, snapshot) => {
      if (isNotFound(error)) {
        forgetTask(client, taskId);
        return;
      }
      if (!snapshot) return;
      restoreLists(client, snapshot.lists);
      client.setQueryData(taskKeys.detail(taskId), snapshot.detail);
    },
    // Not awaited: the user hears about a failure as soon as it happens, not after the lists have reloaded.
    onSettled: () => {
      void client.invalidateQueries({ queryKey: taskKeys.lists() });
    },
  });
};

/** A reorder: put the task right after `afterId`, or at the top when it is null. */
export interface MoveVariables {
  readonly taskId: string;
  readonly afterId: string | null;
}

const moveIn = (items: readonly Task[], { taskId, afterId }: MoveVariables) =>
  moveAfter(items, taskId, afterId);

/**
 * Move a task at once on screen, while the moves themselves reach the server one at a time and in the order the user
 * made them: they share one mutation scope ([mutation scopes](https://tanstack.com/query/v5/docs/framework/react/guides/mutations#mutation-scopes)).
 * The lists reload only after the last queued move, so a refetch never lands between two of them
 * ([concurrent optimistic updates](https://tkdodo.eu/blog/concurrent-optimistic-updates-in-react-query)).
 */
export const useMoveTask = () => {
  const client = useQueryClient();
  const updateLists = optimisticListUpdate(client, moveIn);
  return useMutation({
    mutationKey: taskKeys.mutations.move,
    scope: { id: "task-order" },
    mutationFn: ({ taskId, afterId }: MoveVariables) => moveTask(taskId, afterId),
    onMutate: (vars: MoveVariables) => updateLists(vars),
    onError: (error, { taskId }, snapshot) => {
      if (isNotFound(error)) forgetTask(client, taskId);
      else if (snapshot) restoreLists(client, snapshot);
    },
    onSettled: () => {
      if (client.isMutating({ mutationKey: taskKeys.mutations.move }) === 1)
        void client.invalidateQueries({ queryKey: taskKeys.lists() });
    },
  });
};

/**
 * Add a task. It is not optimistic: the server picks its place at the top, so the list shows it once the server has
 * it, and the mutation stays pending until the lists have reloaded with it in.
 */
export const useCreateTask = () => {
  const client = useQueryClient();
  return useMutation({
    mutationKey: taskKeys.mutations.create,
    mutationFn: createTask,
    onSuccess: () => client.invalidateQueries({ queryKey: taskKeys.lists() }),
  });
};

const removeFrom = (items: readonly Task[], taskId: string) =>
  items.filter((task) => task.id !== taskId);

/**
 * Delete a task at once: it leaves every cached list and its detail entry before the server answers, and comes back
 * if the delete fails. A 404 leaves it gone, since it is gone either way.
 */
export const useDeleteTask = () => {
  const client = useQueryClient();
  const updateLists = optimisticListUpdate(client, removeFrom);
  return useMutation({
    mutationKey: taskKeys.mutations.remove,
    mutationFn: deleteTask,
    onMutate: async (taskId: string) => {
      const lists = await updateLists(taskId);
      client.removeQueries({ queryKey: taskKeys.detail(taskId) });
      return lists;
    },
    onError: (error, _taskId, snapshot) => {
      if (!isNotFound(error) && snapshot) restoreLists(client, snapshot);
    },
    onSettled: () => {
      void client.invalidateQueries({ queryKey: taskKeys.lists() });
    },
  });
};

/**
 * The ids of tasks whose delete the server has not answered yet. A list that loads or refetches meanwhile still holds
 * them, so the screen leaves them out until the delete settles.
 */
export const usePendingDeletes = (): ReadonlySet<string> =>
  new Set(
    useMutationState({
      filters: { mutationKey: taskKeys.mutations.remove, status: "pending" },
      select: (mutation) => mutation.state.variables,
    }).filter((taskId): taskId is string => typeof taskId === "string"),
  );

type NoticeKind = "toggle" | "move" | "remove" | "create";

const noticeKinds: Readonly<Record<string, NoticeKind>> = {
  [taskKeys.mutations.toggle[1]]: "toggle",
  [taskKeys.mutations.move[1]]: "move",
  [taskKeys.mutations.remove[1]]: "remove",
  [taskKeys.mutations.create[1]]: "create",
};

const failedTo: Readonly<Record<NoticeKind, string>> = {
  toggle: "Couldn't update the task, so it's back as it was.",
  move: "Couldn't move the task, so it's back where it was.",
  remove: "Couldn't delete the task, so it's back in the list.",
  create: "Couldn't add the task.",
};

// A delete that finds the task already gone did what the user asked, so there is nothing to tell.
const isWorthTelling = (kind: NoticeKind, error: ApiError): boolean =>
  !(kind === "remove" && isNotFound(error));

// A 404 means someone deleted the task elsewhere; anything else says what was undone and why.
const noticeFor = (kind: NoticeKind, error: ApiError): string =>
  isNotFound(error) ? "That task was deleted elsewhere." : `${failedTo[kind]} ${error.message}`;

const kindOf = (key: MutationKey | undefined): NoticeKind | undefined => {
  const [, name] = key ?? [];
  return typeof name === "string" ? noticeKinds[name] : undefined;
};

interface FailedChange {
  readonly kind: NoticeKind;
  readonly error: ApiError;
  readonly submittedAt: number;
}

/**
 * The newest failed list change, wherever it was started (the detail screen included), until the user dismisses it.
 * It is read from the mutation cache, so no other store holds it.
 */
export const useTaskNotices = (): {
  readonly notice: string | null;
  readonly dismiss: () => void;
} => {
  const [dismissed, setDismissed] = useState<ReadonlySet<number>>(new Set());
  const failures = useMutationState({
    filters: { mutationKey: taskKeys.all, status: "error" },
    select: (mutation) => ({
      kind: kindOf(mutation.options.mutationKey),
      error: mutation.state.error,
      submittedAt: mutation.state.submittedAt,
    }),
  });
  const newest = failures
    .filter(
      (failure): failure is FailedChange =>
        failure.kind !== undefined &&
        failure.error !== null &&
        isWorthTelling(failure.kind, failure.error) &&
        !dismissed.has(failure.submittedAt),
    )
    .reduce<FailedChange | null>(
      (latest, failure) => (latest && latest.submittedAt >= failure.submittedAt ? latest : failure),
      null,
    );
  return {
    notice: newest && noticeFor(newest.kind, newest.error),
    dismiss: () => {
      if (newest) setDismissed((current) => new Set([...current, newest.submittedAt]));
    },
  };
};
