import { z } from "zod";
import { routes } from "../routes.ts";

// Resolve the value the way the browser would, so "//host", "/\host" and the forms with a tab or newline in them
// (which URL parsing strips) all show their real origin; only this app's own origin keeps its path.
// https://url.spec.whatwg.org/#concept-basic-url-parser
const appPath = (value: string): string | null => {
  const { origin } = window.location;
  try {
    const url = new URL(value, origin);
    return url.origin === origin ? url.pathname + url.search + url.hash : null;
  } catch {
    return null;
  }
};

/** Where to go after signing in: a path inside the app, or the task list for anything else, so it is never an open redirect. */
export const returnToSchema = z.string().transform(appPath).pipe(z.string()).catch(routes.tasks);

/** The task id in a detail URL; anything that is not a UUID cannot be a task, so no request is made for it. */
export const taskIdParamSchema = z.uuid();
