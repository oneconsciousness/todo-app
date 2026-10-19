import type { Task } from "./schema/task.ts";

/** Open and completed counts for a list of tasks. */
export interface TaskSummary {
  readonly open: number;
  readonly done: number;
}

/** A reorder as the API takes it: put `taskId` right after `afterId`, or at the top when null. */
export interface Move {
  readonly taskId: string;
  readonly afterId: string | null;
}

/** Count open and completed tasks. */
export const summarize = (tasks: readonly Task[]): TaskSummary =>
  tasks.reduce<TaskSummary>(
    (counts, task) =>
      task.completed ? { ...counts, done: counts.done + 1 } : { ...counts, open: counts.open + 1 },
    { open: 0, done: 0 },
  );

/** True when the search box holds a term, which also turns reordering off (spec D6). */
export const isSearching = (query: string): boolean => query.trim() !== "";

/** The one line under the list heading: counts, matches, or that a search is running. */
export const listSummary = (
  tasks: readonly Task[],
  query: string,
  searchPending: boolean,
): string => {
  if (searchPending) return "Searching…";
  if (!isSearching(query)) {
    const { open, done } = summarize(tasks);
    return `${String(open)} open · ${String(done)} done`;
  }
  if (tasks.length === 0) return "No matches.";
  const noun = tasks.length === 1 ? "match" : "matches";
  return `${String(tasks.length)} ${noun} for “${query.trim()}”. Reordering is off while you search.`;
};

/** Turn a drop of `activeId` onto `overId`'s place into the move the API expects, or null for no change. */
export const moveFor = (ids: readonly string[], activeId: string, overId: string): Move | null => {
  const from = ids.indexOf(activeId);
  const to = ids.indexOf(overId);
  if (from === -1 || to === -1 || from === to) return null;
  const reordered = ids.toSpliced(from, 1).toSpliced(to, 0, activeId);
  return { taskId: activeId, afterId: reordered[to - 1] ?? null };
};

/** The detail route for one task. */
export const taskPath = (taskId: string): string => `/tasks/${taskId}`;
