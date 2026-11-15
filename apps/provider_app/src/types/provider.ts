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
export type Connection = "demo" | "offline";

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

export interface Activity {
  connection: Connection;
  currentJob: ActivityItem | null;
  history: ActivityItem[];
  completedCount: number;
  totalSeconds: number;
  cpuPercent: number;
  gpuPercent: number | null;
}

export const DEFAULT_PREFERENCES: Preferences = {
  cpuPercent: 50,
  ramGb: 4,
  gpuEnabled: false,
  notifications: true,
  deviceName: "",
};
