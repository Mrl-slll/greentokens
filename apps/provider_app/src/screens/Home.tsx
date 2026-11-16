import { useLiveUsage } from "../hooks/useLiveUsage";
import { Power } from "lucide-react";
import { useEffect, useState } from "react";
import { useProvider } from "../hooks/useProvider";
import { formatGb } from "../services/hardware";
import { Button, formatDuration } from "../components/ui";
import { GroupCard } from "../components/GroupCard";
import type { Participation, Preferences } from "../types/provider";

const LABEL: Record<Participation, { title: string; detail: string }> = {
  paused: { title: "Not connected", detail: "Your computer isn't sharing anything." },
  starting: { title: "Connecting…", detail: "Joining your group. The first time can take a few minutes." },
  active: { title: "Connected", detail: "Your computer is available to your group." },
  pausing: { title: "Disconnecting…", detail: "Leaving the group." },
};

export type Level = "light" | "balanced" | "max";
export function levelLimits(level: Level, ramGb: number | null): Pick<Preferences, "cpuPercent" | "ramGb"> {
  const ramCap = ramGb ? Math.max(1, Math.floor(ramGb - 2)) : 16;
  if (level === "light") return { cpuPercent: 25, ramGb: Math.min(2, ramCap) };
  if (level === "balanced") return { cpuPercent: 50, ramGb: Math.min(4, ramCap) };
  return { cpuPercent: 90, ramGb: ramCap };
}
export function currentLevel(p: Preferences, ramGb: number | null): Level | null {
  for (const level of ["light", "balanced", "max"] as const) {
    const l = levelLimits(level, ramGb);
    if (l.cpuPercent === p.cpuPercent && l.ramGb === p.ramGb) return level;
  }
  return null;
}

