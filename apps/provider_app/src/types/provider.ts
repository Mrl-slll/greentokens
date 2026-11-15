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
<<<<<<< HEAD
export type Connection = "demo" | "offline" | "online";

export interface Credentials {
  username: string;
  password: string;
  deviceId: string;
}

/** Result of the one-click setup (installs the training packages this computer can use). */
export interface PrepareResult {
  torch: string | null;
  gpu: string | null;
  gpuReady: boolean;
  note: string;
}

/** What the provider worker is doing right now (installed app). */
export type WorkerState = "stopped" | "starting" | "online" | "working" | "reconnecting" | "error";
=======
export type Connection = "demo" | "offline";
>>>>>>> d5fa911 (Add GreenTokens Provider Windows desktop app (demo))

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

<<<<<<< HEAD
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

=======
>>>>>>> d5fa911 (Add GreenTokens Provider Windows desktop app (demo))
export interface Activity {
  connection: Connection;
  currentJob: ActivityItem | null;
  history: ActivityItem[];
  completedCount: number;
  totalSeconds: number;
  cpuPercent: number;
  gpuPercent: number | null;
<<<<<<< HEAD
  /** Live mode: what the worker is doing, and the last problem if any. */
  workerState?: WorkerState;
  workerError?: string | null;
  /** Live mode: progress of the current job, when the workload reports it. */
  jobProgress?: { step: number; total: number } | null;
=======
>>>>>>> d5fa911 (Add GreenTokens Provider Windows desktop app (demo))
}

export const DEFAULT_PREFERENCES: Preferences = {
  cpuPercent: 50,
  ramGb: 4,
  gpuEnabled: false,
  notifications: true,
  deviceName: "",
};
