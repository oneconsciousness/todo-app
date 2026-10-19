import { QueryClientProvider, useMutation } from "@tanstack/react-query";
import { renderHook } from "@testing-library/react";
import { http } from "msw";
import type { ReactNode } from "react";
import { describe, expect, it, vi } from "vitest";
import { tasks, user } from "../../test/fixtures.ts";
import { errorReply } from "../../test/handlers.ts";
import { server } from "../../test/server.ts";
import { login } from "../api/auth.ts";
import { listTasks } from "../api/tasks.ts";
import { createQueryClient } from "./client.ts";
import { authKeys, taskKeys } from "./keys.ts";

const credentials = { email: user.email, password: "correct horse battery" };

describe("createQueryClient", () => {
  it("clears the cache and goes to sign-in with a return path on not_authenticated", async () => {
    server.use(http.get("/api/v1/tasks", () => errorReply(401, "not_authenticated")));
    const onUnauthenticated = vi.fn<() => void>();
    const client = createQueryClient({ onUnauthenticated });
    client.setQueryData(authKeys.me, user);

    await client
      .query({ queryKey: taskKeys.list(""), queryFn: ({ signal }) => listTasks("", signal) })
      .catch(() => undefined);

    expect(onUnauthenticated).toHaveBeenCalledOnce();
    expect(client.getQueryData(authKeys.me)).toBeUndefined();
  });

  it("does not redirect on invalid_credentials", async () => {
    server.use(http.post("/api/v1/auth/login", () => errorReply(401, "invalid_credentials")));
    const onUnauthenticated = vi.fn<() => void>();
    const client = createQueryClient({ onUnauthenticated });
    client.setQueryData(taskKeys.list(""), tasks);
    const wrapper = ({ children }: { readonly children: ReactNode }) => (
      <QueryClientProvider client={client}>{children}</QueryClientProvider>
    );
    const { result } = renderHook(() => useMutation({ mutationFn: login }), { wrapper });

    await result.current.mutateAsync(credentials).catch(() => undefined);

    expect(onUnauthenticated).not.toHaveBeenCalled();
    expect(client.getQueryData(taskKeys.list(""))).toEqual(tasks);
  });
});

// Load the task list through a fresh app client while the API answers with `reply`.
const loadListAnswering = async (reply: () => Response): Promise<void> => {
  server.use(http.get("/api/v1/tasks", reply));
  const client = createQueryClient({ onUnauthenticated: () => undefined });
  await client
    .query({ queryKey: taskKeys.list(""), queryFn: ({ signal }) => listTasks("", signal) })
    .catch(() => undefined);
};

describe("failure logging", () => {
  it("logs a failure the server could not handle, with no more than the resource, status and code", async () => {
    const logError = vi.spyOn(console, "error").mockImplementation(() => undefined);

    await loadListAnswering(() => errorReply(500, "internal_error"));

    expect(logError).toHaveBeenCalledWith("[query] failed", {
      key: "tasks",
      status: 500,
      code: "internal_error",
    });
  });

  it.each([
    [400, "validation_failed"],
    [401, "invalid_credentials"],
    [404, "not_found"],
    [409, "email_taken"],
    [412, "version_mismatch"],
  ] as const)("does not log an expected %i %s", async (status, code) => {
    const logError = vi.spyOn(console, "error").mockImplementation(() => undefined);

    await loadListAnswering(() => errorReply(status, code));

    expect(logError).not.toHaveBeenCalled();
  });
});
