export interface GpuInfo {
  name: string;
  /** null when Windows does not report it. */
  vramGb: number | null;
  /** true when only the 4 GB-capped WMI value is known and it hit the cap. */
  vramAtLeast: boolean;
}

export interface Hardware {
  cpuModel: string;
  cores: number;
  threads: number;
  ramGb: number;
  gpus: GpuInfo[];
  os: string;
  hostname: string;
}

export type HardwareResult =
  | { status: "ok"; hardware: Hardware }
  | { status: "unavailable"; reason: "browser" | "failed"; message: string };

export type Participation = "paused" | "starting" | "active" | "pausing";
export type Connection = "demo" | "offline" | "lan";

/** A private group of computers on one local network. The code carries the leader address and access token. */
export interface Group {
  role: "host" | "member";
  code: string;
}

export const GROUP_CODE_RE = /^GT1-(\d{1,3}(?:\.\d{1,3}){3})-([0-9a-f]{32})$/;

export interface PrepareResult {
  lanIp: string;
  firewall: boolean;
  networkPrivate: boolean;
}

export interface Account {
  displayName: string;
  deviceId: string;
}

export interface Preferences {
  cpuPercent: number;
  ramGb: number;
  gpuEnabled: boolean;
  notifications: boolean;
  deviceName: string;
}

export type JobStatus = "running" | "completed" | "stopped";

export interface ActivityItem {
  id: string;
  name: string;
  startedAt: number;
  seconds: number;
  status: JobStatus;
}

/** Real, current readings from this computer (installed app only). */
export interface LiveUsage {
  /** Whole-computer processor use, 0-100. */
  cpuPercent: number;
  ramUsedGb: number;
  ramTotalGb: number;
  /** Processor use by GreenTokens' own Ray workers, as a percent of the whole computer. */
  greentokensCpuPercent: number;
  greentokensProcesses: number;
  /** null = the graphics card's use can't be measured on this computer (never shown as 0). */
  gpuPercent: number | null;
  /** The first reading after start isn't meaningful. */
  warmingUp: boolean;
}

export interface Activity {
  connection: Connection;
  currentJob: ActivityItem | null;
  history: ActivityItem[];
  completedCount: number;
  totalSeconds: number;
  cpuPercent: number;
  gpuPercent: number | null;
  /** Computers currently in the group (live mode); null when unknown. */
  groupNodes?: number | null;
  /** false when this computer can't currently reach the group leader. */
  leaderReachable?: boolean;
}

export const DEFAULT_PREFERENCES: Preferences = {
  cpuPercent: 50,
  ramGb: 4,
  gpuEnabled: false,
  notifications: true,
  deviceName: "",
};
