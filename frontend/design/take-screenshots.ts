import { mkdir, readFile, rm } from "node:fs/promises";
import { join } from "node:path";
import { fileURLToPath } from "node:url";
import { chromium } from "playwright";
import sharp from "sharp";

const [outDir = fileURLToPath(new URL("screenshots/", import.meta.url))] = process.argv.slice(2);
const statesDir = join(outDir, "states");
const widths = [390, 1280] as const;
const themes = ["light", "dark"] as const;
const settleMs = 400;

const artifact = await readFile(new URL("dist/artifact.html", import.meta.url), "utf8");
// The artifact host wraps the page in this skeleton; the screenshots use the same one.
const page = `<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover"></head><body>${artifact}</body></html>`;

await rm(outDir, { recursive: true, force: true });
await mkdir(statesDir, { recursive: true });
const browser = await chromium.launch();
try {
  for (const width of widths) {
    for (const theme of themes) {
      const context = await browser.newContext({
        viewport: { width, height: 900 },
        colorScheme: theme,
        reducedMotion: "reduce",
      });
      const tab = await context.newPage();
      await tab.setContent(page, { waitUntil: "load" });
      await tab.evaluate((value) => {
        document.documentElement.dataset.theme = value;
      }, theme);
      await tab.evaluate(() => document.fonts.ready);
      await tab.waitForTimeout(settleMs);
      const overflow = await tab.evaluate(
        () => document.documentElement.scrollWidth - document.documentElement.clientWidth,
      );
      if (overflow > 0)
        console.warn(
          `page scrolls sideways by ${String(overflow)}px at ${String(width)}px, ${theme}`,
        );
      const shoot = async (selector: string, attribute: string, dir: string) => {
        for (const element of await tab.locator(selector).all()) {
          const name = (await element.getAttribute(attribute)) ?? "unnamed";
          // A palette PNG keeps the committed set small; the ledger palette has few colours to lose.
          await sharp(await element.screenshot())
            .png({ palette: true, quality: 90, effort: 10, compressionLevel: 9 })
            .toFile(join(dir, `${name}-${String(width)}-${theme}.png`));
        }
      };
      await shoot("[data-section]", "data-section", outDir);
      await shoot("[data-state]", "data-state", statesDir);
      await context.close();
    }
  }
} finally {
  await browser.close();
}
console.info(`screenshots written to ${outDir}`);
