import { z } from "zod";

/** A task title as the user types it: trimmed, 1 to 200 characters (spec D8). */
export const titleSchema = z
  .string()
  .trim()
  .min(1, "Add a title.")
  .max(200, "Keep the title to 200 characters.");

/** Task notes: free text up to 5,000 characters, empty when there are none. */
export const notesSchema = z.string().max(5000, "Keep the notes to 5,000 characters.");

/** One task as the API sends it (camelCase on the wire). */
export const taskSchema = z.object({
  id: z.uuid(),
  title: titleSchema,
  notes: notesSchema,
  completed: z.boolean(),
  dueDate: z.iso.date().nullable(),
  rank: z.string(),
  version: z.int().positive(),
  createdAt: z.iso.datetime({ offset: true }),
  updatedAt: z.iso.datetime({ offset: true }),
});

/** One task, typed from its schema. */
export type Task = z.infer<typeof taskSchema>;

/** The task edit form: title, notes, and a due date field that is empty when there is none. */
export const taskDraftSchema = z.object({
  title: titleSchema,
  notes: notesSchema,
  dueDate: z
    .union([z.literal(""), z.iso.date("Pick a date from the calendar.")])
    .transform((date) => (date === "" ? null : date)),
});

/** The edit form's values as the fields hold them. */
export type TaskDraft = z.input<typeof taskDraftSchema>;

/** The edit form's values once validated, ready to compare with the task. */
export type TaskEdit = z.output<typeof taskDraftSchema>;

/** The list envelope `{"items": [...]}` that `GET /api/v1/tasks` returns. */
export const taskListSchema = z.object({ items: z.array(taskSchema) });
