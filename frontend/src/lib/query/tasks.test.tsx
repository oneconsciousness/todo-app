import { renderHook, waitFor } from "@testing-library/react";
import { HttpResponse, delay, http } from "msw";
import { describe, expect, it, vi } from "vitest";
import { searchMatches, tasks } from "../../test/fixtures.ts";
import { queryWrapper } from "../../test/query-wrapper.tsx";
import { server } from "../../test/server.ts";
import { useTasks } from "./tasks.ts";

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
