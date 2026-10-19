/** How strongly a due date should draw the eye. */
export type DueTone = "alert" | "emphasis" | "quiet";

/** The text and tone a task row shows for its due date. */
export interface DueLabel {
  readonly text: string;
  readonly tone: DueTone;
}

const dayMs = 86_400_000;

const toUtc = (isoDate: string): Date => new Date(`${isoDate}T00:00:00Z`);

const daysBetween = (from: string, to: string): number =>
  Math.round((toUtc(to).getTime() - toUtc(from).getTime()) / dayMs);

const sameYear = new Intl.DateTimeFormat("en-US", {
  weekday: "short",
  month: "short",
  day: "numeric",
  timeZone: "UTC",
});

const otherYear = new Intl.DateTimeFormat("en-US", {
  weekday: "short",
  month: "short",
  day: "numeric",
  year: "numeric",
  timeZone: "UTC",
});

const formatDate = (dueDate: string, today: string): string =>
  (dueDate.slice(0, 4) === today.slice(0, 4) ? sameYear : otherYear).format(toUtc(dueDate));

/** Describe a `YYYY-MM-DD` due date relative to today; a completed task is never overdue. */
export const dueLabel = (dueDate: string, today: string, completed: boolean): DueLabel => {
  const days = daysBetween(today, dueDate);
  const date = formatDate(dueDate, today);
  if (completed) return { text: `Due ${date}`, tone: "quiet" };
  if (days < 0) return { text: `Overdue · ${date}`, tone: "alert" };
  if (days === 0) return { text: "Due today", tone: "emphasis" };
  if (days === 1) return { text: "Due tomorrow", tone: "quiet" };
  return { text: `Due ${date}`, tone: "quiet" };
};
