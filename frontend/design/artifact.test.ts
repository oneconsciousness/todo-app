import { describe, expect, it } from "vitest";
import { toArtifact } from "./artifact.ts";

const built = [
  "<!doctype html>",
  '<html lang="en">',
  "  <head>",
  '    <meta charset="UTF-8" />',
  '    <meta name="viewport" content="width=device-width, initial-scale=1.0" />',
  "    <title>todo-app Design Gallery</title>",
  '    <script type="module">console.info("x")</script>',
  "    <style>body{color:red}</style>",
  "  </head>",
  "  <body>",
  '    <div id="root"></div>',
  "  </body>",
  "</html>",
].join("\n");

describe("toArtifact", () => {
  it("drops the document wrapper the artifact host adds itself", () => {
    const artifact = toArtifact(built);
    expect(artifact).not.toMatch(/<!doctype|<html|<\/html>|<head|<\/head>|<body|<\/body>|<meta/i);
  });

  it("opens with the title", () => {
    expect(toArtifact(built).startsWith("<title>todo-app Design Gallery</title>")).toBe(true);
  });

  it("keeps the inlined script, styles and root", () => {
    const artifact = toArtifact(built);
    expect(artifact).toContain('<script type="module">console.info("x")</script>');
    expect(artifact).toContain("<style>body{color:red}</style>");
    expect(artifact).toContain('<div id="root"></div>');
  });

  it("refuses a page that would load anything over the network", () => {
    const remote = built.replace(
      "<style>",
      '<link rel="stylesheet" href="https://x.test/a.css"><style>',
    );
    expect(() => toArtifact(remote)).toThrow(/network/);
  });

  it("refuses a page without a title", () => {
    expect(() => toArtifact(built.replace(/<title>.*<\/title>/, ""))).toThrow(/title/);
  });
});
