import { spawn, type ChildProcess } from "node:child_process";
import path from "node:path";

export const runtime = "nodejs";

const REQUEST_TIMEOUT_MS = 90_000; // Covers the first model load.
const IDLE_SHUTDOWN_MS = 10 * 60_000;
const MAX_QUEUED = 4;

type Prediction = { label: string; probability: number; device: string; source: string; checkpoint: string };
type Pending = { resolve: (value: Prediction) => void; reject: (error: Error) => void; timer: NodeJS.Timeout };
type Worker = { child: ChildProcess; pending: Pending[]; buffer: string; idle?: NodeJS.Timeout };

// One long-lived Python worker keeps the model loaded between requests (survives dev hot reloads).
const store = globalThis as typeof globalThis & { __greentokensDemoWorker?: Worker };

function startWorker(): Worker {
  const child = spawn(path.join(process.cwd(), ".tools/bert-tiny-venv/Scripts/python.exe"),
    [path.join(process.cwd(), "scripts/predict_cpu.py"), "--serve"],
    { windowsHide: true, stdio: ["pipe", "pipe", "ignore"],
      env: { ...process.env, HF_HUB_OFFLINE: "1", HF_HUB_DISABLE_IMPLICIT_TOKEN: "1", TOKENIZERS_PARALLELISM: "false" } });
  const worker: Worker = { child, pending: [], buffer: "" };
  const stop = () => {
    if (store.__greentokensDemoWorker === worker) delete store.__greentokensDemoWorker;
    clearTimeout(worker.idle);
    for (const p of worker.pending.splice(0)) { clearTimeout(p.timer); p.reject(new Error("worker stopped")); }
  };
  child.on("exit", stop);
  child.on("error", stop);
  child.stdin?.on("error", () => child.kill());
  child.stdout?.setEncoding("utf8");
  child.stdout?.on("data", (chunk: string) => {
    worker.buffer += chunk;
    let newline;
    while ((newline = worker.buffer.indexOf("\n")) >= 0) {
      const line = worker.buffer.slice(0, newline).trim();
      worker.buffer = worker.buffer.slice(newline + 1);
      const p = worker.pending.shift();
      if (!line || !p) continue;
      clearTimeout(p.timer);
      try {
        const reply = JSON.parse(line);
        if (reply.error) throw new Error(reply.error);
        p.resolve(reply);
      } catch (e) { p.reject(e instanceof Error ? e : new Error("bad reply")); }
    }
    if (worker.pending.length === 0) {
      clearTimeout(worker.idle);
      worker.idle = setTimeout(() => child.kill(), IDLE_SHUTDOWN_MS);
    }
  });
  store.__greentokensDemoWorker = worker;
  return worker;
}

function predict(worker: Worker, text: string) {
  clearTimeout(worker.idle);
  return new Promise<Prediction>((resolve, reject) => {
    // Killing the worker rejects every queued request via the exit handler.
    const timer = setTimeout(() => worker.child.kill(), REQUEST_TIMEOUT_MS);
    worker.pending.push({ resolve, reject, timer });
    worker.child.stdin?.write(JSON.stringify({ text }) + "\n");
  });
}

export async function POST(req: Request) {
  const url = new URL(req.url);
  const origin = req.headers.get("origin");
  const expected = `${url.protocol}//${req.headers.get("host") ?? url.host}`;
  if ((origin && origin !== expected) || req.headers.get("sec-fetch-site") === "cross-site") {
    return Response.json({ error: "Same-origin requests only" }, { status: 403 });
  }
  if (!req.headers.get("content-type")?.startsWith("application/json")) return Response.json({ error: "JSON required" }, { status: 415 });
  const raw = await req.text();
  if (Buffer.byteLength(raw) > 4096) return Response.json({ error: "Sentence too long" }, { status: 413 });
  let text: unknown;
  try { text = JSON.parse(raw).text; } catch { return Response.json({ error: "Invalid JSON" }, { status: 400 }); }
  if (typeof text !== "string" || !text.trim() || text.length > 1000) return Response.json({ error: "Enter 1–1,000 characters" }, { status: 400 });
  const worker = store.__greentokensDemoWorker ?? startWorker();
  if (worker.pending.length >= MAX_QUEUED) return Response.json({ error: "The model is busy. Please try again in a moment." }, { status: 429 });
  try {
    return Response.json(await predict(worker, text));
  } catch {
    return Response.json({ error: "Could not load the local checkpoint. The recorded training results remain available below." }, { status: 503 });
  }
}
