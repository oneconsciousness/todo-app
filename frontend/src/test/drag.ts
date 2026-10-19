import { act, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { vi } from "vitest";

const rowHeight = 48;

// jsdom has no layout, so each list item gets a stacked box the keyboard sensor can measure.
const stackedRect = function (this: HTMLElement): DOMRect {
  const row = this.closest("li");
  const index = row?.parentElement ? [...row.parentElement.children].indexOf(row) : 0;
  return new DOMRect(0, index * rowHeight, 320, rowHeight);
};

/** Give list rows a layout, so dnd-kit's keyboard sensor can move between them. */
export const stackRows = (): void => {
  vi.spyOn(HTMLElement.prototype, "getBoundingClientRect").mockImplementation(stackedRect);
};

const pressAndSettle = async (key: string): Promise<void> => {
  await userEvent.keyboard(key);
  await act(() => new Promise((resolve) => setTimeout(resolve, 0)));
};

/**
 * Move the task called `title` with the keyboard, as a user would: Space, an arrow, Space. jsdom has no layout, so
 * dnd-kit keeps the row positions it measured first; after a reorder, read where a task landed from the screen.
 */
export const moveOnePlace = async (title: string, direction: "up" | "down"): Promise<void> => {
  screen.getByRole("button", { name: `Move ${title}` }).focus();
  await pressAndSettle(" ");
  await pressAndSettle(direction === "up" ? "{ArrowUp}" : "{ArrowDown}");
  await pressAndSettle(" ");
};
