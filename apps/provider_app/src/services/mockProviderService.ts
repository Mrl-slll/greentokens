// MOCK ONLY. Nothing here contacts GreenTokens or runs work on this computer.
// The UI labels every value that comes from this service as "Demo".
import { ProviderError, type ProviderService, type StartContext } from "./ProviderService";
import type { Activity, ActivityItem, Preferences } from "../types/provider";

export interface MockOptions {
  failSignIn: boolean;
  disconnected: boolean;
}

export interface MockProviderService extends ProviderService {
  options: MockOptions;
}

const JOB_SECONDS = [6, 9, 7, 11, 8];
const JOB_NAMES = ["Sum numbers (test job)", "Data check (test job)", "Small model step (test job)"];

export function createMockProviderService({ delayMs = 700, now = () => Date.now() } = {}): MockProviderService {
  const options: MockOptions = { failSignIn: false, disconnected: false };
  let activeSince: number | null = null;
  let cpuLimit = 50;
  let gpuEnabled = false;
  let sequence = 0;
  let current: ActivityItem | null = null;
  const history: ActivityItem[] = [];
  const wait = () => new Promise<void>((resolve) => setTimeout(resolve, delayMs));

  function newJob(startedAt: number): ActivityItem {
    const n = sequence++;
    return { id: `demo-${n + 1}`, name: JOB_NAMES[n % JOB_NAMES.length], startedAt,
      seconds: JOB_SECONDS[n % JOB_SECONDS.length], status: "running" };
  }

  // Advance simulated jobs up to "now"; each job starts as the previous one ends.
  function advance() {
    if (activeSince === null) return;
    const t = now();
    current ??= newJob(activeSince);
    while (current.startedAt + current.seconds * 1000 <= t) {
      history.unshift({ ...current, status: "completed" });
      current = newJob(current.startedAt + current.seconds * 1000);
    }
    history.splice(50);
  }

  return {
    mode: "mock",
    options,
    async signIn() {
      await wait();
      if (options.disconnected) throw new ProviderError("We can't reach GreenTokens right now. Check your internet connection and try again.");
      if (options.failSignIn) throw new ProviderError("We couldn't sign you in. Please try again.");
      return { displayName: "Demo provider", deviceId: `demo-${Math.random().toString(36).slice(2, 8)}` };
    },
    async signOut() {
      activeSince = null;
      current = null;
      history.length = 0;
    },
    async prepare() {
      await wait();
      if (options.disconnected) throw new ProviderError("We can't reach GreenTokens right now. Check your internet connection and try again.");
      return { lanIp: "192.168.1.10", firewall: true, networkPrivate: true };
    },
    async start(preferences: Preferences, context: StartContext) {
      await wait();
      if (!context.group) throw new ProviderError("First start a group or join one with a code.");
      if (options.disconnected) throw new ProviderError("We can't reach GreenTokens, so your computer stays paused.");
      cpuLimit = preferences.cpuPercent;
      gpuEnabled = preferences.gpuEnabled;
      activeSince = now();
    },
    async pause() {
      // Stop accepting work immediately, before any network round-trip.
      advance();
      if (current) history.unshift({ ...current, status: "stopped", seconds: Math.max(0, Math.round((now() - current.startedAt) / 1000)) });
      activeSince = null;
      current = null;
      await wait();
    },
    async savePreferences(preferences: Preferences) {
      await wait();
      cpuLimit = preferences.cpuPercent;
      gpuEnabled = preferences.gpuEnabled;
      return { enforced: false };
    },
    async getActivity(): Promise<Activity> {
      advance();
      const running = current ? Math.round((now() - current.startedAt) / 1000) : 0;
      const busy = current !== null;
      return {
        connection: options.disconnected ? "offline" : "demo",
        currentJob: current ? { ...current } : null,
        history: history.slice(0, 20),
        completedCount: history.filter((j) => j.status === "completed").length,
        totalSeconds: history.reduce((sum, j) => sum + j.seconds, 0) + running,
        cpuPercent: busy ? Math.min(cpuLimit, 20 + ((sequence * 17) % 30)) : 0,
        gpuPercent: gpuEnabled ? (busy ? 12 : 0) : null,
      };
    },
  };
}
