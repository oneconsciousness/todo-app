import { HttpResponse, http } from "msw";
import { tasks } from "./fixtures.ts";

/** The API's happy path, answered from the shared fixtures. */
export const handlers = [http.get("/api/v1/tasks", () => HttpResponse.json({ items: tasks }))];
