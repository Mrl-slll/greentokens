import { expect, it, vi } from "vitest";
import { createLiveProviderService, newGroupToken, type AgentCall } from "../src/services/liveProviderService";
import { ProviderError } from "../src/services/ProviderService";
import { cpusFor } from "../src/hooks/useProvider";
import { DEFAULT_PREFERENCES, GROUP_CODE_RE } from "../src/types/provider";

const CODE = "GT1-192.168.1.20-0123456789abcdef0123456789abcdef";
const okCheck = { ok: true, lan_ip: "192.168.1.30", firewall: true, network_private: true };

function fakeAgent(replies: Record<string, object>) {
  return vi.fn<AgentCall>(async ({ action }) => ({ ok: true, ...(replies[action] ?? {}) }) as never);
}

it("joins with the code and processor count, after checking the network", async () => {
  const call = fakeAgent({ check: okCheck, join: { connected: true } });
  const service = createLiveProviderService(call);
  await service.start(DEFAULT_PREFERENCES, { group: { role: "member", code: CODE }, cpus: 3 });
  expect(call.mock.calls.map(([a]) => a.action)).toEqual(["check", "join"]);
  expect(call.mock.calls[1][0]).toEqual({ action: "join", code: CODE, cpus: 3 });
});

it("asks for the firewall permission only when it's missing, and hosts as leader", async () => {
  const call = fakeAgent({ check: { ...okCheck, firewall: false } });
  await createLiveProviderService(call).start(DEFAULT_PREFERENCES, { group: { role: "host", code: CODE }, cpus: 1 });
  expect(call.mock.calls.map(([a]) => a.action)).toEqual(["check", "firewall", "host"]);
});

it("refuses to connect on a Public network with a plain-English fix", async () => {
  const call = fakeAgent({ check: { ...okCheck, network_private: false } });
  await expect(createLiveProviderService(call).start(DEFAULT_PREFERENCES, { group: { role: "member", code: CODE }, cpus: 1 }))
    .rejects.toThrow(/set to Public/);
  expect(call.mock.calls.map(([a]) => a.action)).toEqual(["check"]);
});

it("passes agent errors through as friendly messages and never claims a connection", async () => {
  const call = vi.fn<AgentCall>(async ({ action }) => (action === "join" ? { ok: false, error: "Couldn't reach the group leader." } : { ...okCheck }));
  const service = createLiveProviderService(call);
  const p = service.start(DEFAULT_PREFERENCES, { group: { role: "member", code: CODE }, cpus: 1 });
  await expect(p).rejects.toBeInstanceOf(ProviderError);
  await expect(p).rejects.toThrow(/group leader/);
  expect((await service.getActivity()).groupNodes).toBeNull();
});

it("reports group size from status, throttled", async () => {
  let t = 0;
  const call = fakeAgent({ check: okCheck, status: { connected: true, nodes: 2 } });
  const service = createLiveProviderService(call, () => t);
  await service.start(DEFAULT_PREFERENCES, { group: { role: "host", code: CODE }, cpus: 1 });
  await service.getActivity();
  await new Promise((r) => setTimeout(r, 0));
  expect((await service.getActivity()).groupNodes).toBe(2);
  const statusCalls = call.mock.calls.filter(([a]) => a.action === "status").length;
  await service.getActivity();
  expect(call.mock.calls.filter(([a]) => a.action === "status").length).toBe(statusCalls); // within 10 s
  t = 11_000;
  await service.getActivity();
  expect(call.mock.calls.filter(([a]) => a.action === "status").length).toBe(statusCalls + 1);
});

it("pause stops the node", async () => {
  const call = fakeAgent({ check: okCheck });
  const service = createLiveProviderService(call);
  await service.start(DEFAULT_PREFERENCES, { group: { role: "host", code: CODE }, cpus: 1 });
  await service.pause();
  expect(call.mock.calls.at(-1)?.[0]).toEqual({ action: "stop" });
});

it("makes valid group tokens and derives processor counts", () => {
  expect(GROUP_CODE_RE.test(`GT1-192.168.1.20-${newGroupToken()}`)).toBe(true);
  const hw = { status: "ok" as const, hardware: { cpuModel: "x", cores: 8, threads: 16, ramGb: 16, gpus: [], os: "", hostname: "" } };
  expect(cpusFor(50, hw)).toBe(8);
  expect(cpusFor(25, hw)).toBe(4);
  expect(cpusFor(10, null)).toBe(1);
});
