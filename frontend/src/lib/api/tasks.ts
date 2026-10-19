import { type Task, taskListSchema, taskSchema } from "../schema/task.ts";
import type { TaskChanges } from "../task-draft.ts";
import { apiRequest, apiRequestNoContent } from "./client.ts";

/** What a new task needs: its title. The server puts it at the top. */
export type NewTask = Pick<Task, "title">;

/** The fields a PATCH can change; only the ones present are sent. */
export type TaskPatch = TaskChanges & Partial<Pick<Task, "completed">>;

const taskPath = (taskId: string): string => `/tasks/${encodeURIComponent(taskId)}`;

const listPath = (q: string): string =>
  q === "" ? "/tasks" : `/tasks?${new URLSearchParams({ q }).toString()}`;

/** The user's tasks in their order, or only those matching `q` when it is not empty. */
export const listTasks = async (q: string, signal?: AbortSignal): Promise<readonly Task[]> =>
  (await apiRequest(listPath(q), { schema: taskListSchema, signal })).items;

/** One task. */
export const getTask = (taskId: string, signal?: AbortSignal): Promise<Task> =>
  apiRequest(taskPath(taskId), { schema: taskSchema, signal });

/** Create a task at the top of the list. */
export const createTask = (input: NewTask): Promise<Task> =>
  apiRequest("/tasks", { method: "POST", body: input, schema: taskSchema });

/** Change some fields of a task. With `ifMatch`, the server refuses the change if the task is no longer that version. */
export const updateTask = (taskId: string, patch: TaskPatch, ifMatch?: number): Promise<Task> =>
  apiRequest(taskPath(taskId), { method: "PATCH", body: patch, ifMatch, schema: taskSchema });

/** Put a task right after `afterId`, or at the top when it is null. */
export const moveTask = (taskId: string, afterId: string | null): Promise<Task> =>
  apiRequest(`${taskPath(taskId)}/position`, {
    method: "PUT",
    body: { afterId },
    schema: taskSchema,
  });

/** Delete a task. */
export const deleteTask = (taskId: string): Promise<void> =>
  apiRequestNoContent(taskPath(taskId), { method: "DELETE" });
