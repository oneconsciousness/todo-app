import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";
import { AppShell } from "./app-shell.tsx";

describe("AppShell", () => {
  it("names who is signed in and signs them out", async () => {
    const onSignOut = vi.fn();
    render(
      <AppShell account={{ email: "maya@example.com", signingOut: false, onSignOut }}>
        <p>Page</p>
      </AppShell>,
    );
    expect(screen.getByText("maya@example.com")).toBeInTheDocument();
    await userEvent.click(screen.getByRole("button", { name: "Sign out" }));
    expect(onSignOut).toHaveBeenCalledOnce();
  });

  it("holds the sign-out button while signing out", () => {
    render(
      <AppShell account={{ email: "maya@example.com", signingOut: true, onSignOut: vi.fn() }}>
        <p>Page</p>
      </AppShell>,
    );
    expect(screen.getByRole("button", { name: "Sign out" })).toBeDisabled();
  });

  it("links the ledger title to the task list and renders the page", () => {
    render(
      <AppShell account={null}>
        <p>Page</p>
      </AppShell>,
    );
    expect(screen.getByRole("link", { name: "To Do" })).toHaveAttribute("href", "/tasks");
    expect(screen.getByRole("main")).toHaveTextContent("Page");
    expect(screen.queryByRole("button", { name: "Sign out" })).not.toBeInTheDocument();
  });
});
