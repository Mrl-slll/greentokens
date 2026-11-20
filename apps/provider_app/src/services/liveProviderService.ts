// LIVE: drives the bundled agent (src-tauri/agent/gt_agent.py) through Tauri commands.
// The worker connects OUTWARD to the GreenTokens server (no groups, no Ray on this computer),
// asks for approved work, runs it and returns the results. It reconnects by itself.
import { invoke } from "@tauri-apps/api/core";
import { ProviderError, type ProviderService, type StartContext } from "./ProviderService";
import type { Activity, Preferences, PrepareResult, WorkerState } from "../types/provider";
import { createProviderAuth, type ProviderAuth } from "./providerAuth";

type Reply = { ok?: boolean; error?: string } & Record<string, unknown>;

export interface Bridge {
  agent(action: "setup" | "capabilities"): Promise<Reply>;
  workerStart(args: { server: string; key: string; deviceId: string; name: string }): Promise<Reply>;
  workerStop(): Promise<Reply>;
  workerState(): Promise<Reply>;
}

const tauriBridge: Bridge = {
  agent: (action) => invoke<Reply>("agent", { action }),
  workerStart: (args) => invoke<Reply>("worker_start", args),
  workerStop: () => invoke<Reply>("worker_stop"),
  workerState: () => invoke<Reply>("worker_state"),
};

const STATES: WorkerState[] = ["stopped", "starting", "online", "working", "reconnecting", "error"];
const asState = (v: unknown): WorkerState => (STATES.includes(v as WorkerState) ? (v as WorkerState) : "stopped");

export function createLiveProviderService(bridge: Bridge = tauriBridge, now = () => Date.now(),
  sleep = (ms: number) => new Promise<void>((r) => setTimeout(r, ms)), startTimeoutMs = 90_000,
  auth: ProviderAuth = createProviderAuth()): ProviderService {
  let connectedSince: number | null = null;

  async function call<T>(fn: () => Promise<T>): Promise<T> {
    try { return await fn(); }
    catch (e) { throw new ProviderError(typeof e === "string" ? e : "Something went wrong on this computer. Please try again."); }
  }

  return {
    mode: "live",
    signIn: (credentials) => auth.authenticate("login", credentials),
    signUp: (credentials) => auth.authenticate("signup", credentials),
    async signOut() { await call(() => bridge.workerStop()); connectedSince = null; await auth.signOut(); },
    async prepare(): Promise<PrepareResult> {
      const r = await call(() => bridge.agent("setup"));
      if (r.ok === false) throw new ProviderError(r.error ?? "Setup didn't finish. Please try again.");
      return { torch: typeof r.torch === "string" ? r.torch : null, gpu: typeof r.gpu === "string" ? r.gpu : null,
        gpuReady: r.gpu_ready === true, note: typeof r.note === "string" ? r.note : "" };
    },
    async start(_preferences: Preferences, context: StartContext) {
      const connection = auth.connection();
      if (connection.deviceId !== context.deviceId) throw new ProviderError("Please sign in on this computer first.");
      await call(() => bridge.workerStart({ server: connection.server, key: connection.key, deviceId: context.deviceId, name: context.deviceName }));
      const deadline = now() + startTimeoutMs;
      while (now() < deadline) {
        const s = await call(() => bridge.workerState());
        const state = asState(s.state);
        if (state === "online" || state === "working") { connectedSince = now(); return; }
        if (state === "error") {
          await call(() => bridge.workerStop());
          throw new ProviderError(typeof s.error === "string" ? s.error : "This computer couldn't connect to GreenTokens.");
        }
        await sleep(1000);
      }
      await call(() => bridge.workerStop());
      throw new ProviderError("Couldn't reach the GreenTokens server. Check your connection and ask the operator whether the server is running.");
    },
    async pause() {
      await call(() => bridge.workerStop());
      connectedSince = null;
    },
    async savePreferences() {
      // The worker runs one job at a time; processor and memory limits aren't enforced yet.
      return { enforced: false };
    },
    async getActivity(): Promise<Activity> {
      let s: Reply = { state: "stopped" };
      try { s = await bridge.workerState(); } catch { /* app is closing or not installed */ }
      const state = s.running === false && connectedSince !== null ? "stopped" : asState(s.state);
      const job = (s.job ?? null) as { id?: string; workload?: string; started?: number; progress?: { step?: number; total?: number } } | null;
      const startedMs = typeof job?.started === "number" ? job.started * 1000 : now();
      return {
        connection: "online",
        currentJob: state === "working" && job?.id
          ? { id: job.id, name: job.workload ?? "Training job", startedAt: startedMs, seconds: Math.max(0, (now() - startedMs) / 1000), status: "running" }
          : null,
        history: [],
        completedCount: 0,
        totalSeconds: connectedSince === null ? 0 : (now() - connectedSince) / 1000,
        cpuPercent: 0,
        gpuPercent: null,
        workerState: state,
        workerError: typeof s.error === "string" ? s.error : null,
        jobProgress: typeof job?.progress?.step === "number" && typeof job?.progress?.total === "number"
          ? { step: job.progress.step, total: job.progress.total } : null,
      };
    },
  };
}
