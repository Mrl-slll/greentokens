// LIVE: drives the bundled agent (src-tauri/agent/gt_agent.py) through the Tauri `agent` command.
// Connecting really starts or joins a private Ray group on the local network.
import { invoke } from "@tauri-apps/api/core";
import { ProviderError, type ProviderService, type StartContext } from "./ProviderService";
import type { Activity, Group, Preferences, PrepareResult } from "../types/provider";

type Reply = { ok: boolean; error?: string } & Record<string, unknown>;
export type AgentCall = (args: { action: string; cpus?: number; code?: string }) => Promise<Reply>;

const tauriAgent: AgentCall = (args) => invoke<Reply>("agent", args);
const STATUS_EVERY_MS = 10_000;

export function createLiveProviderService(call: AgentCall = tauriAgent, now = () => Date.now()): ProviderService {
  let group: Group | null = null;
  let connectedSince: number | null = null;
  let nodes: number | null = null;
  let leaderReachable = true;
  let lastStatus = Number.NEGATIVE_INFINITY; // never polled
  let polling = false;

  async function agent(args: Parameters<AgentCall>[0]): Promise<Reply> {
    let reply: Reply;
    try { reply = await call(args); }
    catch (e) { throw new ProviderError(typeof e === "string" ? e : "Something went wrong on this computer. Please try again."); }
    if (!reply.ok) throw new ProviderError(reply.error ?? "Something went wrong on this computer. Please try again.");
    return reply;
  }

  async function refreshStatus() {
    if (!group || connectedSince === null || polling || now() - lastStatus < STATUS_EVERY_MS) return;
    polling = true;
    lastStatus = now();
    try {
      const s = await agent({ action: "status", code: group.code });
      leaderReachable = s.connected === true;
      nodes = typeof s.nodes === "number" && leaderReachable ? s.nodes : null;
    } catch { leaderReachable = false; nodes = null; }
    finally { polling = false; }
  }

  return {
    mode: "live",
    async signIn() { return { displayName: "This computer", deviceId: "local" }; },
    async signOut() { await agent({ action: "stop" }); group = null; connectedSince = null; },
    async prepare(): Promise<PrepareResult> {
      const r = await agent({ action: "check" });
      return { lanIp: String(r.lan_ip ?? ""), firewall: r.firewall === true, networkPrivate: r.network_private === true };
    },
    async start(_preferences: Preferences, context: StartContext) {
      if (!context.group) throw new ProviderError("First start a group or join one with a code (below the button).");
      const check = await agent({ action: "check" });
      if (check.network_private !== true) {
        throw new ProviderError("Windows has this network set to Public, which blocks groups. Open Settings → Network & internet → your Wi-Fi or Ethernet network, choose Private, then try again.");
      }
      if (check.firewall !== true) await agent({ action: "firewall" }); // one-time Windows permission prompt
      await agent({ action: context.group.role === "host" ? "host" : "join", code: context.group.code, cpus: context.cpus });
      group = context.group;
      connectedSince = now();
      leaderReachable = true;
      nodes = null;
      lastStatus = Number.NEGATIVE_INFINITY; // poll right away
    },
    async pause() {
      await agent({ action: "stop" });
      connectedSince = null;
      nodes = null;
    },
    async savePreferences() {
      // The processor share is applied on the next Connect; memory isn't enforced by Ray's CLI.
      return { enforced: false };
    },
    async getActivity(): Promise<Activity> {
      void refreshStatus();
      return {
        connection: "lan",
        currentJob: null,
        history: [],
        completedCount: 0,
        totalSeconds: connectedSince === null ? 0 : (now() - connectedSince) / 1000,
        cpuPercent: 0,
        gpuPercent: null,
        groupNodes: connectedSince === null ? null : nodes,
        leaderReachable,
      };
    },
  };
}

/** 16 random bytes as lowercase hex: the group's access token. */
export function newGroupToken(): string {
  const bytes = new Uint8Array(16);
  crypto.getRandomValues(bytes);
  return Array.from(bytes, (b) => b.toString(16).padStart(2, "0")).join("");
}
