import { render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";
import { detailTask, taskDetailProps } from "../test/fixtures.ts";
import { TaskDetailView, type TaskDetailViewProps } from "./task-detail-view.tsx";

const renderView = (overrides: Partial<TaskDetailViewProps> = {}) => {
  const props = taskDetailProps({
    onSave: vi.fn(),
    onToggle: vi.fn(),
    onDelete: vi.fn(),
    ...overrides,
  });
  const view = render(<TaskDetailView {...props} />);
  const rerender = (next: Partial<TaskDetailViewProps>) => {
    view.rerender(<TaskDetailView {...props} {...next} />);
  };
  return { props, rerender };
};

const titleField = () => screen.getByRole("textbox", { name: "Title" });

const startEditing = async () => {
  await userEvent.click(screen.getByRole("button", { name: "Edit task" }));
};

const retitle = async (title: string) => {
  await userEvent.clear(titleField());
  await userEvent.type(titleField(), title);
};

describe("TaskDetailView", () => {
  it("holds the page while the task loads", () => {
    renderView({ content: { status: "loading" } });
    expect(screen.getByText("Loading the task…")).toBeInTheDocument();
  });

  it("shows not found for a missing task or someone else's", () => {
    renderView({ content: { status: "not-found" } });
    expect(screen.getByRole("heading", { name: "This task isn't in your ledger" })).toBeVisible();
  });

  it("shows every field of the task, with a way back to the list", () => {
    renderView();
    expect(screen.getByRole("heading", { level: 1, name: detailTask.title })).toBeVisible();
    expect(screen.getByText("Due Sat, Oct 24")).toBeVisible();
    expect(screen.getByText(/The form wants the old passport number/)).toBeVisible();
    expect(screen.getByText("Mon, Oct 12")).toBeVisible();
    expect(screen.getByRole("link", { name: "All tasks" })).toHaveAttribute("href", "/tasks");
  });

  it("ticks the task off from the detail screen", async () => {
    const { props } = renderView();
    await userEvent.click(screen.getByRole("checkbox", { name: `Completed: ${detailTask.title}` }));
    expect(props.onToggle).toHaveBeenCalledWith(detailTask.id, true);
  });

  it("saves only the changed fields, with the version the edit started from", async () => {
    const { props } = renderView();
    await startEditing();
    await retitle("Renew both passports");
    await userEvent.clear(screen.getByLabelText("Due date"));
    await userEvent.click(screen.getByRole("button", { name: "Save changes" }));
    expect(props.onSave).toHaveBeenCalledWith(
      detailTask.id,
      { title: "Renew both passports", dueDate: null },
      detailTask.version,
    );
  });

  it("goes back to reading without a request when nothing changed", async () => {
    const { props } = renderView();
    await startEditing();
    await userEvent.click(screen.getByRole("button", { name: "Save changes" }));
    expect(props.onSave).not.toHaveBeenCalled();
    expect(screen.queryByRole("textbox", { name: "Title" })).not.toBeInTheDocument();
  });

  it("shows field problems next to the fields instead of saving", async () => {
    const { props } = renderView();
    await startEditing();
    await userEvent.clear(titleField());
    await userEvent.click(screen.getByRole("button", { name: "Save changes" }));
    expect(props.onSave).not.toHaveBeenCalled();
    expect(titleField()).toHaveAccessibleDescription("Add a title.");
  });

  it("shows the server's problem with a saved field next to it until the user edits that field", async () => {
    const { rerender } = renderView();
    await startEditing();
    await retitle("Renew both passports");
    await userEvent.click(screen.getByRole("button", { name: "Save changes" }));
    rerender({ fieldErrors: { title: "That title is already in use." } });
    expect(titleField()).toHaveAccessibleDescription("That title is already in use.");
    await userEvent.type(titleField(), "!");
    expect(titleField()).toHaveAccessibleDescription("");
  });

  it("holds the form while saving, then reads the saved task", async () => {
    const { rerender } = renderView();
    await startEditing();
    await retitle("Renew both passports");
    await userEvent.click(screen.getByRole("button", { name: "Save changes" }));
    rerender({ saving: true });
    expect(screen.getByRole("button", { name: "Saving…" })).toBeDisabled();
    rerender({
      saving: false,
      content: {
        status: "ready",
        task: { ...detailTask, title: "Renew both passports", version: detailTask.version + 1 },
      },
    });
    expect(screen.getByRole("heading", { level: 1, name: "Renew both passports" })).toBeVisible();
    expect(screen.queryByRole("textbox", { name: "Title" })).not.toBeInTheDocument();
  });

  it("says the task changed elsewhere when a newer version lands under the draft, and can load it", async () => {
    const { rerender } = renderView();
    await startEditing();
    await retitle("My draft title");
    rerender({
      content: {
        status: "ready",
        task: { ...detailTask, dueDate: "2026-10-23", version: detailTask.version + 1 },
      },
    });
    const notice = screen.getByRole("alert");
    expect(notice).toHaveTextContent("Changed elsewhere");
    expect(notice).toHaveTextContent("due date");
    await userEvent.click(within(notice).getByRole("button", { name: "Use the latest" }));
    expect(titleField()).toHaveValue(detailTask.title);
    expect(screen.getByLabelText("Due date")).toHaveValue("2026-10-23");
  });

  it("can keep the draft over a newer version and save against it", async () => {
    const { props, rerender } = renderView();
    await startEditing();
    await retitle("My draft title");
    const newer = { ...detailTask, dueDate: "2026-10-23", version: detailTask.version + 1 };
    rerender({ content: { status: "ready", task: newer } });
    await userEvent.click(screen.getByRole("button", { name: "Keep my edits" }));
    expect(screen.queryByRole("alert")).not.toBeInTheDocument();
    await userEvent.click(screen.getByRole("button", { name: "Save changes" }));
    expect(props.onSave).toHaveBeenCalledWith(
      detailTask.id,
      { title: "My draft title", dueDate: detailTask.dueDate },
      newer.version,
    );
  });

  it("rebases the draft quietly when a newer version changes nothing visible", async () => {
    const { props, rerender } = renderView();
    await startEditing();
    await retitle("My draft title");
    rerender({
      content: { status: "ready", task: { ...detailTask, version: detailTask.version + 1 } },
    });
    expect(screen.queryByRole("alert")).not.toBeInTheDocument();
    await userEvent.click(screen.getByRole("button", { name: "Save changes" }));
    expect(props.onSave).toHaveBeenCalledWith(
      detailTask.id,
      { title: "My draft title" },
      detailTask.version + 1,
    );
  });

  it("deletes only after the confirm step built into the page", async () => {
    const { props } = renderView();
    await userEvent.click(screen.getByRole("button", { name: "Delete" }));
    expect(props.onDelete).not.toHaveBeenCalled();
    await userEvent.click(screen.getByRole("button", { name: "Delete task" }));
    expect(props.onDelete).toHaveBeenCalledWith(detailTask.id);
  });

  it("shows what failed", () => {
    renderView({ failure: "Couldn't save the task. Check your connection and try again." });
    expect(screen.getByRole("alert")).toHaveTextContent("Couldn't save the task.");
  });
});
