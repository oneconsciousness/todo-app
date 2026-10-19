import { render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";
import { searchMatches, searchTerm, tasks, today, unmatchedTerm } from "../test/fixtures.ts";
import { TaskListView, type TaskListViewProps } from "./task-list-view.tsx";

const renderView = (overrides: Partial<TaskListViewProps> = {}) => {
  const props: TaskListViewProps = {
    content: { status: "ready", tasks },
    today,
    query: "",
    searchPending: false,
    pendingCreate: null,
    failure: null,
    onQueryChange: vi.fn(),
    onCreate: vi.fn(),
    onToggle: vi.fn(),
    onMove: vi.fn(),
    onRetry: vi.fn(),
    onDismissFailure: vi.fn(),
    ...overrides,
  };
  render(<TaskListView {...props} />);
  return props;
};

const [firstTask] = tasks;

describe("TaskListView", () => {
  it("shows placeholder rows while the tasks load", () => {
    renderView({ content: { status: "loading" } });
    expect(screen.getByText("Loading your tasks…")).toBeInTheDocument();
    expect(screen.queryByRole("link")).not.toBeInTheDocument();
  });

  it("invites the first task when the list is empty", () => {
    renderView({ content: { status: "ready", tasks: [] } });
    expect(screen.getByRole("heading", { name: "No tasks yet" })).toBeInTheDocument();
  });

  it("explains a failed load and offers to try again", async () => {
    const { onRetry } = renderView({
      content: { status: "error", message: "The server did not answer." },
    });
    const alert = screen.getByRole("alert");
    expect(alert).toHaveTextContent("Couldn't load your tasks");
    expect(alert).toHaveTextContent("The server did not answer.");
    await userEvent.click(within(alert).getByRole("button", { name: "Try again" }));
    expect(onRetry).toHaveBeenCalledOnce();
  });

  it("lists every task as a link to its detail screen, with its due date", () => {
    renderView();
    const list = screen.getByRole("list", { name: "Tasks" });
    expect(within(list).getAllByRole("listitem")).toHaveLength(tasks.length);
    expect(screen.getByRole("link", { name: "Send Maya the Q3 budget notes" })).toHaveAttribute(
      "href",
      "/tasks/00000000-0000-4000-8000-000000000002",
    );
    expect(screen.getByText("Overdue · Fri, Oct 16")).toBeInTheDocument();
    expect(screen.getByText("6 open · 2 done")).toBeInTheDocument();
  });

  it("shows completed tasks as ticked", () => {
    renderView();
    expect(
      screen.getByRole("checkbox", { name: "Completed: Return the library books" }),
    ).toBeChecked();
  });

  it("reports a toggle with the task id and its new state", async () => {
    const { onToggle } = renderView();
    await userEvent.click(
      screen.getByRole("checkbox", {
        name: "Completed: Call the landlord about the boiler service",
      }),
    );
    expect(onToggle).toHaveBeenCalledWith(firstTask?.id, true);
  });

  it("offers a drag handle on every task when not searching", () => {
    renderView();
    expect(screen.getAllByRole("button", { name: /^Move / })).toHaveLength(tasks.length);
  });

  it("creates a task from the trimmed title and clears the field", async () => {
    const { onCreate } = renderView();
    const field = screen.getByRole("textbox", { name: "New task" });
    await userEvent.type(field, "  Buy stamps  ");
    await userEvent.click(screen.getByRole("button", { name: "Add task" }));
    expect(onCreate).toHaveBeenCalledWith("Buy stamps");
    expect(field).toHaveValue("");
  });

  it("asks for a title instead of creating an empty task", async () => {
    const { onCreate } = renderView();
    await userEvent.click(screen.getByRole("button", { name: "Add task" }));
    expect(onCreate).not.toHaveBeenCalled();
    expect(screen.getByRole("textbox", { name: "New task" })).toHaveAccessibleDescription(
      "Add a title.",
    );
  });

  it("shows a task being created at the top and holds the add button", () => {
    renderView({ pendingCreate: "Buy stamps" });
    expect(screen.getByText("Buy stamps")).toBeInTheDocument();
    expect(screen.getByText("Adding…")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Add task" })).toBeDisabled();
  });

  it("shows matches and turns reordering off while searching", () => {
    renderView({ query: searchTerm, content: { status: "ready", tasks: searchMatches } });
    expect(
      screen.getByText("2 matches for “budget”. Reordering is off while you search."),
    ).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: /^Move / })).not.toBeInTheDocument();
  });

  it("says when a search matches nothing and offers the whole list back", async () => {
    const { onQueryChange } = renderView({
      query: unmatchedTerm,
      content: { status: "ready", tasks: [] },
    });
    expect(screen.getByRole("heading", { name: "No tasks match “plumber”" })).toBeInTheDocument();
    await userEvent.click(screen.getByRole("button", { name: "Show all tasks" }));
    expect(onQueryChange).toHaveBeenCalledWith("");
  });

  it("shows what failed after an action is rolled back", async () => {
    const onRetry = vi.fn();
    const { onDismissFailure } = renderView({
      failure: { message: "Couldn't move “Book a dentist check-up”.", onRetry },
    });
    const alert = screen.getByRole("alert");
    expect(alert).toHaveTextContent("Couldn't move “Book a dentist check-up”.");
    await userEvent.click(within(alert).getByRole("button", { name: "Try again" }));
    await userEvent.click(within(alert).getByRole("button", { name: "Dismiss" }));
    expect(onRetry).toHaveBeenCalledOnce();
    expect(onDismissFailure).toHaveBeenCalledOnce();
  });
});
