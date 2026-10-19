import { screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it } from "vitest";
import { routes } from "../lib/routes.ts";
import { tasks } from "../test/fixtures.ts";
import { renderApp } from "../test/render-app.tsx";

const taskTitles = (): readonly string[] =>
  within(screen.getByRole("list", { name: "Tasks" }))
    .getAllByRole("link")
    .map((link) => link.textContent);

describe("TaskListPage", () => {
  it("shows the server's tasks after loading", async () => {
    renderApp(routes.tasks);

    expect(await screen.findByRole("list", { name: "Tasks" })).toBeVisible();
    expect(taskTitles()).toEqual(tasks.map((task) => task.title));
  });

  it("disables reorder while a search is typed", async () => {
    renderApp(routes.tasks);
    await screen.findByRole("list", { name: "Tasks" });
    expect(screen.getAllByRole("button", { name: /^Move / })).toHaveLength(tasks.length);

    await userEvent.type(screen.getByRole("searchbox", { name: "Search tasks" }), "budget");

    expect(screen.queryAllByRole("button", { name: /^Move / })).toHaveLength(0);
  });
});
