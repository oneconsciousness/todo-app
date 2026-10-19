import { describe, expect, it } from "vitest";
import { makeTask } from "../../test/fixtures.ts";
import { moveAfter } from "./order.ts";

const first = makeTask({ id: "00000000-0000-4000-8000-000000000001", title: "Task 1" });
const second = makeTask({ id: "00000000-0000-4000-8000-000000000002", title: "Task 2" });
const third = makeTask({ id: "00000000-0000-4000-8000-000000000003", title: "Task 3" });

const titles = (items: readonly { readonly title: string }[]) => items.map((task) => task.title);

describe("moveAfter", () => {
  it("moves a task after another without mutating the input", () => {
    const items = Object.freeze([first, second, third]);

    const moved = moveAfter(items, first.id, third.id);

    expect(titles(moved)).toEqual(["Task 2", "Task 3", "Task 1"]);
    expect(titles(items)).toEqual(["Task 1", "Task 2", "Task 3"]);
  });

  it("moves a task to the top", () => {
    expect(titles(moveAfter([first, second, third], third.id, null))).toEqual([
      "Task 3",
      "Task 1",
      "Task 2",
    ]);
  });
});
