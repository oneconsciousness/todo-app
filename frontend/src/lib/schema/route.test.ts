import { describe, expect, it } from "vitest";
import { routes } from "../routes.ts";
import { returnToSchema } from "./route.ts";

// What `searchParams.get("returnTo")` hands the schema for a query string, encoding undone.
const fromQuery = (encoded: string): string | null =>
  new URLSearchParams(`returnTo=${encoded}`).get("returnTo");

describe("returnToSchema", () => {
  it.each([
    ["another host", "//evil.example/steal"],
    ["a backslash host", "/\\evil.example"],
    ["a tab before the host", "/\t/evil.example"],
    ["a newline before the host", "/\n/evil.example"],
    ["a carriage return before the host", "/\r/evil.example"],
    ["an encoded tab", fromQuery("%2F%09%2Fevil.example")],
    ["an encoded newline", fromQuery("%2F%0A%2Fevil.example")],
    ["an encoded double slash", fromQuery("%2F%2Fevil.example")],
    ["an absolute URL", "https://evil.example/tasks"],
    ["a script URL", "javascript:alert(1)"],
    ["a URL that cannot be parsed", "https://["],
    ["nothing", null],
  ])("sends %s to the task list", (_case, returnTo) => {
    expect(returnToSchema.parse(returnTo)).toBe(routes.tasks);
  });

  it("keeps a path inside the app, with its query and fragment", () => {
    expect(returnToSchema.parse("/tasks/abc?q=boiler#notes")).toBe("/tasks/abc?q=boiler#notes");
  });
});
