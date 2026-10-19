import type { ReactNode } from "react";
import { type DueTone, dueLabel } from "../../lib/due-date.ts";
import type { Task } from "../../lib/schema/task.ts";
import { taskPath } from "../../lib/task-list.ts";
import { Checkbox } from "./checkbox.tsx";
import { Link } from "./link.tsx";

/** One ruled ledger line; a row's cells sit on its parent's grid columns. */
export const rowClass =
  "col-span-full grid grid-cols-subgrid items-start border-b border-rule bg-sheet last:border-b-0";

/** The cell for a row's handle or tick box, so placeholders line up with real rows. */
export const controlCellClass = "py-1";

/** The cell right of the red double margin rule, holding a row's text. */
export const textCellClass =
  "relative flex min-w-0 flex-col gap-1 border-l-3 border-double border-margin px-4 py-3";

const dueTones: Readonly<Record<DueTone, string>> = {
  alert: "font-medium text-alert",
  emphasis: "font-medium text-ink",
  quiet: "text-ink-muted",
};

/** Props for `TaskRow`. */
export interface TaskRowProps {
  readonly task: Task;
  readonly today: string;
  readonly handle: ReactNode;
  readonly onToggle: (taskId: string, completed: boolean) => void;
}

/** A task's cells on a ledger line: drag handle, tick box, title with notes, and the due date. */
export function TaskRow({ task, today, handle, onToggle }: TaskRowProps) {
  const due = task.dueDate ? dueLabel(task.dueDate, today, task.completed) : null;
  return (
    <>
      {handle && <span className={`${controlCellClass} pl-1`}>{handle}</span>}
      <span className={controlCellClass}>
        <Checkbox
          label={`Completed: ${task.title}`}
          checked={task.completed}
          onChange={(completed) => {
            onToggle(task.id, completed);
          }}
        />
      </span>
      <div
        className={`${textCellClass} @wide:col-span-2 @wide:grid @wide:grid-cols-subgrid @wide:gap-0 @wide:p-0`}
      >
        <div className="flex min-w-0 flex-col gap-1 @wide:px-4 @wide:py-3">
          <Link
            href={taskPath(task.id)}
            className={`leading-(--text-lead--line-height) break-words after:absolute after:inset-0 ${task.completed ? "text-ink-muted line-through decoration-ink-muted" : "text-ink"}`}
          >
            {task.title}
          </Link>
          {task.notes && <p className="truncate text-caption text-ink-muted">{task.notes}</p>}
        </div>
        <p className="text-caption tabular-nums empty:hidden @wide:block @wide:self-stretch @wide:border-l @wide:border-margin/40 @wide:px-4 @wide:pt-4 @wide:pb-3 @wide:text-right">
          {due && (
            <time dateTime={task.dueDate ?? undefined} className={dueTones[due.tone]}>
              {due.text}
            </time>
          )}
        </p>
      </div>
    </>
  );
}
