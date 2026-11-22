import { readFile } from "node:fs/promises";
import path from "node:path";

/** Repository Markdown files shown in the web app. Only these files can be read. */
export const GUIDES = [
  { slug: "setup", file: "docs/setup-guide.md", title: "Setup & Git guide", summary: "Install Git, get the code, everyday Git commands, and run GreenTokens on the ThinkPad and the Mac." },
  { slug: "readme", file: "README.md", title: "Project README", summary: "What GreenTokens is, how data moves, and the project layout." },
  { slug: "quickstart", file: "docs/developer-quickstart.md", title: "Developer quickstart", summary: "Submit a real training job from the Python client and download the model." },
  { slug: "local-development", file: "docs/local-development.md", title: "Local development", summary: "Start and stop the backend stack safely." },
  { slug: "train-contract", file: "docs/trocr-training-contract.md", title: "Train AI model: backend contract", summary: "What the backend still needs before TrOCR training can run." },
  { slug: "architecture", file: "docs/architecture.md", title: "Architecture", summary: "How the API, database, Ray and storage fit together." },
  { slug: "security", file: "docs/security-boundaries.md", title: "Security boundaries", summary: "What is and isn't protected in the local MVP." },
] as const;

export type Guide = (typeof GUIDES)[number];

const REPO_BLOB = "https://github.com/Mrl-slll/greentokens/blob/main/";

export function findGuide(slug: string): Guide | undefined {
  return GUIDES.find((g) => g.slug === slug);
}

export async function readGuide(guide: Guide, root = process.cwd()): Promise<string> {
  // guide.file always comes from the GUIDES allowlist; pages are pre-rendered at build time.
  return readFile(/*turbopackIgnore: true*/ path.join(/*turbopackIgnore: true*/ root, guide.file), "utf8");
}

/**
 * Rewrite a Markdown link found in `fromFile`:
 * - links to other shown guides stay inside the app (/docs/<slug>, keeping any #anchor),
 * - other repository paths go to GitHub,
 * - absolute URLs and in-page anchors are left alone.
 */
export function rewriteHref(href: string | undefined, fromFile: string): string | undefined {
  if (!href || /^([a-z]+:|#|\/\/)/i.test(href)) return href;
  const [target, hash] = href.split("#");
  const resolved = path.posix.normalize(path.posix.join(path.posix.dirname(fromFile), target));
  const guide = GUIDES.find((g) => g.file === resolved);
  const anchor = hash ? `#${hash}` : "";
  if (guide) return `/docs/${guide.slug}${anchor}`;
  if (resolved.startsWith("..")) return undefined;
  return `${REPO_BLOB}${resolved}${anchor}`;
}
