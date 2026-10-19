import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";
import { ErrorView } from "./error-view.tsx";

describe("ErrorView", () => {
  it("says what went wrong and offers to try again or go to the tasks", async () => {
    const onRetry = vi.fn();
    const onGoToTasks = vi.fn();
    render(
      <ErrorView
        message="The page stopped with an error."
        onRetry={onRetry}
        onGoToTasks={onGoToTasks}
      />,
    );
    expect(screen.getByRole("heading", { name: "Something went wrong" })).toBeVisible();
    expect(screen.getByText("The page stopped with an error.")).toBeVisible();
    await userEvent.click(screen.getByRole("button", { name: "Try again" }));
    await userEvent.click(screen.getByRole("button", { name: "Go to tasks" }));
    expect(onRetry).toHaveBeenCalledOnce();
    expect(onGoToTasks).toHaveBeenCalledOnce();
  });
});
