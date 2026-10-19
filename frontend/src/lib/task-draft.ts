import type { Task, TaskDraft, TaskEdit } from "./schema/task.ts";

/** The fields a PATCH changes, holding only the ones that differ from the task. */
export type TaskChanges = Partial<TaskEdit>;

const editable = ["title", "notes", "dueDate"] as const satisfies readonly (keyof TaskEdit)[];

const compared = [
  "title",
  "notes",
  "dueDate",
  "completed",
] as const satisfies readonly (keyof Task)[];

const fieldNames: Readonly<Record<(typeof compared)[number], string>> = {
  title: "title",
  notes: "notes",
  dueDate: "due date",
  completed: "completed",
};

/** Start the edit form from a task; no due date becomes an empty date field. */
export const draftFrom = (task: Task): TaskDraft => ({
  title: task.title,
  notes: task.notes,
  dueDate: task.dueDate ?? "",
});

/** The fields of a validated edit that differ from the task, so the PATCH sends only those. */
export const changesFrom = (task: Task, edit: TaskEdit): TaskChanges =>
  editable.reduce<TaskChanges>(
    (changes, field) =>
      task[field] === edit[field] ? changes : { ...changes, [field]: edit[field] },
    {},
  );

/** Name, in plain words, each field that differs between two versions of a task. */
export const changedFieldNames = (before: Task, after: Task): readonly string[] =>
  compared.filter((field) => before[field] !== after[field]).map((field) => fieldNames[field]);
