import { screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { HttpResponse, delay, http } from "msw";
import { describe, expect, it, vi } from "vitest";
import { taskKeys } from "../lib/query/keys.ts";
import { routes } from "../lib/routes.ts";
import { moveOnePlace, stackRows } from "../test/drag.ts";
import { detailTask, makeTask, tasks } from "../test/fixtures.ts";
import { errorReply, orderKeepingServer } from "../test/handlers.ts";
import { renderApp } from "../test/render-app.tsx";
import { server } from "../test/server.ts";

const taskTitles = (): readonly string[] =>
  within(screen.getByRole("list", { name: "Tasks" }))
    .getAllByRole("link")
    .map((link) => link.textContent);

const titleAt = (index: number): string => {
  const task = tasks[index];
  if (!task) throw new Error(`the fixtures have no task at ${String(index)}`);
  return task.title;
};

// Each move answers later than the one sent after it, so only a queue keeps them in order.
const reorderingServer = () => {
  server.use(...orderKeepingServer({ moveDelaysMs: [300, 200, 100], listDelayMs: 150 }).handlers);
};

const tickBox = (title: string) => screen.getByRole("checkbox", { name: `Completed: ${title}` });

const renderList = async () => {
  const app = renderApp(routes.tasks);
  await screen.findByRole("list", { name: "Tasks" });
  return app;
};

describe("TaskListPage", () => {
  it("shows the server's tasks after loading", async () => {
    renderApp(routes.tasks);

    expect(await screen.findByRole("list", { name: "Tasks" })).toBeVisible();
    expect(taskTitles()).toEqual(tasks.map((task) => task.title));
  });

  it("disables reorder while a search is typed", async () => {
    await renderList();
    expect(screen.getAllByRole("button", { name: /^Move / })).toHaveLength(tasks.length);

    await userEvent.type(screen.getByRole("searchbox", { name: "Search tasks" }), "budget");

    expect(screen.queryAllByRole("button", { name: /^Move / })).toHaveLength(0);
  });

  it("three quick moves end in the order the user made", async () => {
    stackRows();
    reorderingServer();
    const app = await renderList();
    const refetchLists = () => {
      void app.client.refetchQueries({ queryKey: taskKeys.lists() });
    };

    // The moves overlap, so the server ends in the user's order only if it applies them in the order they were made.
    await moveOnePlace(titleAt(0), "down");
    refetchLists();
    await moveOnePlace(titleAt(2), "up");
    refetchLists();
    await moveOnePlace(titleAt(3), "up");
    const madeByUser = taskTitles();

    await waitFor(
      () => {
        expect(app.client.isMutating() + app.client.isFetching()).toBe(0);
      },
      { timeout: 3000 },
    );
    expect(madeByUser).not.toEqual(tasks.map((task) => task.title));
    expect(taskTitles()).toEqual(madeByUser);
  });

  it("rolls back an optimistic toggle and says what failed", async () => {
    vi.spyOn(console, "error").mockImplementation(() => undefined);
    await renderList();
    // The refetch after the failure answers late, so what the test sees is the rollback, not fresh data.
    server.use(
      http.patch("/api/v1/tasks/:taskId", async () => {
        await delay(30);
        return errorReply(500, "internal_error");
      }),
      http.get("/api/v1/tasks", async () => {
        await delay(500);
        return HttpResponse.json({ items: tasks });
      }),
    );

    await userEvent.click(tickBox(detailTask.title));
    expect(tickBox(detailTask.title)).toBeChecked();

    expect(await screen.findByRole("alert")).toHaveTextContent("Couldn't update the task");
    expect(tickBox(detailTask.title)).not.toBeChecked();
  });

  it("keeps a dismissed notice gone after opening a task and coming back", async () => {
    vi.spyOn(console, "error").mockImplementation(() => undefined);
    server.use(http.patch("/api/v1/tasks/:taskId", () => errorReply(500, "internal_error")));
    await renderList();
    await userEvent.click(tickBox(detailTask.title));
    await userEvent.click(
      within(await screen.findByRole("alert")).getByRole("button", { name: "Dismiss" }),
    );

    await userEvent.click(screen.getByRole("link", { name: detailTask.title }));
    await userEvent.click(await screen.findByRole("link", { name: "All tasks" }));

    expect(await screen.findByRole("list", { name: "Tasks" })).toBeVisible();
    expect(screen.queryByRole("alert")).not.toBeInTheDocument();
  });

  it("removes the row and says why when a toggle gets 404", async () => {
    vi.spyOn(console, "error").mockImplementation(() => undefined);
    await renderList();
    server.use(
      http.patch("/api/v1/tasks/:taskId", () => errorReply(404, "not_found")),
      http.get("/api/v1/tasks", () =>
        HttpResponse.json({ items: tasks.filter((task) => task.id !== detailTask.id) }),
      ),
    );

    await userEvent.click(tickBox(detailTask.title));

    expect(await screen.findByRole("alert")).toHaveTextContent("That task was deleted elsewhere.");
    expect(screen.queryByRole("link", { name: detailTask.title })).not.toBeInTheDocument();
  });

  it("keeps quick add saving until the server answers", async () => {
    const created = makeTask({ id: "00000000-0000-4000-8000-0000000000c1", title: "Buy stamps" });
    const state = { saved: false };
    await renderList();
    server.use(
      http.post("/api/v1/tasks", async () => {
        await delay(100);
        state.saved = true;
        return HttpResponse.json(created, { status: 201 });
      }),
      http.get("/api/v1/tasks", () =>
        HttpResponse.json({ items: state.saved ? [created, ...tasks] : tasks }),
      ),
    );

    await userEvent.type(screen.getByRole("textbox", { name: "New task" }), "Buy stamps{Enter}");

    expect(screen.getByText("Adding…")).toBeVisible();
    expect(screen.getByRole("button", { name: "Add task" })).toBeDisabled();
    expect(await screen.findByRole("link", { name: "Buy stamps" })).toBeVisible();
    expect(screen.queryByText("Adding…")).not.toBeInTheDocument();
  });

  it("says why quick add failed", async () => {
    vi.spyOn(console, "error").mockImplementation(() => undefined);
    await renderList();
    server.use(http.post("/api/v1/tasks", () => errorReply(500, "internal_error")));

    await userEvent.type(screen.getByRole("textbox", { name: "New task" }), "Buy stamps{Enter}");

    expect(await screen.findByRole("alert")).toHaveTextContent("Couldn't add the task.");
    expect(screen.getByRole("button", { name: "Add task" })).toBeEnabled();
  });
});
