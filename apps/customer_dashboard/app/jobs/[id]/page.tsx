"use client";
import Link from "next/link";
import { useParams } from "next/navigation";
import { useCallback, useEffect, useState } from "react";
import { useApp } from "@/components/AppProvider";
import { ApiError, TERMINAL, type JobDetail, type JobResult } from "@/lib/types";

export default function JobPage() {
  const { id } = useParams<{ id: string }>(), { client, user, mode } = useApp();
  const [job, setJob] = useState<JobDetail | null>(null), [res, setRes] = useState<JobResult | null>(null);
  const [err, setErr] = useState<string | null>(null), [note, setNote] = useState<string | null>(null);

  useEffect(() => {
    const ac = new AbortController(); let timer: ReturnType<typeof setTimeout>, fails = 0, done = false;
    const getResult = async () => {
      try { setRes(await client.getResult(user, id, ac.signal)); setNote(null); }
      catch (e) { if (ac.signal.aborted) return;
        setNote(e instanceof ApiError ? (e.status === 410 ? "Result expired. The job is still SUCCEEDED." : `Result unavailable: ${e.detail} (HTTP ${e.status})`) : "Could not fetch the result (network)."); }
    };
    const tick = async () => {
      try {
        const j = await client.getJob(user, id, ac.signal); if (ac.signal.aborted) return;
        fails = 0; setErr(null); setJob(j);
        if (TERMINAL.includes(j.status)) { done = true; if (j.status === "SUCCEEDED") await getResult(); return; }
      } catch (e) {
        if (ac.signal.aborted) return;
        if (e instanceof ApiError) { setErr(e.status === 404 ? (client.mode === "mock" ? "This mock job no longer exists. Mock data resets on reload or when you switch modes." : "Job not found for this identity (404).") : `${e.detail} (HTTP ${e.status})`); if (e.status === 404) return; }
        else { fails++; setErr("Cannot reach the API. Retrying; your job ID is kept."); }
      }
      if (!done) timer = setTimeout(tick, Math.min(2000 * 1.5 ** fails, 10000));
    };
    tick();
    return () => { ac.abort(); clearTimeout(timer); };
  }, [client, user, id]);

  const cancel = useCallback(async () => {
    try { const c = await client.cancelJob(user, id); setNote(c.cancel_requested ? "Cancellation requested. Waiting for the backend to confirm." : null); setJob((j) => j && { ...j, status: c.status, cancel_requested: c.cancel_requested }); }
    catch (e) { setNote(e instanceof ApiError ? `${e.detail} (HTTP ${e.status})` : "Network error while cancelling."); }
  }, [client, user, id]);

  return (
    <div className="space-y-4" aria-live="polite"><h1 className="text-2xl font-semibold">Job Details</h1>
      <p className="font-mono text-sm break-all">{id}</p>
      <Link className="text-sm underline" href={`/jobs/${id}/results`}>Results and downloads</Link>
      {mode === "mock" && <p className="rounded bg-purple-100 p-2 text-sm text-purple-900">MOCK data — not real execution.</p>}
      {err && <p role="alert" className="rounded border border-red-300 bg-red-50 p-3 text-red-800">{err}</p>}
      {note && <p className="rounded border bg-white p-3">{note}</p>}
      {!job && !err && <p>Loading job…</p>}
      {job && <dl className="grid grid-cols-2 gap-2 rounded border bg-white p-4 text-sm">
        <dt>Status</dt><dd className="font-semibold">{job.status}{job.cancel_requested && !TERMINAL.includes(job.status) ? " (cancellation requested)" : ""}</dd>
        <dt>Created (UTC → local)</dt><dd>{new Date(job.created_at).toLocaleString()}</dd>
        <dt>Attempts</dt><dd>{job.attempt_count}</dd>
        <dt>Error code</dt><dd>{job.error_code ?? "none"}</dd></dl>}
      {job && !TERMINAL.includes(job.status) && <button onClick={cancel} className="rounded border border-red-700 px-4 py-2 text-red-800 hover:bg-red-50">Request cancellation</button>}
      {res && <section className="rounded border border-emerald-300 bg-emerald-50 p-4"><h2 className="font-semibold">Result</h2><p className="text-3xl font-bold" data-testid="result">{res.result}</p></section>}
    </div>);
}
