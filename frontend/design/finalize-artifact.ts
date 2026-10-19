import { readFile, rm, stat, writeFile } from "node:fs/promises";
import { toArtifact } from "./artifact.ts";

const built = new URL("dist/index.html", import.meta.url);
const artifact = new URL("dist/artifact.html", import.meta.url);
const sizeLimit = 16 * 1024 * 1024;

await writeFile(artifact, toArtifact(await readFile(built, "utf8")));
await rm(built);
const { size } = await stat(artifact);
if (size > sizeLimit)
  throw new Error(`artifact.html is ${String(size)} bytes, over the 16 MB limit`);
console.info(`design artifact written: ${artifact.pathname} (${(size / 1024).toFixed(0)} KB)`);
