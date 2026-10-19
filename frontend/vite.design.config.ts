import { defineConfig, mergeConfig } from "vite";
import { viteSingleFile } from "vite-plugin-singlefile";
import appConfig from "./vite.config.ts";

/** Vite config for the design gallery: the app's plugins, built into one self-contained HTML file. */
export default mergeConfig(
  appConfig,
  defineConfig({
    root: "design",
    plugins: [viteSingleFile()],
    build: {
      outDir: "dist",
      emptyOutDir: true,
      assetsInlineLimit: Number.MAX_SAFE_INTEGER,
    },
  }),
);
