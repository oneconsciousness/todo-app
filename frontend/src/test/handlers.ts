import { HttpResponse, delay, http } from "msw";
import { z } from "zod";
import type { FieldError, ServerErrorCode } from "../lib/schema/error.ts";
import { detailTask, tasks, user } from "./fixtures.ts";

type ServerCode = (typeof ServerErrorCode)[keyof typeof ServerErrorCode];

/** An API error reply in the envelope every endpoint uses. */
export const errorReply = (
  status: number,
  code: ServerCode,
  details: readonly FieldError[] = [],
): HttpResponse<{ error: { code: ServerCode; message: string; details: readonly FieldError[] } }> =>
  HttpResponse.json({ error: { code, message: `The API said ${code}.`, details } }, { status });

// The server's side of a move: take the task out of the order, then put it back right after `afterId`.
const serverMove = (ids: readonly string[], id: string, afterId: string | null) => {
  const rest = ids.filter((other) => other !== id);
  return rest.toSpliced(afterId === null ? 0 : rest.indexOf(afterId) + 1, 0, id);
};

const moveBodySchema = z.object({ afterId: z.string().nullable() });

/** How slowly the order-keeping server answers: each move after its own delay, in arrival order, and every list. */
export interface OrderServerTiming {
  readonly moveDelaysMs: readonly number[];
  readonly listDelayMs: number;
}

/**
 * A task server that keeps the order in memory, so a test can see which order each list answer carries. It returns
 * its handlers for `server.use`, and its state: the order, and how many moves and list requests have arrived.
 */
export const orderKeepingServer = ({ moveDelaysMs, listDelayMs }: OrderServerTiming) => {
  const byId = new Map(tasks.map((task) => [task.id, task]));
  const state = { ids: tasks.map((task) => task.id), movesReceived: 0, listRequests: 0 };
  const handlers = [
    http.get("/api/v1/tasks", async () => {
      state.listRequests += 1;
      await delay(listDelayMs);
      return HttpResponse.json({ items: state.ids.map((id) => byId.get(id)) });
    }),
    http.put("/api/v1/tasks/:taskId/position", async ({ params, request }) => {
      const taskId = String(params.taskId);
      const { afterId } = moveBodySchema.parse(await request.json());
      const wait = moveDelaysMs[state.movesReceived] ?? 0;
      state.movesReceived += 1;
      await delay(wait);
      state.ids = serverMove(state.ids, taskId, afterId);
      return HttpResponse.json(byId.get(taskId));
    }),
  ];
  return { state, handlers };
};

// The detail screen's task first, so its id opens the fuller version of that task.
const findTask = (taskId: unknown) => [detailTask, ...tasks].find((task) => task.id === taskId);

/** The API's happy path for a signed-in user, answered from the shared fixtures. */
export const handlers = [
  http.get("/api/v1/auth/me", () => HttpResponse.json(user)),
  http.get("/api/v1/tasks", () => HttpResponse.json({ items: tasks })),
  http.get("/api/v1/tasks/:taskId", ({ params }) => {
    const task = findTask(params.taskId);
    return task ? HttpResponse.json(task) : errorReply(404, "not_found");
  }),
];