export function HomeScreen() {
  const { participation, start, pause, controlError, preferences, savePreferences, hardware, activity, consent, setConsent, service, group, preparing } = useProvider();
  const live = service.mode === "live";
  const [asking, setAsking] = useState(false);
  const ramGb = hardware?.status === "ok" ? hardware.hardware.ramGb : null;
  const label = LABEL[participation];
  const connected = participation === "active";
  const busy = participation === "starting" || participation === "pausing";
  const level = currentLevel(preferences, ramGb);
  const { usage } = useLiveUsage(live && connected);

  // Session timer, like a VPN client.
  const [since, setSince] = useState<number | null>(null);
  const [, tick] = useState(0);
  useEffect(() => { setSince(connected ? Date.now() : null); }, [connected]);
  useEffect(() => { if (!connected) return; const id = setInterval(() => tick((n) => n + 1), 1000); return () => clearInterval(id); }, [connected]);

  const ring = connected ? "bg-emerald-600 text-white shadow-emerald-300 ring-emerald-200"
    : busy ? "bg-amber-400 text-white shadow-amber-200 ring-amber-100 animate-pulse"
    : "bg-white text-slate-500 shadow-slate-200 ring-slate-200 hover:text-emerald-700";

  return (
    <div className="flex flex-col items-center gap-6 text-center">
      <button
        type="button"
        onClick={() => { if (participation !== "paused") void pause(); else if (!consent) setAsking(true); else void start(); }}
        disabled={participation === "pausing" || (participation === "paused" && (!group || preparing))}
        aria-label={participation === "paused" ? "Connect" : "Disconnect"}
        className={`mt-4 flex h-48 w-48 items-center justify-center rounded-full shadow-xl ring-8 transition-colors disabled:cursor-wait ${ring}`}
      >
        <Power className="h-20 w-20" strokeWidth={2.5} aria-hidden />
      </button>

      <div aria-live="polite">
        <h1 className="text-2xl font-semibold">{label.title}</h1>
        <p className="text-slate-600">{label.detail}</p>
        {connected && since !== null && <p className="mt-1 font-mono text-sm text-slate-500">{formatDuration((Date.now() - since) / 1000)}</p>}
        {connected && activity?.currentJob && <p className="mt-1 text-sm text-slate-600">Working on: {activity.currentJob.name}</p>}
        {live && connected && usage && !usage.warmingUp && <p className="mt-1 text-sm text-slate-600">GreenTokens is using {usage.greentokensCpuPercent}% of this computer right now.</p>}
        {connected && activity?.leaderReachable === false && <p className="mt-1 text-sm font-medium text-amber-800">Can't reach the group leader right now.</p>}
        {participation === "paused" && !group && <p className="mt-1 text-sm text-slate-500">Start or join a group below first.</p>}
      </div>
      {asking && !consent && participation === "paused" && (
        <section role="dialog" aria-label="Before you connect" className="w-full rounded-2xl border border-emerald-200 bg-white p-5 text-left shadow-sm">
          <h2 className="font-semibold">Before you connect</h2>
          <p className="mt-1 text-sm text-slate-600">While connected, your group can run computing work on this computer using the processor share you choose. That can use more power and make it feel slower. You can disconnect any time, it never connects by itself, and closing the app disconnects.</p>
          <p className="mt-2 text-sm font-medium text-slate-800">Only connect to groups run by people you trust: the group leader can run programs on this computer while you're connected.</p>
          {!live && <p className="mt-2 text-xs text-slate-500">Demo version: nothing actually runs on your computer.</p>}
          <div className="mt-4 flex gap-2">
            <Button variant="primary" onClick={() => { setConsent(true); setAsking(false); void start({ consented: true }); }}>Agree &amp; Connect</Button>
            <Button onClick={() => setAsking(false)}>Not now</Button>
          </div>
        </section>
      )}
      {controlError && <p role="alert" className="w-full rounded-lg border border-red-200 bg-red-50 p-3 text-sm text-red-800">{controlError}</p>}

      <GroupCard />

      <section className="w-full text-left">
        <h2 className="mb-2 text-sm font-medium text-slate-500">Sharing level</h2>
        <div role="radiogroup" aria-label="Sharing level" className="grid grid-cols-3 gap-2">
          {(["light", "balanced", "max"] as const).map((l) => {
            const limits = levelLimits(l, ramGb);
            const selected = level === l;
            return (
              <button key={l} type="button" role="radio" aria-checked={selected}
                onClick={() => void savePreferences({ ...preferences, ...limits })}
                className={`rounded-xl border p-3 text-left ${selected ? "border-emerald-600 bg-emerald-50" : "border-slate-200 bg-white hover:bg-slate-50"}`}>
                <span className="block font-medium capitalize">{l === "max" ? "Maximum" : l}</span>
                <span className="block text-xs text-slate-500">{limits.cpuPercent}% CPU · {formatGb(limits.ramGb)}</span>
              </button>
            );
          })}
        </div>
        <p className="mt-2 text-xs text-slate-500">{level ? "" : `Custom: ${preferences.cpuPercent}% CPU · ${formatGb(preferences.ramGb)}. `}{live ? "The processor share applies when you connect. Memory limits aren't enforced yet." : "Limits aren't enforced yet in this demo."}</p>
      </section>

      <div className="grid w-full grid-cols-2 gap-2 text-left">
        {live
          ? <div className="rounded-xl border border-slate-200 bg-white p-3"><p className="text-xs text-slate-500">Computers in group</p><p className="text-lg font-semibold">{activity?.groupNodes ?? "–"}</p></div>
          : <div className="rounded-xl border border-slate-200 bg-white p-3"><p className="text-xs text-slate-500">Jobs done</p><p className="text-lg font-semibold">{activity?.completedCount ?? 0}</p></div>}
        <div className="rounded-xl border border-slate-200 bg-white p-3"><p className="text-xs text-slate-500">Time shared</p><p className="text-lg font-semibold">{formatDuration(activity?.totalSeconds ?? 0)}</p></div>
      </div>
    </div>
  );
}
