import { z } from "zod";
import { routes } from "../routes.ts";

// "//host" and "/\host" both leave the site in a browser, so only a single leading slash is a path inside the app.
const isAppPath = (path: string): boolean => /^\/(?![/\\])/.test(path);

/** Where to go after signing in: a path inside the app, or the task list for anything else, so it is never an open redirect. */
export const returnToSchema = z.string().refine(isAppPath).catch(routes.tasks);
