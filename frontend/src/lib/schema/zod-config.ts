import { z } from "zod";

// Zod probes for eval with `new Function` when a schema is built; the app's CSP blocks it and reports a violation
// on every page load. Imported before any schema, so the probe never runs: https://zod.dev/api#jitless
z.config({ jitless: true });
