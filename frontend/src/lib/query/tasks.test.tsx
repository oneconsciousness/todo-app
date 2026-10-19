import type { QueryClient } from "@tanstack/react-query";
import { renderHook, waitFor } from "@testing-library/react";
import { HttpResponse, delay, http } from "msw";
import { describe, expect, it, vi } from "vitest";
import { detailTask, searchMatches, tasks } from "../../test/fixtures.ts";
import { errorReply } from "../../test/handlers.ts";
import { queryWrapper } from "../../test/query-wrapper.tsx";
import { server } from "../../test/server.ts";
import { taskKeys } from "./keys.ts";
import { useDeleteTask, useMoveTask, useTasks, useToggleTask } from "./tasks.ts";

const lateMs = 60;
const abResults = tasks.slice(0, 3);

// The "ab" search is in flight when the user types "abc", and answers only after "abc" has.
const searchWithLateAb = () => {
  const abSent = vi.fn<() => void>();
  const abAborted = vi.fn<() => void>();
  const handler = http.get("/api/v1/tasks", async ({ request }) => {
    if (new URL(request.url).searchParams.get("q") !== "ab")
      return HttpResponse.json({ items: searchMatches });
    request.signal.addEventListener("abort", abAborted);
    abSent();
    await delay(lateMs);
    return HttpResponse.json({ items: abResults });
  });
  return { handler, abSent, abAborted };
};

const renderSearch = async () => {
  const late = searchWithLateAb();
  server.use(late.handler);
  const { wrapper } = queryWrapper();
  const hook = renderHook(({ q }) => useTasks(q), { wrapper, initialProps: { q: "ab" } });
  await waitFor(() => {
    expect(late.abSent).toHaveBeenCalledOnce();
  });
  hook.rerender({ q: "abc" });
  return { ...hook, ...late };
};

describe("useTasks", () => {
  it("keeps abc on screen when the late ab response arrives", async () => {
    const { result } = await renderSearch();

    await waitFor(() => {
      expect(result.current.data).toEqual(searchMatches);
    });
    await delay(lateMs * 2);

    expect(result.current.data).toEqual(searchMatches);
  });

  it("aborts the superseded search request", async () => {
    const { abAborted } = await renderSearch();

    await waitFor(() => {
      expect(abAborted).toHaveBeenCalledOnce();
    });
  });
});

// The task hooks rendered together, over a cache that already holds the full list and one search.
const renderTaskHooks = () => {
  const { client, wrapper } = queryWrapper();
  client.setQueryData(taskKeys.list(""), tasks);
  client.setQueryData(taskKeys.list("budget"), searchMatches);
  const { result } = renderHook(
    () => ({ toggle: useToggleTask(), move: useMoveTask(), remove: useDeleteTask() }),
    { wrapper },
  );
  return { client, hooks: result };
};

type TaskHooks = ReturnType<typeof renderTaskHooks>["hooks"]["current"];

const cachedTaskData = (client: QueryClient) =>
  client
    .getQueryCache()
    .findAll({ queryKey: taskKeys.all })
    .filter((query) => query.state.data !== undefined);

describe("when the session ends during a change", () => {
  it.each([
    {
      change: "toggle",
      reply: http.patch("/api/v1/tasks/:taskId", () => errorReply(401, "not_authenticated")),
      run: (hooks: TaskHooks) =>
        hooks.toggle.mutateAsync({ taskId: detailTask.id, completed: true }),
    },
    {
      change: "move",
      reply: http.put("/api/v1/tasks/:taskId/position", () => errorReply(401, "not_authenticated")),
      run: (hooks: TaskHooks) => hooks.move.mutateAsync({ taskId: detailTask.id, afterId: null }),
    },
    {
      change: "delete",
      reply: http.delete("/api/v1/tasks/:taskId", () => errorReply(401, "not_authenticated")),
      run: (hooks: TaskHooks) => hooks.remove.mutateAsync(detailTask.id),
    },
  ])("leaves no task in the cache after a 401 on a $change", async ({ reply, run }) => {
    server.use(reply);
    const { client, hooks } = renderTaskHooks();

    await run(hooks.current).catch(() => undefined);

    expect(cachedTaskData(client)).toEqual([]);
  });
});
