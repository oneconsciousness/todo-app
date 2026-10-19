import { HttpResponse, http } from "msw";
import { describe, expect, it, vi } from "vitest";
import { taskListSchema, taskSchema } from "../schema/task.ts";
import { detailTask, tasks } from "../../test/fixtures.ts";
import { server } from "../../test/server.ts";
import { ApiError, ApiErrorCode, apiRequest, apiRequestNoContent } from "./client.ts";

const taskUrl = `/api/v1/tasks/${detailTask.id}`;

const rejection = async (request: Promise<unknown>): Promise<unknown> =>
  request.then(
    () => undefined,
    (error: unknown) => error,
  );

describe("apiRequest", () => {
  it("parses a success body with the schema", async () => {
    await expect(apiRequest("/tasks", { schema: taskListSchema })).resolves.toEqual({
      items: tasks,
    });
  });

  it("turns the error envelope into an ApiError with its code", async () => {
    server.use(
      http.post("/api/v1/auth/register", () =>
        HttpResponse.json(
          {
            error: {
              code: "email_taken",
              message: "An account with this email already exists.",
              details: [{ field: "email", message: "An account with this email already exists." }],
            },
          },
          { status: 409 },
        ),
      ),
    );
    const error = await rejection(
      apiRequest("/auth/register", { method: "POST", body: {}, schema: taskSchema }),
    );
    expect(error).toBeInstanceOf(ApiError);
    expect(error).toMatchObject({
      status: 409,
      code: ApiErrorCode.EmailTaken,
      details: [{ field: "email", message: "An account with this email already exists." }],
    });
  });

  it("turns a plain-text 503 into service_unavailable", async () => {
    server.use(
      http.get("/api/v1/tasks", () => new HttpResponse("Service Unavailable", { status: 503 })),
    );
    await expect(apiRequest("/tasks", { schema: taskListSchema })).rejects.toMatchObject({
      status: 503,
      code: ApiErrorCode.ServiceUnavailable,
    });
  });

  it("sends If-Match as a quoted version", async () => {
    const ifMatch = vi.fn<(value: string | null) => void>();
    server.use(
      http.patch(taskUrl, ({ request }) => {
        ifMatch(request.headers.get("If-Match"));
        return HttpResponse.json(detailTask);
      }),
    );
    await apiRequest(`/tasks/${detailTask.id}`, {
      method: "PATCH",
      body: { title: detailTask.title },
      ifMatch: 3,
      schema: taskSchema,
    });
    expect(ifMatch).toHaveBeenCalledWith('"3"');
  });

  it("reports a schema mismatch as invalid_response", async () => {
    const logError = vi.spyOn(console, "error").mockImplementation(() => undefined);
    server.use(http.get("/api/v1/tasks", () => HttpResponse.json({ items: [{ id: "x" }] })));
    await expect(apiRequest("/tasks", { schema: taskListSchema })).rejects.toMatchObject({
      code: ApiErrorCode.InvalidResponse,
    });
    expect(logError).toHaveBeenCalledWith(
      "[api] response did not match schema",
      expect.objectContaining({ path: "/tasks" }),
    );
  });
});

describe("apiRequestNoContent", () => {
  it("returns nothing for 204", async () => {
    server.use(http.delete(taskUrl, () => new HttpResponse(null, { status: 204 })));
    await expect(
      apiRequestNoContent(`/tasks/${detailTask.id}`, { method: "DELETE" }),
    ).resolves.toBeUndefined();
  });
});
