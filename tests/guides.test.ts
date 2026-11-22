// @vitest-environment jsdom
import { access } from "node:fs/promises";
import path from "node:path";
import { createElement } from "react";
import { cleanup, render, screen } from "@testing-library/react";
import { afterEach, expect, it } from "vitest";
import { GUIDES, findGuide, readGuide, rewriteHref } from "@/lib/guides";
import { Markdown } from "@/components/Markdown";
import TrainModel from "@/app/train/page";

afterEach(cleanup);

it("every listed guide file exists in the repository", async () => {
  for (const g of GUIDES) await expect(access(path.join(process.cwd(), g.file))).resolves.toBeUndefined();
  expect(new Set(GUIDES.map((g) => g.slug)).size).toBe(GUIDES.length);
  expect(findGuide("../../etc/passwd")).toBeUndefined();
});

it("keeps links between guides inside the app and sends other repo files to GitHub", () => {
  expect(rewriteHref("docs/local-development.md", "README.md")).toBe("/docs/local-development");
  expect(rewriteHref("trocr-training-contract.md", "docs/setup-guide.md")).toBe("/docs/train-contract");
  expect(rewriteHref("local-development.md#start-and-stop", "docs/setup-guide.md")).toBe("/docs/local-development#start-and-stop");
  expect(rewriteHref("docs/validation-milestones-2-3.md", "README.md")).toBe("https://github.com/Mrl-slll/greentokens/blob/main/docs/validation-milestones-2-3.md");
  expect(rewriteHref("https://brew.sh", "docs/setup-guide.md")).toBe("https://brew.sh");
  expect(rewriteHref("#troubleshooting", "docs/setup-guide.md")).toBe("#troubleshooting");
  expect(rewriteHref("../../outside.md", "docs/setup-guide.md")).toBeUndefined();
});

it("renders the setup guide with copyable Git commands and in-app links", async () => {
  const guide = findGuide("setup")!;
  render(createElement(Markdown, { source: await readGuide(guide), file: guide.file }));
  expect(screen.getByRole("heading", { level: 1, name: "Setup & Git guide" })).toBeTruthy();
  expect(screen.getAllByText("git pull --ff-only").length).toBeGreaterThan(0);
  expect(screen.getAllByRole("button", { name: "Copy" }).length).toBeGreaterThan(5);
  expect(screen.getByRole("link", { name: "Train AI model contract" }).getAttribute("href")).toBe("/docs/train-contract");
});

it("train page never lets a customer start an unsupported job", () => {
  render(createElement(TrainModel));
  expect((screen.getByRole("button", { name: "Start training" }) as HTMLButtonElement).disabled).toBe(true);
  expect(screen.getByText(/Not available yet/)).toBeTruthy();
  expect((screen.getByRole("combobox", { name: "Preset" }) as HTMLSelectElement).closest("fieldset")?.disabled).toBe(true);
  expect(screen.getByText(/64 KB/)).toBeTruthy();
});
