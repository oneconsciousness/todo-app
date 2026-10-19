import { describe, expect, it } from "vitest";
import { makeTask } from "../test/fixtures.ts";
import { moveFor, summarize, taskPath } from "./task-list.ts";

describe("summarize", () => {
  it("counts open and completed tasks", () => {
    const tasks = [
      makeTask({ completed: false }),
      makeTask({ completed: true }),
      makeTask({ completed: false }),
    ];
    expect(summarize(tasks)).toEqual({ open: 2, done: 1 });
  });

  it("counts nothing in an empty list", () => {
    expect(summarize([])).toEqual({ open: 0, done: 0 });
  });
});

describe("moveFor", () => {
  const ids = ["a", "b", "c", "d"];

  it("places a task moved down after the task it was dropped on", () => {
    expect(moveFor(ids, "a", "c")).toEqual({ taskId: "a", afterId: "c" });
  });

  it("places a task moved up after the task above its new spot", () => {
    expect(moveFor(ids, "d", "b")).toEqual({ taskId: "d", afterId: "a" });
  });

  it("sends null when a task moves to the top", () => {
    expect(moveFor(ids, "c", "a")).toEqual({ taskId: "c", afterId: null });
  });

  it("ignores a drop on the task's own place", () => {
    expect(moveFor(ids, "b", "b")).toBeNull();
  });

  it("ignores ids that are not in the list", () => {
    expect(moveFor(ids, "a", "z")).toBeNull();
  });
});

describe("taskPath", () => {
  it("builds the detail route for a task", () => {
    expect(taskPath("3f0c6f7e-8a51-4f7a-9d64-2f0b9c1e5a10")).toBe(
      "/tasks/3f0c6f7e-8a51-4f7a-9d64-2f0b9c1e5a10",
    );
  });
});
