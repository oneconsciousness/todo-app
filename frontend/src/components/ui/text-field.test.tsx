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

  it("is valid without an error", () => {
    render(<TextField label="Title" />);
    expect(screen.getByRole("textbox", { name: "Title" })).toBeValid();
  });
});
