import { Loader2, Pause, Play } from "lucide-react";
import { useEffect, useState } from "react";
import { useProvider } from "../hooks/useProvider";
import { formatGb } from "../services/hardware";
import { Button, Card, DemoBadge, NotEnforced, Toggle } from "../components/ui";
import type { Participation, Preferences } from "../types/provider";

const STATUS: Record<Participation, { title: string; detail: string; tone: string }> = {
  paused: { title: "Paused", detail: "Your computer is not available for jobs.", tone: "border-slate-300 bg-slate-50" },
  starting: { title: "Starting…", detail: "Waiting for GreenTokens to confirm.", tone: "border-amber-300 bg-amber-50" },
  active: { title: "Your computer is available for jobs", detail: "Demo: no real jobs run on this computer.", tone: "border-emerald-300 bg-emerald-50" },
  pausing: { title: "Pausing…", detail: "No new jobs will be accepted.", tone: "border-amber-300 bg-amber-50" },
};

export function ControlScreen() {
  const { participation, start, pause, controlError, preferences, savePreferences, hardware, activity } = useProvider();
  const status = STATUS[participation];
  const busy = participation === "starting" || participation === "pausing";

  return (
    <div className="space-y-6">
      <header>
        <h1 className="text-2xl font-semibold">Computing</h1>
        <p className="text-slate-600">Decide when your computer helps, and how much it shares.</p>
      </header>

      <section aria-labelledby="status-title" className={`rounded-2xl border-2 p-6 ${status.tone}`}>
        <div className="flex flex-wrap items-start justify-between gap-3">
          <div aria-live="polite">
            <p className="text-sm font-medium uppercase tracking-wide text-slate-500">Current status</p>
            <h2 id="status-title" className="mt-1 text-2xl font-semibold">{status.title}</h2>
            <p className="text-slate-700">{status.detail}</p>
            {participation === "active" && activity?.currentJob && <p className="mt-1 text-sm text-slate-600">Working on: {activity.currentJob.name} (demo)</p>}
          </div>
          <DemoBadge label="Demo: simulated" />
        </div>
        <div className="mt-6 grid gap-3 sm:grid-cols-2">
          <Button variant="primary" className="py-4 text-lg" disabled={participation !== "paused"} onClick={() => void start()}>
            {participation === "starting" ? <Loader2 className="h-5 w-5 animate-spin" aria-hidden /> : <Play className="h-5 w-5" aria-hidden />} Start Computing
          </Button>
          <Button className="py-4 text-lg" disabled={participation === "paused" || participation === "pausing"} onClick={() => void pause()}>
            {participation === "pausing" ? <Loader2 className="h-5 w-5 animate-spin" aria-hidden /> : <Pause className="h-5 w-5" aria-hidden />} Pause Computing
          </Button>
        </div>
        {controlError && <p role="alert" className="mt-4 rounded-lg border border-red-200 bg-red-50 p-3 text-sm text-red-800">{controlError}</p>}
        {busy && <p className="sr-only">{status.title}</p>}
      </section>

      <Limits
        initial={preferences}
        ramMax={hardware?.status === "ok" ? Math.max(1, Math.floor(hardware.hardware.ramGb - 2)) : 16}
        hasGpu={hardware?.status === "ok" ? hardware.hardware.gpus.length > 0 : null}
        onSave={savePreferences}
      />

      <Card title="Availability schedule" badge={<span className="text-xs font-medium text-slate-500">Coming later</span>}>
        <fieldset disabled className="opacity-60">
          <legend className="sr-only">Availability schedule</legend>
          <p className="text-sm text-slate-600">Later you'll be able to share only at certain times, for example overnight. For now, use Start and Pause.</p>
        </fieldset>
      </Card>
    </div>
  );
}

function Limits({ initial, ramMax, hasGpu, onSave }: { initial: Preferences; ramMax: number; hasGpu: boolean | null; onSave(p: Preferences): Promise<{ enforced: boolean } | null> }) {
  const [draft, setDraft] = useState(initial);
  const [state, setState] = useState<"idle" | "saving" | "saved" | "error">("idle");
  const ram = Math.min(draft.ramGb, ramMax);
  useEffect(() => { if (state === "saved") { const t = setTimeout(() => setState("idle"), 5000); return () => clearTimeout(t); } }, [state]);
  const dirty = JSON.stringify({ ...draft, ramGb: ram }) !== JSON.stringify(initial);

  async function save() {
    setState("saving");
    const result = await onSave({ ...draft, ramGb: ram });
    setState(result ? "saved" : "error");
  }

  return (
    <Card title="How much to share" badge={<NotEnforced />}>
      <div className="space-y-6">
        <div>
          <label htmlFor="cpu" className="flex justify-between font-medium"><span>Processor (CPU)</span><span>Up to {draft.cpuPercent}%</span></label>
          <input id="cpu" type="range" min={10} max={100} step={10} value={draft.cpuPercent} onChange={(e) => setDraft({ ...draft, cpuPercent: Number(e.target.value) })} className="mt-2 w-full" />
        </div>
        <div>
          <label htmlFor="ram" className="flex justify-between font-medium"><span>Memory (RAM)</span><span>Up to {formatGb(ram)}</span></label>
          <input id="ram" type="range" min={1} max={ramMax} step={1} value={ram} onChange={(e) => setDraft({ ...draft, ramGb: Number(e.target.value) })} className="mt-2 w-full" />
          <p className="mt-1 text-xs text-slate-500">We keep at least 2 GB free for you.</p>
        </div>
        <Toggle id="gpu" label="Share graphics card (GPU)" checked={draft.gpuEnabled && hasGpu !== false} disabled={hasGpu === false}
          description={hasGpu === false ? "No graphics card detected on this computer." : "Off by default. Graphics jobs are not available yet."}
          onChange={(gpuEnabled) => setDraft({ ...draft, gpuEnabled })} />
        <div className="flex flex-wrap items-center gap-3">
          <Button variant="primary" disabled={!dirty || state === "saving"} onClick={() => void save()}>{state === "saving" ? "Saving…" : "Save preferences"}</Button>
          <p aria-live="polite" className="text-sm text-slate-600">
            {state === "saved" && "Saved on this computer. These limits aren't enforced yet: that needs the GreenTokens worker."}
            {state === "error" && <span className="text-red-700">Couldn't save. Please try again.</span>}
          </p>
        </div>
      </div>
    </Card>
  );
}
