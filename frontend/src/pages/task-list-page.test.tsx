import { screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { HttpResponse, delay, http } from "msw";
import { describe, expect, it, vi } from "vitest";
import { routes } from "../lib/routes.ts";
import { detailTask, tasks } from "../test/fixtures.ts";
import { errorReply } from "../test/handlers.ts";
import { renderApp } from "../test/render-app.tsx";
import { server } from "../test/server.ts";

const taskTitles = (): readonly string[] =>
  within(screen.getByRole("list", { name: "Tasks" }))
    .getAllByRole("link")
    .map((link) => link.textContent);

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
});
