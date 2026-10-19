import { screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { HttpResponse, delay, http } from "msw";
import { describe, expect, it, vi } from "vitest";
import { routes, signInPath } from "../lib/routes.ts";
import { detailTask, user } from "../test/fixtures.ts";
import { errorReply } from "../test/handlers.ts";
import { renderApp } from "../test/render-app.tsx";
import { server } from "../test/server.ts";

const notFoundHeading = { name: "This task isn't in your ledger" };
const taskUrl = `/api/v1/tasks/${detailTask.id}`;

describe("app router", () => {
  it("shows not found for another user's task id", async () => {
    vi.spyOn(console, "error").mockImplementation(() => undefined);
    renderApp(routes.task("7b0c1e5a-0000-4000-8000-00000000ffff"));

    expect(await screen.findByRole("heading", notFoundHeading)).toBeVisible();
  });

  it("shows not found for an unknown route", async () => {
    renderApp("/ledger/nowhere");

    expect(
      await screen.findByRole("heading", { name: "This page isn't in the ledger" }),
    ).toBeVisible();
  });

  it("shows the error screen when a task fails to load", async () => {
    vi.spyOn(console, "error").mockImplementation(() => undefined);
    server.use(http.get(taskUrl, () => errorReply(500, "internal_error")));
    renderApp(routes.task(detailTask.id));

    expect(await screen.findByRole("heading", { name: "Something went wrong" })).toBeVisible();
  });

  it("loads the page again from the error screen", async () => {
    vi.spyOn(console, "error").mockImplementation(() => undefined);
    const state = { failed: false };
    server.use(
      http.get(taskUrl, () => {
        if (state.failed) return HttpResponse.json(detailTask);
        state.failed = true;
        return errorReply(500, "internal_error");
      }),
    );
    renderApp(routes.task(detailTask.id));

    await userEvent.click(await screen.findByRole("button", { name: "Try again" }));

    expect(await screen.findByRole("heading", { level: 1, name: detailTask.title })).toBeVisible();
  });

  it("goes to the task list from the error screen", async () => {
    vi.spyOn(console, "error").mockImplementation(() => undefined);
    server.use(http.get(taskUrl, () => errorReply(500, "internal_error")));
    const { router } = renderApp(routes.task(detailTask.id));

    await userEvent.click(await screen.findByRole("button", { name: "Go to tasks" }));

    expect(await screen.findByRole("list", { name: "Tasks" })).toBeVisible();
    expect(router.state.location.pathname).toBe(routes.tasks);
  });

  it("shows not found for a task id that is not a UUID, without asking the server", async () => {
    const taskRequests = vi.fn<() => void>();
    server.use(
      http.get("/api/v1/tasks/:taskId", () => {
        taskRequests();
        return errorReply(404, "not_found");
      }),
    );
    renderApp(routes.task("not-a-task"));

    expect(await screen.findByRole("heading", notFoundHeading)).toBeVisible();
    expect(taskRequests).not.toHaveBeenCalled();
  });

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
