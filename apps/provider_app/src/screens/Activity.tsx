import { useProvider } from "../hooks/useProvider";
import { Card, DemoBadge, Stat, StatusPill, formatDuration } from "../components/ui";
import { Sparkline } from "../components/Sparkline";
import { useLiveUsage } from "../hooks/useLiveUsage";
import { isTraining } from "../services/usage";
import type { JobStatus } from "../types/provider";

const STATUS_TEXT: Record<JobStatus, string> = { running: "Running", completed: "Completed", stopped: "Stopped by pause" };

export function ActivityScreen() {
  const { activity, participation, service, hardware } = useProvider();
  const live = service.mode === "live";
  const { usage, history, unavailable } = useLiveUsage(live);
  const training = isTraining(usage);
  const gpuCount = hardware?.status === "ok" ? hardware.hardware.gpus.length : null;
  const gpuValue = gpuCount === 0 ? "No GPU found" : usage?.gpuPercent == null ? "Not measured" : `${usage.gpuPercent}%`;
  const gpuNote = gpuCount === 0 ? undefined : usage?.gpuPercent == null ? "Not available on this computer" : "Today's training uses the processor only";
  const measuring = !usage || usage.warmingUp;

  return (
    <div className="space-y-6">
      <header className="flex flex-wrap items-end justify-between gap-3">
        <div>
          <h1 className="text-2xl font-semibold">Activity</h1>
          <p className="text-slate-600">What your computer has done for GreenTokens.</p>
        </div>
        {!live && <DemoBadge label="Demo data: simulated jobs" />}
      </header>

      {!activity ? <Card><p role="status">Loading activity…</p></Card> : (
        <>
          <div className="flex flex-wrap gap-3">
            {live
              ? <StatusPill tone={training ? "good" : participation === "active" ? "neutral" : "warn"}>{training ? "Training a GreenTokens job now" : participation === "active" ? "Connected, waiting for work" : "Not connected"}</StatusPill>
              : <>
                  {activity.connection === "offline"
                    ? <StatusPill tone="bad">Disconnected (simulated)</StatusPill>
                    : <StatusPill tone="warn">Demo mode: not connected to GreenTokens</StatusPill>}
                  <StatusPill tone={participation === "active" ? "good" : "neutral"}>{participation === "active" ? "Available for jobs" : "Paused"}</StatusPill>
                </>}
            {live && activity.leaderReachable === false && <StatusPill tone="warn">Can't reach the group leader</StatusPill>}
          </div>

          {live && unavailable && <p role="note" className="rounded-lg bg-slate-100 px-3 py-2 text-sm text-slate-600">Live usage numbers are shown in the installed app, not in a browser.</p>}
          <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
            {live ? (
              <>
                <div className="rounded-2xl border border-slate-200 bg-white p-4 shadow-sm sm:col-span-2">
                  <p className="text-sm text-slate-500">GreenTokens is using</p>
                  <p className="text-3xl font-semibold" aria-live="off">{measuring ? "–" : `${usage.greentokensCpuPercent}%`}</p>
                  <p className="text-xs text-slate-500">of this computer's processor{usage && !measuring ? ` · ${usage.greentokensProcesses} worker${usage.greentokensProcesses === 1 ? "" : "s"}` : ""} · updates every second</p>
                  <Sparkline values={history} label="GreenTokens processor use over the last minute" />
                </div>
                <Stat label="Whole computer" value={measuring ? "–" : `${usage.cpuPercent}%`} note="Processor, everything running" />
                <Stat label="Memory used" value={measuring ? "–" : `${usage.ramUsedGb} of ${usage.ramTotalGb} GB`} />
                <Stat label="Graphics (GPU)" value={measuring && gpuCount !== 0 ? "–" : gpuValue} note={gpuNote} />
                <Stat label="Computers in group" value={activity.groupNodes ?? "–"} note="Updates about every 10 seconds" />
                <Stat label="Connected for" value={formatDuration(activity.totalSeconds)} />
              </>
            ) : (
              <>
                <Stat label="Current job" value={activity.currentJob ? "1 running" : "None"} note={activity.currentJob?.name} />
                <Stat label="Processor activity" value={`${activity.cpuPercent}%`} note="Simulated" />
                <Stat label="Graphics activity" value={activity.gpuPercent === null ? "Not shared" : `${activity.gpuPercent}%`} note={activity.gpuPercent === null ? undefined : "Simulated"} />
                <Stat label="Completed jobs" value={activity.completedCount} />
                <Stat label="Total computing time" value={formatDuration(activity.totalSeconds)} />
              </>
            )}
            <Stat label="Estimated earnings" value="Unavailable" note="Earnings are not offered during the pilot." />
          </div>

          <Card title="Recent jobs">
            {activity.history.length === 0 && !activity.currentJob ? (
              <p className="text-slate-600">{live ? "Job history arrives in a later version. The live numbers above show work as it happens." : "No jobs yet. Connect to see activity here."}</p>
            ) : (
              <div className="overflow-x-auto">
                <table className="w-full text-left text-sm">
                  <thead className="text-slate-500">
                    <tr><th className="py-2 pr-4 font-medium">Job</th><th className="py-2 pr-4 font-medium">Started</th><th className="py-2 pr-4 font-medium">Duration</th><th className="py-2 font-medium">Result</th></tr>
                  </thead>
                  <tbody>
                    {[...(activity.currentJob ? [activity.currentJob] : []), ...activity.history].map((job) => (
                      <tr key={`${job.id}-${job.status}`} className="border-t border-slate-100">
                        <td className="py-2 pr-4">{job.name}</td>
                        <td className="py-2 pr-4">{new Date(job.startedAt).toLocaleTimeString()}</td>
                        <td className="py-2 pr-4">{job.status === "running" ? "In progress" : formatDuration(job.seconds)}</td>
                        <td className="py-2">{STATUS_TEXT[job.status]}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </Card>
        </>
      )}
    </div>
  );
}
