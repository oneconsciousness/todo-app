import { defineConfig, mergeConfig } from "vitest/config";
import appConfig from "./vite.config.ts";

/** Vitest config: jsdom, Testing Library matchers, and the 85% coverage floor from spec D12. */
export default mergeConfig(
  appConfig,
  defineConfig({
    test: {
      environment: "jsdom",
      setupFiles: ["src/test/setup.ts"],
      css: { include: [/tokens\.css/] },
      include: ["src/**/*.test.{ts,tsx}", "design/**/*.test.{ts,tsx}"],
      coverage: {
        provider: "v8",
        include: ["src/**/*.{ts,tsx}"],
        exclude: ["src/main.tsx", "src/test/**", "src/**/*.test.{ts,tsx}"],
        thresholds: { lines: 85, branches: 85 },
      },
    },
  }),
);
