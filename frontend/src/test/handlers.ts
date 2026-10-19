import { HttpResponse, http } from "msw";
import type { FieldError, ServerErrorCode } from "../lib/schema/error.ts";
import { tasks, user } from "./fixtures.ts";

type ServerCode = (typeof ServerErrorCode)[keyof typeof ServerErrorCode];

/** An API error reply in the envelope every endpoint uses. */
export const errorReply = (
  status: number,
  code: ServerCode,
  details: readonly FieldError[] = [],
): HttpResponse<{ error: { code: ServerCode; message: string; details: readonly FieldError[] } }> =>
  HttpResponse.json({ error: { code, message: `The API said ${code}.`, details } }, { status });

/** The API's happy path for a signed-in user, answered from the shared fixtures. */
export const handlers = [
  http.get("/api/v1/auth/me", () => HttpResponse.json(user)),
  http.get("/api/v1/tasks", () => HttpResponse.json({ items: tasks })),
];
