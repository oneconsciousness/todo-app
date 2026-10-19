import { describe, expect, it } from "vitest";
import { routes } from "./routes.ts";

describe("routes", () => {
  it("builds the detail route for a task", () => {
    expect(routes.task("3f0c6f7e-8a51-4f7a-9d64-2f0b9c1e5a10")).toBe(
      "/tasks/3f0c6f7e-8a51-4f7a-9d64-2f0b9c1e5a10",
    );
  });

  it("names the fixed screens of spec's Screens table", () => {
    expect([routes.signIn, routes.signUp, routes.tasks]).toEqual([
      "/sign-in",
      "/sign-up",
      "/tasks",
    ]);
  });
});
