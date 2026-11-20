import { invoke } from "@tauri-apps/api/core";
import type { GpuInfo, Hardware, HardwareResult } from "../types/provider";

const GIB = 1024 ** 3;
// Software adapters that are not real graphics cards.
const NOT_A_GPU = /^Microsoft (Basic Display|Basic Render|Remote Display)/i;

const num = (v: unknown) => (typeof v === "number" && Number.isFinite(v) && v > 0 ? v : 0);
const str = (v: unknown, fallback: string) => (typeof v === "string" && v.trim() ? v.trim() : fallback);

/** Accepts the raw JSON from detect_hardware.ps1 and tolerates Windows PowerShell 5.1 array quirks. */
export function normalizeHardware(raw: unknown): Hardware {
  const r = (raw ?? {}) as Record<string, unknown>;
  let gpuList: unknown = r.gpus;
  if (gpuList && !Array.isArray(gpuList) && Array.isArray((gpuList as { value?: unknown }).value)) gpuList = (gpuList as { value: unknown[] }).value;
  if (gpuList && !Array.isArray(gpuList)) gpuList = [gpuList];
  const gpus: GpuInfo[] = ((gpuList as unknown[] | undefined) ?? [])
    .map((g) => g as Record<string, unknown>)
    .filter((g) => typeof g.name === "string" && g.name.trim() && !NOT_A_GPU.test(g.name.trim()))
    .map((g) => {
      const registry = num(g.registry_vram), adapter = num(g.adapter_ram);
      if (registry) return { name: (g.name as string).trim(), vramGb: registry / GIB, vramAtLeast: false };
      if (adapter) return { name: (g.name as string).trim(), vramGb: adapter / GIB, vramAtLeast: adapter >= 4 * GIB - 1024 * 1024 };
      return { name: (g.name as string).trim(), vramGb: null, vramAtLeast: false };
    });
  return {
    cpuModel: str(r.cpu_model, "Unknown processor"),
    cores: Math.round(num(r.cores)),
    threads: Math.round(num(r.threads)),
    ramGb: num(r.ram_bytes) / GIB,
    gpus,
    os: [str(r.os, "Windows"), typeof r.os_version === "string" ? r.os_version : ""].filter(Boolean).join(" · "),
    hostname: str(r.hostname, ""),
  };
}

export type HardwareDetector = () => Promise<HardwareResult>;

export const inDesktopApp = () => typeof window !== "undefined" && "__TAURI_INTERNALS__" in window;

export const detectHardware: HardwareDetector = async () => {
  if (!inDesktopApp()) {
    return { status: "unavailable", reason: "browser", message: "Hardware details are shown in the installed desktop app." };
  }
  try {
    return { status: "ok", hardware: normalizeHardware(await invoke("detect_hardware")) };
  } catch {
    return { status: "unavailable", reason: "failed", message: "We couldn't read this computer's hardware details." };
  }
};

/** Preliminary, local-only check. The real eligibility decision belongs to GreenTokens. */
export function compatibility(h: Hardware): { ok: boolean; text: string } {
  const ok = h.cores >= 2 && h.ramGb >= 3.5;
  return ok
    ? { ok, text: "Looks compatible (preliminary check)" }
    : { ok, text: "May be below the minimum of 2 processor cores and 4 GB memory" };
}

export function formatGb(gb: number) {
  return gb >= 10 ? `${Math.round(gb)} GB` : `${Math.round(gb * 10) / 10} GB`;
}
