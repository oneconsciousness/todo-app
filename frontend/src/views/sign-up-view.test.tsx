import { render, screen, within } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import { SignUpView, type SignUpViewProps } from "./sign-up-view.tsx";

const renderView = (overrides: Partial<SignUpViewProps> = {}) => {
  render(<SignUpView submitting={false} failure={null} onSubmit={vi.fn()} {...overrides} />);
};

describe("SignUpView", () => {
  it("asks for a new password of at least 12 characters", () => {
    renderView();
    expect(screen.getByRole("heading", { name: "Create an account" })).toBeInTheDocument();
    expect(screen.getByLabelText("Password")).toHaveAttribute("autocomplete", "new-password");
    expect(screen.getByLabelText("Password")).toHaveAccessibleDescription(
      "At least 12 characters.",
    );
  });

  it("offers sign-in when the email is already registered (409)", () => {
    renderView({ failure: "email-taken" });
    const alert = screen.getByRole("alert");
    expect(alert).toHaveTextContent("An account with this email already exists.");
    expect(within(alert).getByRole("link", { name: "Sign in instead" })).toHaveAttribute(
      "href",
      "/sign-in",
    );
  });
});
