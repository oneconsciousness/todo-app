import { screen } from "@testing-library/react";
import { http } from "msw";
import { beforeEach, describe, expect, it } from "vitest";
import { routes } from "../lib/routes.ts";
import { submitCredentials } from "../test/credentials.ts";
import { errorReply } from "../test/handlers.ts";
import { renderApp } from "../test/render-app.tsx";
import { server } from "../test/server.ts";

describe("SignUpPage", () => {
  beforeEach(() => {
    server.use(http.get("/api/v1/auth/me", () => errorReply(401, "not_authenticated")));
  });

  it("says the email is taken on 409", async () => {
    server.use(
      http.post("/api/v1/auth/register", () =>
        errorReply(409, "email_taken", [{ field: "email", message: "Already registered." }]),
      ),
    );
    renderApp(routes.signUp);

    await submitCredentials("Create account");

    expect(await screen.findByRole("alert")).toHaveTextContent(
      "An account with this email already exists.",
    );
  });

  it("shows the server's email error next to the field on 400", async () => {
    const message = "The domain name example.test is a special-use or reserved name.";
    server.use(
      http.post("/api/v1/auth/register", () =>
        errorReply(400, "validation_failed", [{ field: "email", message }]),
      ),
    );
    renderApp(routes.signUp);

    await submitCredentials("Create account", "maya@example.test");

    expect(await screen.findByRole("textbox", { name: "Email" })).toHaveAccessibleDescription(
      message,
    );
  });
});
