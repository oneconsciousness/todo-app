import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";
import { SearchBox } from "./search-box.tsx";

describe("SearchBox", () => {
  it("reports each change to the search text", async () => {
    const onChange = vi.fn();
    render(<SearchBox label="Search tasks" value="" onChange={onChange} />);
    await userEvent.type(screen.getByRole("searchbox", { name: "Search tasks" }), "b");
    expect(onChange).toHaveBeenCalledWith("b");
  });

  it("clears the search and returns focus to the box", async () => {
    const onChange = vi.fn();
    render(<SearchBox label="Search tasks" value="budget" onChange={onChange} />);
    await userEvent.click(screen.getByRole("button", { name: "Clear search" }));
    expect(onChange).toHaveBeenCalledWith("");
    expect(screen.getByRole("searchbox")).toHaveFocus();
  });

  it("offers no clear button when there is nothing to clear", () => {
    render(<SearchBox label="Search tasks" value="" onChange={vi.fn()} />);
    expect(screen.queryByRole("button", { name: "Clear search" })).not.toBeInTheDocument();
  });
});
