import { invoke } from "@tauri-apps/api/core";
import { inDesktopApp } from "./hardware";
import type { LiveUsage } from "../types/provider";

/** GreenTokens workers using at least this much of the whole computer count as "training now". */
export const TRAINING_THRESHOLD_PERCENT = 5;

const num = (v: unknown) => (typeof v === "number" && Number.isFinite(v) ? v : 0);

/** Accepts the raw JSON from the `live_usage` command. Missing or odd values never become fake numbers. */
export function normalizeUsage(raw: unknown): LiveUsage {
  const r = (raw ?? {}) as Record<string, unknown>;
  const gpu = typeof r.gpu_percent === "number" && Number.isFinite(r.gpu_percent) ? r.gpu_percent : null;
  return {
    cpuPercent: num(r.cpu_percent),
    ramUsedGb: num(r.ram_used_gb),
    ramTotalGb: num(r.ram_total_gb),
    greentokensCpuPercent: num(r.greentokens_cpu_percent),
    greentokensProcesses: Math.round(num(r.greentokens_processes)),
    gpuPercent: gpu,
    warmingUp: r.warming_up === true,
  };
}

export function isTraining(usage: LiveUsage | null): boolean {
  return !!usage && !usage.warmingUp && usage.greentokensProcesses > 0 && usage.greentokensCpuPercent >= TRAINING_THRESHOLD_PERCENT;
}

export type UsageReader = () => Promise<LiveUsage | null>;

/** null when not running inside the installed app, or if the reading fails. */
export const readLiveUsage: UsageReader = async () => {
  if (!inDesktopApp()) return null;
  try {
    return normalizeUsage(await invoke("live_usage"));
  } catch {
    return null;
  }
};
