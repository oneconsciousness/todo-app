import tailwindcss from "@tailwindcss/vite";
import react from "@vitejs/plugin-react";
import { defineConfig } from "vite";

/** The compose stack's front door, which is also the API's trusted origin (`APP_ORIGIN`) in local development. */
const STACK_ORIGIN = "http://localhost:8080";

/** Vite config for the app itself. `npm run dev` sends `/api` to the compose stack. */
export default defineConfig({
  plugins: [react(), tailwindcss()],
  server: {
    proxy: {
      // The API refuses writes from any origin but its own, so the dev server presents the stack's origin.
      // https://vite.dev/config/server-options#server-proxy
      "/api": { target: STACK_ORIGIN, headers: { origin: STACK_ORIGIN } },
    },
  },
});
