import { render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import { SignInView, type SignInViewProps } from "./sign-in-view.tsx";

const renderView = (overrides: Partial<SignInViewProps> = {}) => {
  render(<SignInView submitting={false} failure={null} onSubmit={vi.fn()} {...overrides} />);
};

describe("SignInView", () => {
  it("is the landing page: a sign-in form and a way to create an account", () => {
    renderView();
    expect(screen.getByRole("heading", { name: "Sign in" })).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Create an account" })).toHaveAttribute(
      "href",
      "/sign-up",
    );
  });

  it("says the email and password don't match after a 401", () => {
    renderView({ failure: "wrong-credentials" });
    expect(screen.getByRole("alert")).toHaveTextContent(
      "That email and password don't match an account.",
    );
  });

  it("says the server couldn't be reached", () => {
    renderView({ failure: "unreachable" });
    expect(screen.getByRole("alert")).toHaveTextContent("Couldn't reach the server.");
  });
});
