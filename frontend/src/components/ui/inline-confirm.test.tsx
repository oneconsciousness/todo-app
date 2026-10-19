import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";
import { InlineConfirm, type InlineConfirmProps } from "./inline-confirm.tsx";

const renderConfirm = (overrides: Partial<InlineConfirmProps> = {}) => {
  const props: InlineConfirmProps = {
    message: "Delete this task? This can't be undone.",
    confirmLabel: "Delete task",
    busyLabel: "Deleting…",
    cancelLabel: "Keep it",
    busy: false,
    onConfirm: vi.fn(),
    onCancel: vi.fn(),
    ...overrides,
  };
  render(<InlineConfirm {...props} />);
  return props;
};

describe("InlineConfirm", () => {
  it("asks its question and puts focus on the safe choice", () => {
    renderConfirm();
    expect(
      screen.getByRole("group", { name: "Delete this task? This can't be undone." }),
    ).toBeVisible();
    expect(screen.getByRole("button", { name: "Keep it" })).toHaveFocus();
  });

  it("confirms or backs out", async () => {
    const { onConfirm, onCancel } = renderConfirm();
    await userEvent.click(screen.getByRole("button", { name: "Delete task" }));
    await userEvent.click(screen.getByRole("button", { name: "Keep it" }));
    expect(onConfirm).toHaveBeenCalledOnce();
    expect(onCancel).toHaveBeenCalledOnce();
  });

  it("holds both choices while the action runs", () => {
    renderConfirm({ busy: true });
    expect(screen.getByRole("button", { name: "Deleting…" })).toBeDisabled();
    expect(screen.getByRole("button", { name: "Keep it" })).toBeDisabled();
  });
});
