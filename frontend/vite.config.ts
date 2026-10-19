import tailwindcss from "@tailwindcss/vite";
import react from "@vitejs/plugin-react";
import { defineConfig } from "vite";

/** Vite config for the app itself. */
export default defineConfig({
  plugins: [react(), tailwindcss()],
});
