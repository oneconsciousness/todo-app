import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";
import { Notice } from "./notice.tsx";

describe("Notice", () => {
  it("announces an alert with its message", () => {
    render(<Notice>Couldn't move the task.</Notice>);
    expect(screen.getByRole("alert")).toHaveTextContent("Couldn't move the task.");
  });

  it("runs each of its actions", async () => {
    const useLatest = vi.fn();
    const keepEdits = vi.fn();
    render(
      <Notice
        actions={[
          { label: "Use the latest", onAction: useLatest },
          { label: "Keep my edits", onAction: keepEdits },
        ]}
      >
        Changed elsewhere.
      </Notice>,
    );
    await userEvent.click(screen.getByRole("button", { name: "Use the latest" }));
    await userEvent.click(screen.getByRole("button", { name: "Keep my edits" }));
    expect(useLatest).toHaveBeenCalledOnce();
    expect(keepEdits).toHaveBeenCalledOnce();
  });

  it("can be dismissed", async () => {
    const onDismiss = vi.fn();
    render(<Notice onDismiss={onDismiss}>Couldn't add the task.</Notice>);
    await userEvent.click(screen.getByRole("button", { name: "Dismiss" }));
    expect(onDismiss).toHaveBeenCalledOnce();
  });
});
