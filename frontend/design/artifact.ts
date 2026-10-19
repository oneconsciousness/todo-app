const wrapperTags = /<!doctype[^>]*>|<\/?(html|head|body)\b[^>]*>|<meta\b[^>]*>/gi;
const titleTag = /<title>[^<]*<\/title>/i;
const remoteLoads = [
  /<(script|link|img|iframe)\b[^>]*\b(src|href)\s*=\s*["']?(https?:)?\/\//i,
  /url\(\s*["']?(https?:)?\/\//i,
  /@import\s+["'](https?:)?\/\//i,
];

/**
 * Turn Vite's single-file build into an artifact page: no document wrapper (the host adds its own),
 * the title first, and nothing that would reach the network.
 */
export const toArtifact = (html: string): string => {
  const title = titleTag.exec(html)?.[0];
  if (!title)
    throw new Error("The built page has no <title>; the artifact host names the page from it.");
  if (remoteLoads.some((pattern) => pattern.test(html)))
    throw new Error("The built page loads a file over the network; inline it instead.");
  const body = html.replace(titleTag, "").replace(wrapperTags, "").trim();
  return `${title}\n${body}\n`;
};
