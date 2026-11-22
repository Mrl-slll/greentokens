import { expect, it, vi } from "vitest";
import { createLiveProviderService, type Bridge } from "../src/services/liveProviderService";
import { ProviderError } from "../src/services/ProviderService";
import { fakeAuth, credentials, TEST_KEY } from "./fixtures";
import { cpusFor } from "../src/hooks/useProvider";
import { DEFAULT_PREFERENCES } from "../src/types/provider";

const context = { deviceId: credentials.deviceId, deviceName: "RTX-PC-1", cpus: 4 };

function fakeBridge(states: Record<string, unknown>[], setup: Record<string, unknown> = {}) {
  let i = 0;
  const bridge = {
    agent: vi.fn(async () => ({ ok: true, ...setup })),
    workerStart: vi.fn(async () => ({ ok: true, running: true })),
    workerStop: vi.fn(async () => ({ ok: true, running: false })),
    workerState: vi.fn(async () => states[Math.min(i++, states.length - 1)]),
  };
  return bridge as typeof bridge & Bridge;
}
const service = (bridge: Bridge, timeout = 5000) => {
  let t = 0;
  return createLiveProviderService(bridge, () => t, async (ms) => { t += ms; }, timeout, fakeAuth());
};

it("one-click setup reports what was installed and whether the GPU is usable", async () => {
  const bridge = fakeBridge([], { torch: "2.15.0+cu132", gpu: "NVIDIA GeForce RTX 5070", gpu_ready: true, note: "GPU support installed" });
  expect(await service(bridge).prepare()).toEqual({ torch: "2.15.0+cu132", gpu: "NVIDIA GeForce RTX 5070", gpuReady: true, note: "GPU support installed" });
  expect(bridge.agent).toHaveBeenCalledWith("setup");
});

it("connects outward with the signed-in session and resolves only once the worker is online", async () => {
  const bridge = fakeBridge([{ state: "starting", running: true }, { state: "online", running: true }]);
  const s = service(bridge);
  await s.signIn(credentials);
  await s.start(DEFAULT_PREFERENCES, context);
  expect(bridge.workerStart).toHaveBeenCalledWith({ server: "https://gt.example.com", key: TEST_KEY, deviceId: context.deviceId, name: "RTX-PC-1" });
  expect(bridge.workerState).toHaveBeenCalledTimes(2);
});

it("requires sign-in and explains an expired session without staying half-connected", async () => {
  await expect(service(fakeBridge([])).start(DEFAULT_PREFERENCES, context)).rejects.toThrow(/sign in/);
  const bridge = fakeBridge([{ state: "error", error: "Your GreenTokens session expired or was revoked. Sign out and sign in again." }]);
  const s = service(bridge);
  await s.signIn(credentials);
  const p = s.start(DEFAULT_PREFERENCES, context);
  await expect(p).rejects.toBeInstanceOf(ProviderError);
  await expect(p).rejects.toThrow(/session expired/);
  expect(bridge.workerStop).toHaveBeenCalled();
});

it("gives up with a clear message when the server can't be reached in time", async () => {
  const bridge = fakeBridge([{ state: "reconnecting", running: true }]);
  const s = service(bridge, 3000);
  await s.signIn(credentials);
  await expect(s.start(DEFAULT_PREFERENCES, context)).rejects.toThrow(/Couldn't reach the GreenTokens server/);
  expect(bridge.workerStop).toHaveBeenCalled();
});

it("pause stops the worker; nothing ever runs ray stop", async () => {
  const bridge = fakeBridge([{ state: "online" }]);
  const s = service(bridge);
  await s.signIn(credentials);
  await s.start(DEFAULT_PREFERENCES, context);
  await s.pause();
  expect(bridge.workerStop).toHaveBeenCalledTimes(1);
  expect(bridge.agent).not.toHaveBeenCalledWith("stop");
});

it("activity shows the real job and its progress while working", async () => {
  const bridge = fakeBridge([{ state: "online" }, { state: "working", running: true,
    job: { id: "job-1", workload: "text_finetune", started: 100, progress: { step: 30, total: 63 } } }]);
  const s = service(bridge);
  await s.signIn(credentials);
  await s.start(DEFAULT_PREFERENCES, context);
  const a = await s.getActivity();
  expect(a.workerState).toBe("working");
  expect(a.currentJob?.name).toBe("text_finetune");
  expect(a.jobProgress).toEqual({ step: 30, total: 63 });
});

it("offers the chosen share of processor threads", () => {
  const hw = { status: "ok" as const, hardware: { cpuModel: "x", cores: 8, threads: 16, ramGb: 16, gpus: [], os: "Windows", hostname: "PC" } };
  expect(cpusFor(50, hw)).toBe(8);
  expect(cpusFor(1, null)).toBe(1);
});
