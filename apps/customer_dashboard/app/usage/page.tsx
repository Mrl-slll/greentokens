"use client";
import { useEffect, useState } from "react";
import { useApp } from "@/components/AppProvider";
import { ApiError, type Usage } from "@/lib/types";

export default function UsagePage() {
  const { client, user, mode } = useApp();
  const [u, setU] = useState<Usage | null>(null), [err, setErr] = useState<string | null>(null);
  useEffect(() => {
    const ac = new AbortController();
    client.getUsage(user, ac.signal).then((x) => { if (!ac.signal.aborted) setU(x); })
      .catch((e) => { if (!ac.signal.aborted) setErr(e instanceof ApiError ? `${e.detail} (HTTP ${e.status})` : "Cannot reach the API."); });
    return () => ac.abort();
  }, [client, user]);
  return (
    <div className="space-y-4"><h1 className="text-2xl font-semibold">Usage</h1>
      {mode === "mock" && <p className="rounded bg-purple-100 p-2 text-sm text-purple-900">MOCK data — not real usage.</p>}
      {err && <p role="alert" className="rounded border border-red-300 bg-red-50 p-3 text-red-800">{err}</p>}
      {!u && !err && <p>Loading…</p>}
      {u && <dl className="grid grid-cols-2 gap-2 rounded border bg-white p-4 text-sm">
        <dt>Attempts</dt><dd className="font-semibold">{u.attempts}</dd>
        <dt>Elapsed attempt time</dt><dd className="font-semibold">{u.wall_seconds} seconds</dd>
        <dt>Billable</dt><dd>No (not billing)</dd><dt>Measurement</dt><dd>{u.measurement}</dd></dl>}
      <p className="text-sm text-neutral-600">This is elapsed time of attempts for your organization. It is not CPU or GPU utilization, and there are no prices, credits or earnings.</p>
    </div>);
}
