import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";
import { CredentialsForm, type CredentialsFormProps } from "./credentials-form.tsx";

const renderForm = (overrides: Partial<CredentialsFormProps> = {}) => {
  const props: CredentialsFormProps = {
    submitLabel: "Sign in",
    submittingLabel: "Signing in…",
    passwordAutoComplete: "current-password",
    submitting: false,
    failure: null,
    onSubmit: vi.fn(),
    ...overrides,
  };
  render(<CredentialsForm {...props} />);
  return props;
};

describe("CredentialsForm", () => {
  it("submits the trimmed email and the password as typed", async () => {
    const { onSubmit } = renderForm();
    await userEvent.type(screen.getByRole("textbox", { name: "Email" }), " maya@example.com ");
    await userEvent.type(screen.getByLabelText("Password"), "correct horse battery");
    await userEvent.click(screen.getByRole("button", { name: "Sign in" }));
    expect(onSubmit).toHaveBeenCalledWith({
      email: "maya@example.com",
      password: "correct horse battery",
    });
  });

  it("shows each field's problem next to it instead of submitting", async () => {
    const { onSubmit } = renderForm();
    await userEvent.type(screen.getByRole("textbox", { name: "Email" }), "maya@");
    await userEvent.type(screen.getByLabelText("Password"), "short");
    await userEvent.click(screen.getByRole("button", { name: "Sign in" }));
    expect(onSubmit).not.toHaveBeenCalled();
    expect(screen.getByRole("textbox", { name: "Email" })).toHaveAccessibleDescription(
      "Enter an email address like name@example.com.",
    );
    expect(screen.getByLabelText("Password")).toHaveAccessibleDescription(
      "Use at least 12 characters.",
    );
  });

  it("clears a field's problem once the user edits it", async () => {
    renderForm();
    await userEvent.click(screen.getByRole("button", { name: "Sign in" }));
    const email = screen.getByRole("textbox", { name: "Email" });
    expect(email).toHaveAccessibleDescription("Enter an email address like name@example.com.");
    await userEvent.type(email, "m");
    expect(email).toHaveAccessibleDescription("");
  });

  it("shows the server's problem with a field next to it until the user edits that field", async () => {
    renderForm({ fieldErrors: { email: "That domain can't receive email." } });
    const email = screen.getByRole("textbox", { name: "Email" });
    expect(email).toHaveAccessibleDescription("That domain can't receive email.");
    await userEvent.type(email, "m");
    expect(email).toHaveAccessibleDescription("");
  });

  it("holds the form while it is submitting", () => {
    renderForm({ submitting: true });
    expect(screen.getByRole("button", { name: "Signing in…" })).toBeDisabled();
    expect(screen.getByRole("textbox", { name: "Email" })).toBeDisabled();
  });

  it("starts from a given email", () => {
    renderForm({ initialEmail: "maya@example.com" });
    expect(screen.getByRole("textbox", { name: "Email" })).toHaveValue("maya@example.com");
  });
});
