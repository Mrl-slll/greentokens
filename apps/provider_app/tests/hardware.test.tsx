import { expect, it } from "vitest";
import { compatibility, normalizeHardware } from "../src/services/hardware";
import { createMockProviderService } from "../src/services/mockProviderService";

const GIB = 1024 ** 3;

it("normalizes real detection output from this repo's development PC", () => {
  const h = normalizeHardware({ cpu_model: "AMD Ryzen 7 PRO 5850U with Radeon Graphics", cores: 8, threads: 16, ram_bytes: 15919939584,
    os: "Microsoft Windows 11 Pro", os_version: "10.0.26200", hostname: "PC1",
    gpus: [{ name: "AMD Radeon(TM) Graphics", adapter_ram: GIB, registry_vram: GIB }] });
  expect(h.cores).toBe(8);
  expect(Math.round(h.ramGb)).toBe(15);
  expect(h.gpus).toEqual([{ name: "AMD Radeon(TM) Graphics", vramGb: 1, vramAtLeast: false }]);
  expect(compatibility(h).ok).toBe(true);
});

it("prefers registry VRAM over the 4 GB-capped WMI value, and flags the cap otherwise", () => {
  const h = normalizeHardware({ gpus: [
    { name: "Big GPU", adapter_ram: 4 * GIB - 1, registry_vram: 12 * GIB },
    { name: "Capped GPU", adapter_ram: 4 * GIB - 1, registry_vram: null },
  ] });
  expect(h.gpus[0]).toEqual({ name: "Big GPU", vramGb: 12, vramAtLeast: false });
  expect(h.gpus[1].vramAtLeast).toBe(true);
});

it("handles PowerShell 5.1 array shapes and drops software display adapters", () => {
  expect(normalizeHardware({ gpus: { value: [{ name: "Wrapped GPU" }], Count: 1 } }).gpus[0].name).toBe("Wrapped GPU");
  expect(normalizeHardware({ gpus: { name: "Single GPU" } }).gpus[0].name).toBe("Single GPU");
  expect(normalizeHardware({ gpus: [{ name: "Microsoft Basic Display Adapter" }] }).gpus).toEqual([]);
  expect(normalizeHardware(null).cpuModel).toBe("Unknown processor");
});

it("mock stops accepting jobs immediately on pause", async () => {
  let t = 0;
  const service = createMockProviderService({ delayMs: 0, now: () => t });
  await service.start({ cpuPercent: 50, ramGb: 4, gpuEnabled: false, notifications: true, deviceName: "" });
  t = 20_000;
  const busy = await service.getActivity();
  expect(busy.completedCount).toBeGreaterThan(0);
  expect(busy.currentJob).not.toBeNull();
  await service.pause();
  t = 60_000;
  const after = await service.getActivity();
  expect(after.currentJob).toBeNull();
  expect(after.completedCount).toBe(busy.completedCount);
  expect(after.history[0].status).toBe("stopped");
});
