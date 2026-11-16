import { mkdir, mkdtemp, rm, writeFile } from "node:fs/promises";
import os from "node:os";
import path from "node:path";
import { afterEach, expect, it } from "vitest";
import { DEMO_RUNS_DIR, latestDemoRun } from "@/lib/demoCheckpoint";
import { POST } from "@/app/api/demo/predict/route";

const roots: string[] = [];
afterEach(async () => { await Promise.all(roots.splice(0).map(r => rm(r, { recursive: true, force: true }))); });

async function makeRun(root: string, name: string, metrics: object | null, weights = true) {
  const dir = path.join(root, DEMO_RUNS_DIR, name);
  await mkdir(dir, { recursive: true });
  if (metrics) await writeFile(path.join(dir, "metrics.json"), JSON.stringify(metrics));
  if (weights) await writeFile(path.join(dir, "model.safetensors"), "");
}

it("picks the newest run with a verified reload and skips unfinished or smoke runs", async () => {
  const root = await mkdtemp(path.join(os.tmpdir(), "gt-demo-"));
  roots.push(root);
  await makeRun(root, "bert-tiny-run-20261114-100000", { checkpoint_reload_verified: true, validation_accuracy: 0.6 });
  await makeRun(root, "bert-tiny-run-20261114-110000", { checkpoint_reload_verified: true, validation_accuracy: 0.8 });
  await makeRun(root, "bert-tiny-run-20261114-120000", { checkpoint_reload_verified: false });
  await makeRun(root, "bert-tiny-run-20261114-130000", null); // still training
  await makeRun(root, "bert-tiny-run-20261114-140000", { checkpoint_reload_verified: true }, false);
  await makeRun(root, "bert-tiny-smoke-20261114-150000", { checkpoint_reload_verified: true });
  const run = await latestDemoRun(root);
  expect(run?.name).toBe("bert-tiny-run-20261114-110000");
  expect(run?.metrics.validation_accuracy).toBe(0.8);
});

it("returns null when no runs exist", async () => {
  const root = await mkdtemp(path.join(os.tmpdir(), "gt-demo-"));
  roots.push(root);
  expect(await latestDemoRun(root)).toBeNull();
});

const call = (body: string, headers: Record<string, string> = {}) =>
  POST(new Request("http://127.0.0.1:3000/api/demo/predict",
    { method: "POST", body, headers: { host: "127.0.0.1:3000", "content-type": "application/json", ...headers } }));

it("rejects cross-origin, non-JSON, and invalid sentences before starting the model", async () => {
  expect((await call('{"text":"hi"}', { origin: "http://evil.example" })).status).toBe(403);
  expect((await call('{"text":"hi"}', { "sec-fetch-site": "cross-site" })).status).toBe(403);
  expect((await call("hi", { "content-type": "text/plain" })).status).toBe(415);
  expect((await call("not json")).status).toBe(400);
  expect((await call('{"text":"   "}')).status).toBe(400);
  expect((await call(JSON.stringify({ text: "x".repeat(1001) }))).status).toBe(400);
  expect((await call(JSON.stringify({ text: "x".repeat(5000) }))).status).toBe(413);
});
