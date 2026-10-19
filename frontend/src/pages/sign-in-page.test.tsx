import { screen, waitFor } from "@testing-library/react";
import { HttpResponse, http } from "msw";
import { beforeEach, describe, expect, it } from "vitest";
import { routes, signInPath } from "../lib/routes.ts";
import { submitCredentials } from "../test/credentials.ts";
import { detailTask, user } from "../test/fixtures.ts";
import { errorReply } from "../test/handlers.ts";
import { renderApp } from "../test/render-app.tsx";
import { server } from "../test/server.ts";

describe("SignInPage", () => {
  beforeEach(() => {
    server.use(
      http.get("/api/v1/auth/me", () => errorReply(401, "not_authenticated")),
      http.post("/api/v1/auth/login", () => HttpResponse.json(user)),
    );
  });

  it("returns to the page that asked after sign-in", async () => {
    const { router } = renderApp(signInPath(routes.task(detailTask.id)));

    await submitCredentials("Sign in");

    await waitFor(() => {
      expect(router.state.location.pathname).toBe(routes.task(detailTask.id));
    });
  });

  it("ignores an external returnTo", async () => {
    const { router } = renderApp(signInPath("//evil.example/steal"));

    await submitCredentials("Sign in");

    await waitFor(() => {
      expect(router.state.location.pathname).toBe(routes.tasks);
    });
  });

  it("says the email or password is wrong on 401", async () => {
    server.use(http.post("/api/v1/auth/login", () => errorReply(401, "invalid_credentials")));
    const { router } = renderApp(routes.signIn);

    await submitCredentials("Sign in");

    expect(await screen.findByRole("alert")).toHaveTextContent(
      "That email and password don't match an account.",
    );
    expect(router.state.location.pathname).toBe(routes.signIn);
  });
});
