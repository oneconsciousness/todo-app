import { mkdir, readFile } from "node:fs/promises";
import { join } from "node:path";
import { fileURLToPath } from "node:url";
import { chromium } from "playwright";

const [outDir = fileURLToPath(new URL("screenshots/", import.meta.url)), mode = "sections"] =
  process.argv.slice(2);
const widths = [390, 1280] as const;
const themes = ["light", "dark"] as const;
const target = mode === "--states" ? "[data-state]" : "[data-section]";
const nameOf = mode === "--states" ? "data-state" : "data-section";

const artifact = await readFile(new URL("dist/artifact.html", import.meta.url), "utf8");
// The artifact host wraps the page in this skeleton; the screenshots use the same one.
const page = `<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover"></head><body>${artifact}</body></html>`;

await mkdir(outDir, { recursive: true });
const browser = await chromium.launch();
try {
  for (const width of widths) {
    for (const theme of themes) {
      const context = await browser.newContext({
        viewport: { width, height: 900 },
        colorScheme: theme,
        deviceScaleFactor: 1,
      });
      const tab = await context.newPage();
      await tab.setContent(page, { waitUntil: "load" });
      await tab.evaluate((value) => {
        document.documentElement.dataset.theme = value;
      }, theme);
      await tab.evaluate(() => document.fonts.ready);
      const overflow = await tab.evaluate(
        () => document.documentElement.scrollWidth - document.documentElement.clientWidth,
      );
      if (overflow > 0)
        console.warn(
          `page scrolls sideways by ${String(overflow)}px at ${String(width)}px, ${theme}`,
        );
      for (const section of await tab.locator(target).all()) {
        const name = (await section.getAttribute(nameOf)) ?? "section";
        const slug = name.toLowerCase().replaceAll(" ", "-");
        await section.screenshot({ path: join(outDir, `${slug}-${String(width)}-${theme}.png`) });
      }
      await context.close();
    }
  }
} finally {
  await browser.close();
}
console.info(`screenshots written to ${outDir}`);
