import type { ReactNode } from "react";
import { type DueTone, dueLabel } from "../../lib/due-date.ts";
import { routes } from "../../lib/routes.ts";
import type { Task } from "../../lib/schema/task.ts";
import { Checkbox } from "./checkbox.tsx";
import { Link } from "./link.tsx";

const columns = {
  reorderable:
    "grid-cols-[var(--spacing-touch)_minmax(0,1fr)_var(--spacing-touch)] @wide:grid-cols-[var(--spacing-touch)_var(--spacing-touch)_minmax(0,1fr)_var(--container-due)]",
  fixed:
    "grid-cols-[var(--spacing-touch)_minmax(0,1fr)] @wide:grid-cols-[var(--spacing-touch)_minmax(0,1fr)_var(--container-due)]",
} as const;

/**
 * The column template of a ledger line. Narrow: tick box, text, then the handle at the right edge.
 * Wide: handle, tick box, text, then the due column. Without a handle the handle column is dropped.
 */
export const ledgerColumns = (reorderable: boolean): string =>
  reorderable ? columns.reorderable : columns.fixed;

/** The ruling between ledger lines. */
export const ledgerRuleClass = "border-b border-rule last:border-b-0";

/** The colour and weight of a due date in each tone, shared by the list and the detail screen. */
export const dueToneClass: Readonly<Record<DueTone, string>> = {
  alert: "font-medium text-alert",
  emphasis: "font-medium text-ink",
  quiet: "text-ink-muted",
};

/** Props for `LedgerCells`. */
export interface LedgerCellsProps {
  /** The drag handle, or a falsy value when the line has no handle column. */
  readonly handle: ReactNode;
  readonly control: ReactNode;
  readonly children: ReactNode;
  readonly due?: ReactNode;
}

/**
 * The cells of one ledger line: tick box, the text right of the red double margin rule, the due date (under the
 * title when narrow, in its own ruled column when wide) and the handle. Real, pending and placeholder lines all use
 * it, so they align.
 */
export function LedgerCells({ handle, control, children, due }: LedgerCellsProps) {
  return (
    <>
      {handle && <span className="order-last @wide:order-first @wide:py-1">{handle}</span>}
      <span className="flex size-touch items-center justify-center @wide:box-content @wide:py-1">
        {control}
      </span>
      <div className="relative flex min-w-0 flex-col gap-1 border-l-3 border-double border-margin py-2 pr-1 pl-3 @wide:contents">
        <div className="flex min-w-0 flex-col gap-1 @wide:relative @wide:border-l-3 @wide:border-double @wide:border-margin @wide:px-4 @wide:py-3">
          {children}
        </div>
        <p className="text-caption tabular-nums empty:hidden @wide:block @wide:self-stretch @wide:border-l @wide:border-margin/40 @wide:px-4 @wide:pt-4 @wide:pb-3 @wide:text-right @wide:empty:block">
          {due}
        </p>
      </div>
    </>
  );
}

/** Props for `LedgerHead`. */
export interface LedgerHeadProps {
  readonly reorderable: boolean;
}

/** The ledger's column headings, shown on wide screens only and hidden from screen readers. */
export function LedgerHead({ reorderable }: LedgerHeadProps) {
  return (
    <div
      aria-hidden="true"
      className={`hidden border-b border-rule-strong text-caption font-medium tracking-caps text-ink-muted uppercase @wide:grid ${ledgerColumns(reorderable)}`}
    >
      <span className={reorderable ? "col-span-2" : undefined} />
      <span className="border-l-3 border-double border-margin px-4 pt-3 pb-2">Task</span>
      <span className="border-l border-margin/40 px-4 pt-3 pb-2 text-right">Due</span>
    </div>
  );
}

/** Props for `TaskRow`. */
export interface TaskRowProps {
  readonly task: Task;
  readonly today: string;
  readonly handle: ReactNode;
  readonly onToggle: (taskId: string, completed: boolean) => void;
}

/** A task on a ledger line: tick box, title with notes, due date and drag handle. */
export function TaskRow({ task, today, handle, onToggle }: TaskRowProps) {
  const due = task.dueDate ? dueLabel(task.dueDate, today, task.completed) : null;
  return (
    <LedgerCells
      handle={handle}
      control={
        <Checkbox
          label={`Completed: ${task.title}`}
          checked={task.completed}
          onChange={(completed) => {
            onToggle(task.id, completed);
          }}
        />
      }
      due={
        due && (
          <time dateTime={task.dueDate ?? undefined} className={dueToneClass[due.tone]}>
            {due.text}
          </time>
        )
      }
    >
      <Link
        href={routes.task(task.id)}
        className={`leading-(--text-lead--line-height) break-words after:absolute after:inset-0 ${task.completed ? "text-ink-muted line-through decoration-ink-muted" : "text-ink"}`}
      >
        {task.title}
      </Link>
      {task.notes && <p className="truncate text-caption text-ink-muted">{task.notes}</p>}
    </LedgerCells>
  );
}
