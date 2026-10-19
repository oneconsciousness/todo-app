import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";
import { Checkbox } from "./checkbox.tsx";

describe("Checkbox", () => {
  it("reports the new state when clicked", async () => {
    const onChange = vi.fn();
    render(<Checkbox label="Completed: Renew passport" checked={false} onChange={onChange} />);
    await userEvent.click(screen.getByRole("checkbox", { name: "Completed: Renew passport" }));
    expect(onChange).toHaveBeenCalledWith(true);
  });

  it("toggles from the keyboard", async () => {
    const onChange = vi.fn();
    render(<Checkbox label="Completed: Renew passport" checked onChange={onChange} />);
    await userEvent.tab();
    await userEvent.keyboard(" ");
    expect(onChange).toHaveBeenCalledWith(false);
  });
});
