import { type ChangeEvent, type SubmitEvent, useId, useState } from "react";
import { Button } from "../components/ui/button.tsx";
import { Checkbox } from "../components/ui/checkbox.tsx";
import { Icon } from "../components/ui/icon.tsx";
import { InlineConfirm } from "../components/ui/inline-confirm.tsx";
import { Link } from "../components/ui/link.tsx";
import { Notice } from "../components/ui/notice.tsx";
import { Page } from "../components/ui/page.tsx";
import { Skeleton } from "../components/ui/skeleton.tsx";
import { dueToneClass } from "../components/ui/task-row.tsx";
import { TextArea } from "../components/ui/text-area.tsx";
import { TextField } from "../components/ui/text-field.tsx";
import { dueLabel, formatDay } from "../lib/due-date.ts";
import { routes } from "../lib/routes.ts";
import { type FieldErrors, fieldErrors } from "../lib/schema/field-errors.ts";
import { type Task, type TaskDraft, type TaskEdit, taskDraftSchema } from "../lib/schema/task.ts";
import {
  type TaskChanges,
  changedFieldNames,
  changesFrom,
  draftFields,
  draftFrom,
} from "../lib/task-draft.ts";
import { NotFoundView } from "./not-found-view.tsx";

/** What the detail screen shows: a placeholder, not found (missing or someone else's), or the task. */
export type TaskDetailContent =
  | { readonly status: "loading" }
  | { readonly status: "not-found" }
  | { readonly status: "ready"; readonly task: Task };

/** Props for `TaskDetailView`. The task comes in; saves, toggles and deletes go out as callbacks. */
export interface TaskDetailViewProps {
  readonly content: TaskDetailContent;
  /** Today as `YYYY-MM-DD`, so the due date reads relative to it. */
  readonly today: string;
  readonly saving: boolean;
  readonly deleting: boolean;
  /** What the last save or delete failed with, in words for the user; null when nothing failed. */
  readonly failure: string | null;
  /** The server's problems with the fields of the last save, shown next to each field until the user edits it. */
  readonly fieldErrors?: FieldErrors<TaskDraft> | undefined;
  /** Save the changed fields. `version` is the one the edit started from; the API rejects the save if the task has changed since. */
  readonly onSave: (taskId: string, changes: TaskChanges, version: number) => void;
  readonly onToggle: (taskId: string, completed: boolean) => void;
  readonly onDelete: (taskId: string) => void;
}

const inset = "px-4 @wide:px-12";
const captionCaps = "text-caption font-medium tracking-caps text-ink-muted uppercase";

/** The task detail screen: read every field, tick it off, edit and save it, or delete it after a confirm step. */
export function TaskDetailView(props: TaskDetailViewProps) {
  const { content } = props;
  switch (content.status) {
    case "loading":
      return <LoadingEntry />;
    case "not-found":
      return <NotFoundView subject="task" />;
    case "ready":
      return <TaskEntry key={content.task.id} {...props} task={content.task} />;
    default: {
      const unreachable: never = content;
      return unreachable;
    }
  }
}

interface Editing {
  /** The version the draft started from, or was last rebased onto. */
  readonly base: Task;
  readonly draft: TaskDraft;
  readonly errors: FieldErrors<TaskDraft>;
  /** The edit sent with the last save, so the view can recognise its own save when it comes back. */
  readonly submitted: TaskEdit | null;
  /** The fields the server's errors still apply to: every field once saved, less each one edited since. */
  readonly serverErrorsApply: ReadonlySet<keyof TaskDraft>;
}

interface TaskEntryProps extends Omit<TaskDetailViewProps, "content"> {
  readonly task: Task;
}

const isEmpty = (changes: TaskChanges): boolean => Object.keys(changes).length === 0;

