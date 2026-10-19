import { setupServer } from "msw/node";
import { handlers } from "./handlers.ts";

/** The mock API every test talks to through `fetch`; a test adds its own handlers with `server.use`. */
export const server = setupServer(...handlers);
