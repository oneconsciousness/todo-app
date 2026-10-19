import { useNavigate, useParams } from "react-router";
import { type ApiError, ApiErrorCode } from "../lib/api/client.ts";
import { localIsoDate } from "../lib/due-date.ts";
import { useDeleteTask, useTask, useToggleTask, useUpdateTask } from "../lib/query/tasks.ts";
import { routes } from "../lib/routes.ts";
import { serverFieldErrors } from "../lib/schema/field-errors.ts";
import { taskIdParamSchema } from "../lib/schema/route.ts";
import type { Task } from "../lib/schema/task.ts";
import { type TaskDetailContent, TaskDetailView } from "../views/task-detail-view.tsx";

const draftFields = ["title", "notes", "dueDate"] as const;

const detailContent = (
  taskId: string | null,
  task: Task | undefined,
  error: ApiError | null,
): TaskDetailContent => {
  if (taskId === null || error?.code === ApiErrorCode.NotFound) return { status: "not-found" };
  if (task) return { status: "ready", task };
  return { status: "loading" };
};

// A 412 shows as "Changed elsewhere" and a field problem shows next to its field, so neither needs a second message.
const saveFailure = (error: ApiError | null): string | null => {
  if (error === null) return null;
  if (error.code === ApiErrorCode.VersionMismatch || error.code === ApiErrorCode.ValidationFailed)
    return null;
  return `Couldn't save the task. ${error.message}`;
};

const toggleFailure = (error: ApiError | null): string | null =>
  error && `Couldn't update the task, so it's back as it was. ${error.message}`;

/** The task detail route: one task to read, tick off, edit with `If-Match`, or delete. */
export function TaskDetailPage() {
  const params = useParams();
  const parsedId = taskIdParamSchema.safeParse(params.taskId);
  const taskId = parsedId.success ? parsedId.data : null;
  const task = useTask(taskId);
  const update = useUpdateTask();
  const toggle = useToggleTask();
  const remove = useDeleteTask();
  const navigate = useNavigate();

  return (
    <TaskDetailView
      content={detailContent(taskId, task.data, task.error)}
      today={localIsoDate(new Date())}
      saving={update.isPending}
      deleting={remove.isPending}
      failure={saveFailure(update.error) ?? toggleFailure(toggle.error)}
      fieldErrors={
        update.error?.code === ApiErrorCode.ValidationFailed
          ? serverFieldErrors(update.error.details, draftFields)
          : undefined
      }
      onSave={(id, changes, version) => {
        update.mutate({ taskId: id, changes, version });
      }}
      onToggle={(id, completed) => {
        toggle.mutate({ taskId: id, completed });
      }}
      onDelete={(id) => {
        remove.mutate(id);
        void navigate(routes.tasks);
      }}
    />
  );
}
