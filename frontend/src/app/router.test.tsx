import { screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { HttpResponse, delay, http } from "msw";
import { describe, expect, it } from "vitest";
import { routes, signInPath } from "../lib/routes.ts";
import { user } from "../test/fixtures.ts";
import { errorReply } from "../test/handlers.ts";
import { renderApp } from "../test/render-app.tsx";
import { server } from "../test/server.ts";

describe("app router", () => {
  it("sends a signed-out visitor to sign-in with a return path", async () => {
    server.use(http.get("/api/v1/auth/me", () => errorReply(401, "not_authenticated")));
    const { router } = renderApp("/tasks?q=boiler");

    expect(await screen.findByRole("heading", { name: "Sign in" })).toBeVisible();
    expect(router.state.location.pathname).toBe("/sign-in");
    expect(new URLSearchParams(router.state.location.search).get("returnTo")).toBe(
      "/tasks?q=boiler",
    );
  });

  it("sends a user whose session ended to sign-in, and keeps them there", async () => {
    const session = { ended: false };
    server.use(
      http.get("/api/v1/auth/me", () =>
        session.ended ? errorReply(401, "not_authenticated") : HttpResponse.json(user),
      ),
      http.get("/api/v1/tasks", () => {
        session.ended = true;
        return errorReply(401, "not_authenticated");
      }),
    );
    const { router } = renderApp(routes.tasks);

    expect(await screen.findByRole("heading", { name: "Sign in" })).toBeVisible();
    await delay(100);

    expect(screen.getByRole("heading", { name: "Sign in" })).toBeVisible();
    expect(router.state.location.pathname + router.state.location.search).toBe(
      signInPath(routes.tasks),
    );
  });

  it("signs out and returns to sign-in", async () => {
    const session = { signedIn: true };
    server.use(
      http.get("/api/v1/auth/me", () =>
        session.signedIn ? HttpResponse.json(user) : errorReply(401, "not_authenticated"),
      ),
      http.post("/api/v1/auth/logout", () => {
        session.signedIn = false;
        return new HttpResponse(null, { status: 204 });
      }),
    );
    const { router } = renderApp("/tasks");

    await userEvent.click(await screen.findByRole("button", { name: "Sign out" }));

    expect(await screen.findByRole("heading", { name: "Sign in" })).toBeVisible();
    await waitFor(() => {
      expect(router.state.location.pathname).toBe("/sign-in");
    });
  });
});
