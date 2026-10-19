import type { Task } from "../schema/task.ts";

/**
 * A new list with task `id` placed right after `afterId`, or at the top when it is null. The list comes back unchanged
 * when either task is missing from it, as in a search that doesn't include both.
 */
export const moveAfter = (
  items: readonly Task[],
  id: string,
  afterId: string | null,
): readonly Task[] => {
  const from = items.findIndex((task) => task.id === id);
  const task = items[from];
  if (task === undefined) return items;
  const rest = items.toSpliced(from, 1);
  const to = afterId === null ? 0 : rest.findIndex((other) => other.id === afterId) + 1;
  if (afterId !== null && to === 0) return items;
  return rest.toSpliced(to, 0, task);
};
