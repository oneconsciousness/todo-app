import { QueryClientProvider, useMutation } from "@tanstack/react-query";
import { renderHook } from "@testing-library/react";
import { http } from "msw";
import type { ReactNode } from "react";
import { describe, expect, it, vi } from "vitest";
import { tasks } from "../../test/fixtures.ts";
import { errorReply } from "../../test/handlers.ts";
import { server } from "../../test/server.ts";
import { login } from "../api/auth.ts";
import { listTasks } from "../api/tasks.ts";
import { createQueryClient } from "./client.ts";
import { authKeys, taskKeys } from "./keys.ts";

const user = { id: "00000000-0000-4000-8000-0000000000aa", email: "maya@example.com" };
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
    vi.spyOn(console, "error").mockImplementation(() => undefined);
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