function TaskEntry({
  task,
  today,
  saving,
  deleting,
  failure,
  fieldErrors: serverErrors,
  onSave,
  onToggle,
  onDelete,
}: TaskEntryProps) {
  const headingId = useId();
  const [editing, setEditing] = useState<Editing | null>(null);
  const [confirmingDelete, setConfirmingDelete] = useState(false);
  const [seenVersion, setSeenVersion] = useState(task.version);

  // A newer version came in (React's pattern for adjusting state when a prop changes). If it is our own save,
  // leave edit mode; if it changes nothing the user can see, quietly rebase the draft onto it.
  if (task.version !== seenVersion) {
    setSeenVersion(task.version);
    if (editing?.submitted && isEmpty(changesFrom(task, editing.submitted))) setEditing(null);
    else if (editing && changedFieldNames(editing.base, task).length === 0)
      setEditing({ ...editing, base: task });
  }

  const startFrom = (latest: Task) => {
    setEditing({
      base: latest,
      draft: draftFrom(latest),
      errors: {},
      submitted: null,
      serverErrorsApply: new Set(),
    });
  };

  const edit =
    (field: keyof TaskDraft) => (event: ChangeEvent<HTMLInputElement | HTMLTextAreaElement>) => {
      const { value } = event.target;
      setEditing(
        (current) =>
          current && {
            ...current,
            draft: { ...current.draft, [field]: value },
            errors: { ...current.errors, [field]: undefined },
            submitted: null,
            serverErrorsApply: new Set(
              [...current.serverErrorsApply].filter((name) => name !== field),
            ),
          },
      );
    };

  // The form's own check wins; the server's message stays until the field is edited after the save.
  const errorFor = (current: Editing, field: keyof TaskDraft): string | undefined =>
    current.errors[field] ??
    (current.serverErrorsApply.has(field) ? serverErrors?.[field] : undefined);

  const save = (event: SubmitEvent<HTMLFormElement>) => {
    event.preventDefault();
    if (!editing) return;
    const result = taskDraftSchema.safeParse(editing.draft);
    if (!result.success) {
      setEditing({ ...editing, errors: fieldErrors(result.error) });
      return;
    }
    const changes = changesFrom(editing.base, result.data);
    if (isEmpty(changes)) {
      setEditing(null);
      return;
    }
    onSave(task.id, changes, editing.base.version);
    setEditing({ ...editing, submitted: result.data, serverErrorsApply: new Set(draftFields) });
  };

  const changedElsewhere =
    editing && task.version > editing.base.version ? changedFieldNames(editing.base, task) : null;
  const due = task.dueDate ? dueLabel(task.dueDate, today, task.completed) : null;

  return (
    <Page labelledBy={headingId}>
      <div className={inset}>
        <Link
          href={routes.tasks}
          className={`inline-flex min-h-touch items-center gap-2 transition-colors hover:text-ink ${captionCaps}`}
        >
          <Icon name="back" className="size-4" />
          All tasks
        </Link>
      </div>

      {failure && (
        <div className={inset}>
          <Notice>{failure}</Notice>
        </div>
      )}

      {editing ? (
        <form noValidate onSubmit={save} className={`flex flex-col gap-6 ${inset}`}>
          <h1 id={headingId} className="font-display text-title font-medium text-balance">
            Edit task
          </h1>
          {changedElsewhere && (
            <Notice
              actions={[
                {
                  label: "Use the latest",
                  onAction: () => {
                    startFrom(task);
                  },
                },
                {
                  label: "Keep my edits",
                  onAction: () => {
                    setEditing({ ...editing, base: task });
                  },
                },
              ]}
            >
              <strong className="font-semibold">Changed elsewhere.</strong> Another tab or device
              saved a newer version ({changedElsewhere.join(", ")}). Use the latest, or keep your
              edits and save over it.
            </Notice>
          )}
          <fieldset disabled={saving} className="flex min-w-0 flex-col gap-4">
            <TextField
              label="Title"
              value={editing.draft.title}
              error={errorFor(editing, "title")}
              onChange={edit("title")}
            />
            <TextField
              label="Due date"
              type="date"
              value={editing.draft.dueDate}
              error={errorFor(editing, "dueDate")}
              onChange={edit("dueDate")}
              className="@wide:w-1/2"
            />
            <TextArea
              label="Notes"
              rows={6}
              value={editing.draft.notes}
              error={errorFor(editing, "notes")}
              onChange={edit("notes")}
            />
          </fieldset>
          <div className="flex flex-wrap gap-2">
            <Button type="submit" variant="primary" disabled={saving}>
              {saving ? "Saving…" : "Save changes"}
            </Button>
            <Button
              disabled={saving}
              onClick={() => {
                setEditing(null);
              }}
            >
              Cancel
            </Button>
          </div>
        </form>
      ) : (
        <>
          <header className={`flex items-start gap-1 ${inset}`}>
            <span className="-ml-3">
              <Checkbox
                label={`Completed: ${task.title}`}
                checked={task.completed}
                onChange={(completed) => {
                  onToggle(task.id, completed);
                }}
              />
            </span>
            <div className="flex min-w-0 flex-col gap-2 pt-1">
              <h1
                id={headingId}
                className={`font-display text-display font-medium text-balance break-words ${task.completed ? "text-ink-muted line-through decoration-2" : ""}`}
              >
                {task.title}
              </h1>
              {due && (
                <p className="tabular-nums">
                  <time dateTime={task.dueDate ?? undefined} className={dueToneClass[due.tone]}>
                    {due.text}
                  </time>
                </p>
              )}
            </div>
          </header>

          <dl className={`grid grid-cols-3 gap-4 border-y border-rule py-4 ${inset}`}>
            {[
              ["Status", task.completed ? "Done" : "Open"],
              ["Entered", formatDay(task.createdAt, today)],
              ["Changed", formatDay(task.updatedAt, today)],
            ].map(([term, detail]) => (
              <div key={term} className="flex flex-col gap-1">
                <dt className={captionCaps}>{term}</dt>
                <dd className="tabular-nums">{detail}</dd>
              </div>
            ))}
          </dl>

          <section className={`flex flex-col gap-2 ${inset}`}>
            <h2 className={captionCaps}>Notes</h2>
            {task.notes ? (
              <p className="ruled break-words whitespace-pre-line">{task.notes}</p>
            ) : (
              <p className="text-ink-muted">No notes yet. Edit the task to add some.</p>
            )}
          </section>

          <div className={`flex flex-wrap gap-2 ${inset}`}>
            {confirmingDelete ? (
              <InlineConfirm
                message={`Delete “${task.title}”? This can't be undone.`}
                confirmLabel="Delete task"
                busyLabel="Deleting…"
                cancelLabel="Keep it"
                busy={deleting}
                onConfirm={() => {
                  onDelete(task.id);
                }}
                onCancel={() => {
                  setConfirmingDelete(false);
                }}
              />
            ) : (
              <>
                <Button
                  variant="primary"
                  onClick={() => {
                    startFrom(task);
                  }}
                >
                  Edit task
                </Button>
                <Button
                  onClick={() => {
                    setConfirmingDelete(true);
                  }}
                >
                  Delete
                </Button>
              </>
            )}
          </div>
        </>
      )}
    </Page>
  );
}

function LoadingEntry() {
  return (
    <Page>
      <div role="status" className={`flex flex-col gap-4 ${inset}`}>
        <span className="sr-only">Loading the task…</span>
        <Skeleton className="h-3 w-1/4" />
        <Skeleton className="h-8 w-3/4" />
        <Skeleton className="h-3 w-1/2" />
        <Skeleton className="mt-6 h-3 w-full" />
        <Skeleton className="h-3 w-2/3" />
      </div>
    </Page>
  );
}
