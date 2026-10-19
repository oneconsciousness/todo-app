import { act, render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { SortableList } from "./sortable-list.tsx";

const items = [
  { id: "a", name: "Alpha" },
  { id: "b", name: "Bravo" },
  { id: "c", name: "Charlie" },
] as const;

const rowHeight = 48;

// jsdom has no layout, so give each list item a stacked box the keyboard sensor can measure.
const stackedRect = function (this: HTMLElement): DOMRect {
  const row = this.closest("li");
  const index = row?.parentElement ? [...row.parentElement.children].indexOf(row) : 0;
  return new DOMRect(0, index * rowHeight, 320, rowHeight);
};

const renderList = (onMove = vi.fn(), disabled = false) => {
  render(
    <SortableList
      items={items}
      label="Tasks"
      itemLabel={(item) => item.name}
      disabled={disabled}
      onMove={onMove}
    >
      {(item, handle) => (
        <>
          {handle}
          <span>{item.name}</span>
        </>
      )}
    </SortableList>,
  );
  return onMove;
};

const pressAndSettle = async (key: string) => {
  await userEvent.keyboard(key);
  await act(() => new Promise((resolve) => setTimeout(resolve, 0)));
};

describe("SortableList", () => {
  beforeEach(() => {
    vi.spyOn(HTMLElement.prototype, "getBoundingClientRect").mockImplementation(stackedRect);
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  it("renders a named drag handle for each item", () => {
    renderList();
    expect(screen.getByRole("list", { name: "Tasks" })).toBeInTheDocument();
    expect(screen.getAllByRole("button", { name: /^Move / })).toHaveLength(3);
  });

  it("moves an item down with the keyboard and reports where it landed", async () => {
    const onMove = renderList();
    screen.getByRole("button", { name: "Move Alpha" }).focus();
    await pressAndSettle(" ");
    await pressAndSettle("{ArrowDown}");
    await pressAndSettle(" ");
    expect(onMove).toHaveBeenCalledWith("a", "b");
  });

  it("reports a move to the top with no task before it", async () => {
    const onMove = renderList();
    screen.getByRole("button", { name: "Move Bravo" }).focus();
    await pressAndSettle(" ");
    await pressAndSettle("{ArrowUp}");
    await pressAndSettle(" ");
    expect(onMove).toHaveBeenCalledWith("b", null);
  });

  it("drops nothing when the move is cancelled", async () => {
    const onMove = renderList();
    screen.getByRole("button", { name: "Move Alpha" }).focus();
    await pressAndSettle(" ");
    await pressAndSettle("{ArrowDown}");
    await pressAndSettle("{Escape}");
    expect(onMove).not.toHaveBeenCalled();
  });

  it("hides the handles while reordering is off", () => {
    renderList(vi.fn(), true);
    expect(screen.queryByRole("button", { name: /^Move / })).not.toBeInTheDocument();
    expect(screen.getAllByRole("listitem")).toHaveLength(3);
  });
});
