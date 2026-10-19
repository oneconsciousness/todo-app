import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";
import { Notice } from "./notice.tsx";

describe("Notice", () => {
  it("announces an alert with its message", () => {
    render(<Notice tone="alert">Couldn't move the task.</Notice>);
    expect(screen.getByRole("alert")).toHaveTextContent("Couldn't move the task.");
  });

  it("runs its action", async () => {
    const onAction = vi.fn();
    render(
      <Notice tone="alert" action={{ label: "Try again", onAction }}>
        Couldn't add the task.
      </Notice>,
    );
    await userEvent.click(screen.getByRole("button", { name: "Try again" }));
    expect(onAction).toHaveBeenCalledOnce();
  });

  it("can be dismissed", async () => {
    const onDismiss = vi.fn();
    render(
      <Notice tone="alert" onDismiss={onDismiss}>
        Couldn't add the task.
      </Notice>,
    );
    await userEvent.click(screen.getByRole("button", { name: "Dismiss" }));
    expect(onDismiss).toHaveBeenCalledOnce();
  });
});
