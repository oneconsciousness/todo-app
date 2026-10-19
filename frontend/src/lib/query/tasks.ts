import { keepPreviousData, useQuery } from "@tanstack/react-query";
import { listTasks } from "../api/tasks.ts";
import { taskKeys } from "./keys.ts";

/**
 * The user's tasks, or the matches for `q`. Each term is cached on its own, so a late answer for an older term never
 * replaces a newer one; the previous results stay on screen while the next load; and a superseded request is
 * aborted ([query cancellation](https://tanstack.com/query/v5/docs/framework/react/guides/query-cancellation)).
 */
export const useTasks = (q: string) =>
  useQuery({
    queryKey: taskKeys.list(q),
    queryFn: ({ signal }) => listTasks(q, signal),
    placeholderData: keepPreviousData,
  });
