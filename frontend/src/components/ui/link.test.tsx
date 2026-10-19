import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import { Link, NavigationProvider } from "./link.tsx";

describe("Link", () => {
  it("hands a plain click to the app's navigate", () => {
    const navigate = vi.fn();
    render(
      <NavigationProvider navigate={navigate}>
        <Link href="/tasks/1">Renew passport</Link>
      </NavigationProvider>,
    );
    const notPrevented = fireEvent.click(screen.getByRole("link", { name: "Renew passport" }));
    expect(navigate).toHaveBeenCalledWith("/tasks/1");
    expect(notPrevented).toBe(false);
  });

  it("leaves a modified click to the browser, so it can open a new tab", () => {
    const navigate = vi.fn();
    render(
      <NavigationProvider navigate={navigate}>
        <Link href="/tasks/1">Renew passport</Link>
      </NavigationProvider>,
    );
    fireEvent.click(screen.getByRole("link"), { metaKey: true });
    expect(navigate).not.toHaveBeenCalled();
  });

  it("behaves as a normal link outside a navigation provider", () => {
    render(<Link href="/tasks/1">Renew passport</Link>);
    expect(fireEvent.click(screen.getByRole("link"))).toBe(true);
  });
});
