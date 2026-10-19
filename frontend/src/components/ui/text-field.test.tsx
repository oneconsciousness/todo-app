import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { TextField } from "./text-field.tsx";

describe("TextField", () => {
  it("is named by its label, even when the label is visually hidden", () => {
    render(<TextField label="New task" hideLabel />);
    expect(screen.getByRole("textbox", { name: "New task" })).toBeInTheDocument();
  });

  it("marks the field invalid and describes it with the error", () => {
    render(<TextField label="Title" error="Add a title." />);
    const field = screen.getByRole("textbox", { name: "Title" });
    expect(field).toBeInvalid();
    expect(field).toHaveAccessibleDescription("Add a title.");
  });

  it("describes the field with its hint, and with the error once there is one", () => {
    const { rerender } = render(<TextField label="Password" hint="At least 12 characters." />);
    expect(screen.getByRole("textbox", { name: "Password" })).toHaveAccessibleDescription(
      "At least 12 characters.",
    );
    rerender(
      <TextField
        label="Password"
        hint="At least 12 characters."
        error="Use at least 12 characters."
      />,
    );
    expect(screen.getByRole("textbox", { name: "Password" })).toHaveAccessibleDescription(
      "At least 12 characters. Use at least 12 characters.",
    );
  });

  it("is valid without an error", () => {
    render(<TextField label="Title" />);
    expect(screen.getByRole("textbox", { name: "Title" })).toBeValid();
  });
});
