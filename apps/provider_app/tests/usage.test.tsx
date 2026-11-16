import { createElement } from "react";
import { act, cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, beforeEach, expect, it, vi } from "vitest";
import App from "../src/App";
import { createMockProviderService } from "../src/services/mockProviderService";
import { createLiveProviderService } from "../src/services/liveProviderService";
import { isTraining, normalizeUsage } from "../src/services/usage";
import * as usageModule from "../src/services/usage";
import type { HardwareDetector } from "../src/services/hardware";
import type { HardwareResult, LiveUsage } from "../src/types/provider";

const CODE = "GT1-192.168.1.20-0123456789abcdef0123456789abcdef";
const sample = (over: Partial<LiveUsage> = {}): LiveUsage => ({
  cpuPercent: 40, ramUsedGb: 9.5, ramTotalGb: 16, greentokensCpuPercent: 25, greentokensProcesses: 2, gpuPercent: null, warmingUp: false, ...over,
});
const hardware = (gpus: { name: string; vramGb: number | null; vramAtLeast: boolean }[]): HardwareDetector => async () =>
  ({ status: "ok", hardware: { cpuModel: "Test", cores: 8, threads: 16, ramGb: 16, gpus, os: "Windows 11", hostname: "PC" } }) as HardwareResult;

beforeEach(() => localStorage.clear());
afterEach(() => {
  cleanup();
  vi.restoreAllMocks();
});

it("turns the raw command output into numbers, and never turns a missing GPU reading into 0", () => {
  const u = normalizeUsage({ cpu_percent: 12.5, ram_used_gb: 7, ram_total_gb: 16, greentokens_cpu_percent: 6.2, greentokens_processes: 3, gpu_percent: null, warming_up: false });
  expect(u).toEqual({ cpuPercent: 12.5, ramUsedGb: 7, ramTotalGb: 16, greentokensCpuPercent: 6.2, greentokensProcesses: 3, gpuPercent: null, warmingUp: false });
  expect(normalizeUsage({ gpu_percent: 41 }).gpuPercent).toBe(41);
  expect(normalizeUsage(undefined).gpuPercent).toBeNull();
  expect(normalizeUsage({ cpu_percent: "x", warming_up: "yes" }).cpuPercent).toBe(0);
});

it("says 'training' only when GreenTokens workers really use the processor", () => {
  expect(isTraining(sample())).toBe(true);
  expect(isTraining(sample({ greentokensCpuPercent: 1.2 }))).toBe(false); // idle Ray workers
  expect(isTraining(sample({ greentokensProcesses: 0 }))).toBe(false);
  expect(isTraining(sample({ warmingUp: true }))).toBe(false);
  expect(isTraining(null)).toBe(false);
});

async function openLiveActivity(detect: HardwareDetector, readings: (LiveUsage | null)[]) {
  let call = 0;
  vi.spyOn(usageModule, "readLiveUsage").mockImplementation(async () => readings[Math.min(call++, readings.length - 1)]);
  const agent = vi.fn(async ({ action }: { action: string }) => ({ ok: true, lan_ip: "192.168.1.30", firewall: true, network_private: true, connected: action !== "stop", nodes: 2 }) as never);
  const service = createLiveProviderService(agent as never);
  render(createElement(App, { service, detectHardware: detect }));
  fireEvent.click(await screen.findByRole("button", { name: "Join a group" }));
  fireEvent.change(await screen.findByLabelText(/Group code/), { target: { value: CODE } });
  fireEvent.click(screen.getByRole("button", { name: "Join" }));
  await screen.findByText(/Joined the group led by/);
  fireEvent.click(screen.getByRole("button", { name: "Connect" }));
  fireEvent.click(await screen.findByRole("button", { name: "Agree & Connect" }));
  await screen.findByRole("heading", { name: "Connected" });
  fireEvent.click(screen.getByRole("button", { name: "Activity" }));
}

it("live Activity shows real numbers and none of the old placeholder text", async () => {
  await openLiveActivity(hardware([{ name: "Test GPU", vramGb: 4, vramAtLeast: false }]), [sample({ warmingUp: true }), sample({ gpuPercent: 37 })]);
  await screen.findByText("Training a GreenTokens job now");
  expect(await screen.findByText("25%")).toBeTruthy(); // GreenTokens' share
  expect(screen.getByText("40%")).toBeTruthy(); // whole computer
  expect(screen.getByText("9.5 of 16 GB")).toBeTruthy();
  expect(screen.getByText("37%")).toBeTruthy(); // GPU
  expect(screen.getByRole("img", { name: /processor use over the last minute/ })).toBeTruthy();
  expect(screen.queryByText(/Simulated/)).toBeNull();
  expect(screen.queryByText(/Demo/)).toBeNull();
  expect(screen.queryByText(/aren't sent/)).toBeNull();
});

it("shows waiting, 'No GPU found' and 'Not measured' honestly", async () => {
  await openLiveActivity(hardware([]), [sample({ greentokensCpuPercent: 0.4, greentokensProcesses: 2 })]);
  await screen.findByText("Connected, waiting for work");
  expect(screen.getByText("No GPU found")).toBeTruthy();
  cleanup();
  localStorage.clear(); // forget the group saved by the first half
  await openLiveActivity(hardware([{ name: "Integrated", vramGb: null, vramAtLeast: false }]), [sample({ gpuPercent: null })]);
  expect(await screen.findByText("Not measured")).toBeTruthy();
});

it("stops reading usage when the Activity screen is closed", async () => {
  await openLiveActivity(hardware([]), [sample()]);
  await screen.findByText("Training a GreenTokens job now");
  fireEvent.click(screen.getByRole("button", { name: "Home" }));
  const spy = vi.mocked(usageModule.readLiveUsage);
  await act(async () => {
    spy.mockClear();
    await new Promise((r) => setTimeout(r, 2300));
  });
  // Home keeps one reader (the 'using X%' line) but Activity's second reader must be gone.
  expect(spy.mock.calls.length).toBeLessThanOrEqual(3);
});

it("keeps the demo version clearly labelled, with no live numbers", async () => {
  render(createElement(App, { service: createMockProviderService({ delayMs: 0 }), detectHardware: hardware([]) }));
  expect(screen.getByText(/Demo version/)).toBeTruthy();
  await waitFor(() => expect(usageModule.readLiveUsage).toBeDefined());
});
