import { Cpu, Gpu, MemoryStick, Monitor, RefreshCw } from "lucide-react";
import type { ReactNode } from "react";
import { useProvider } from "../hooks/useProvider";
import { compatibility, formatGb } from "../services/hardware";
import { Button, Card, RealBadge, StatusPill } from "../components/ui";
import type { GpuInfo } from "../types/provider";

export function HardwareScreen({ onContinue }: { onContinue(): void }) {
  const { hardware, refreshHardware } = useProvider();

  return (
    <div className="space-y-6">
      <header>
        <h1 className="text-2xl font-semibold">Your computer</h1>
        <p className="text-slate-600">What GreenTokens would be able to use on this PC.</p>
      </header>

      {hardware === null && <Card><p role="status">Checking your hardware…</p></Card>}

      {hardware?.status === "unavailable" && (
        <Card>
          <p role="status" className="font-medium">{hardware.message}</p>
          <p className="mt-1 text-sm text-slate-600">{hardware.reason === "browser" ? "You're viewing a browser preview of the app." : "You can still continue; GreenTokens will check compatibility later."}</p>
          {hardware.reason === "failed" && <Button className="mt-4" onClick={refreshHardware}><RefreshCw className="h-4 w-4" aria-hidden /> Try again</Button>}
        </Card>
      )}

      {hardware?.status === "ok" && (() => {
        const h = hardware.hardware;
        const compat = compatibility(h);
        return (
          <>
            <div className="flex flex-wrap items-center gap-3">
              <StatusPill tone={compat.ok ? "good" : "warn"}>{compat.text}</StatusPill>
              <RealBadge label="Detected by this app on this PC" />
            </div>
            <div className="grid gap-4 md:grid-cols-2">
              <Item icon={<Cpu aria-hidden />} title="Processor" lines={[h.cpuModel, `${h.cores} cores · ${h.threads} threads`]} />
              <Item icon={<MemoryStick aria-hidden />} title="Memory (RAM)" lines={[`${formatGb(h.ramGb)} installed`]} />
              <Item icon={<Gpu aria-hidden />} title="Graphics" lines={h.gpus.length ? h.gpus.map(gpuLine) : ["No graphics card detected. That's fine: GreenTokens can use the processor."]} />
              <Item icon={<Monitor aria-hidden />} title="System" lines={[h.os, h.hostname ? `Computer name: ${h.hostname}` : ""].filter(Boolean)} />
            </div>
            <p className="text-sm text-slate-500">Graphics card memory (VRAM) is separate from system memory. Eligibility for real jobs will be decided by GreenTokens.</p>
          </>
        );
      })()}

      <Button variant="primary" onClick={onContinue}>Back to Home</Button>
    </div>
  );
}

function gpuLine(g: GpuInfo) {
  if (g.vramGb === null) return `${g.name} · memory not reported`;
  return `${g.name} · ${g.vramAtLeast ? "4 GB or more" : formatGb(g.vramGb)} graphics memory`;
}

function Item({ icon, title, lines }: { icon: ReactNode; title: string; lines: string[] }) {
  return (
    <Card>
      <div className="flex items-start gap-4">
        <span className="rounded-xl bg-emerald-50 p-3 text-emerald-700 [&>svg]:h-6 [&>svg]:w-6">{icon}</span>
        <div>
          <h2 className="font-semibold">{title}</h2>
          {lines.map((l) => <p key={l} className="text-slate-700">{l}</p>)}
        </div>
      </div>
    </Card>
  );
}
