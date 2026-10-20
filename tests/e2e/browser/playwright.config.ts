import { defineConfig, devices } from "@playwright/test";

/** The browser journeys run against the stack's front door: compose on port 8080, or `BASE_URL` (k3d: https://localhost:8443). */
export default defineConfig({
  testDir: ".",
  testMatch: "*.spec.ts",
  fullyParallel: true,
  forbidOnly: true,
  // A journey that passes only on a second try is a bug to find, not to hide.
  retries: 0,
  reporter: [["list"], ["html", { outputFolder: "playwright-report", open: "never" }]],
  use: {
    baseURL: process.env.BASE_URL ?? "http://localhost:8080",
    // Only on a Mac that has not yet trusted mkcert's local authority with `mkcert -install`.
    ignoreHTTPSErrors: process.env.IGNORE_HTTPS_ERRORS === "1",
    trace: "retain-on-failure",
  },
  projects: [{ name: "chromium", use: { ...devices["Desktop Chrome"] } }],
});
