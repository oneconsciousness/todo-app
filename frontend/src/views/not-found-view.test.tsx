import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { NotFoundView } from "./not-found-view.tsx";

describe("NotFoundView", () => {
  it("explains a missing page and leads back to the tasks", () => {
    render(<NotFoundView subject="page" />);
    expect(screen.getByRole("heading", { name: "This page isn't in the ledger" })).toBeVisible();
    expect(screen.getByRole("link", { name: "Go to your tasks" })).toHaveAttribute(
      "href",
      "/tasks",
    );
  });

  it("explains a task that is gone or belongs to someone else, without saying which", () => {
    render(<NotFoundView subject="task" />);
    expect(screen.getByRole("heading", { name: "This task isn't in your ledger" })).toBeVisible();
    expect(screen.getByText("It may have been deleted, or the link may be wrong.")).toBeVisible();
  });
});
