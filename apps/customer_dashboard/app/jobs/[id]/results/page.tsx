"use client";
import Link from "next/link";
import { useParams } from "next/navigation";
import { useEffect, useState } from "react";
import { useApp } from "@/components/AppProvider";
import { safeFilename, saveText } from "@/lib/download";
import { ApiError, type ArtifactSummary, type JobDetail, type JobResult } from "@/lib/types";

const why = (e: unknown) => e instanceof ApiError
  ? e.status === 410 ? "This artifact has expired (HTTP 410). The job itself is still SUCCEEDED."
  : e.status === 502 ? "The backend could not read this artifact (HTTP 502)."
  : e.status === 404 ? "Not found for this identity (HTTP 404)."
  : e.status === 409 ? "No successful result for this job yet (HTTP 409)."
  : `${e.detail} (HTTP ${e.status})` : "Cannot reach the API. Nothing was lost; try again.";

export default function Results() {
  const { id } = useParams<{ id: string }>(), { client, user, mode } = useApp();
  const [job, setJob] = useState<JobDetail | null>(null), [res, setRes] = useState<JobResult | null>(null);
  const [msg, setMsg] = useState<string | null>(null), [log, setLog] = useState<string | null>(null), [loading, setLoading] = useState(true);

  useEffect(() => {
    const ac = new AbortController();
    (async () => {
      try {
        const j = await client.getJob(user, id, ac.signal); setJob(j);
        if (j.status === "SUCCEEDED") { try { setRes(await client.getResult(user, id, ac.signal)); } catch (e) { if (!ac.signal.aborted) setMsg(why(e)); } }
      } catch (e) { if (!ac.signal.aborted) setMsg(why(e)); }
      finally { if (!ac.signal.aborted) setLoading(false); }
    })();
    return () => ac.abort();
  }, [client, user, id]);

  const download = async (a: ArtifactSummary) => { try { const t = await client.getArtifactText(user, a.artifact_id); saveText(t.text, safeFilename(a.kind, a.artifact_id), t.contentType || "text/plain"); setMsg(null); } catch (e) { setMsg(why(e)); } };
  const showLog = async (a: ArtifactSummary) => { try { setLog((await client.getArtifactText(user, a.artifact_id)).text); setMsg(null); } catch (e) { setMsg(why(e)); } };

  return (
    <div className="space-y-4" aria-live="polite"><h1 className="text-2xl font-semibold">Results</h1>
      <p className="font-mono text-sm break-all">{id}</p><Link className="text-sm underline" href={`/jobs/${id}`}>Back to job details</Link>
      {mode === "mock" && <p className="rounded bg-purple-100 p-2 text-sm text-purple-900">MOCK data — not real execution.</p>}
      {loading && <p>Loading…</p>}
      {msg && <p role="alert" className="rounded border border-red-300 bg-red-50 p-3 text-red-800">{msg}</p>}
      {job && job.status !== "SUCCEEDED" && <p className="rounded border bg-white p-3">No result: status is {job.status}. Results exist only after SUCCEEDED.</p>}
      {res && <section className="rounded border border-emerald-300 bg-emerald-50 p-4"><h2 className="font-semibold">Result</h2><p className="text-3xl font-bold" data-testid="result">{res.result}</p></section>}
      {job && job.artifacts.length > 0 && <section className="rounded border bg-white p-4"><h2 className="mb-2 font-semibold">Artifacts</h2>
        <ul className="divide-y">{job.artifacts.map((a) => <li key={a.artifact_id} className="space-y-1 py-3 text-sm">
          <p><strong className="uppercase">{a.kind}</strong> · {a.size_bytes} bytes · expires {new Date(a.expires_at).toLocaleString()}</p>
          <p className="break-all font-mono text-xs">sha256 {a.sha256}</p>
          <div className="flex gap-2"><button onClick={() => download(a)} className="rounded border border-emerald-700 px-3 py-1 text-emerald-800 hover:bg-emerald-50">Download {a.kind}</button>
            {a.kind === "log" && <button onClick={() => showLog(a)} className="rounded border px-3 py-1 hover:bg-neutral-50">View log</button>}</div></li>)}</ul></section>}
      {log !== null && <section><h2 className="mb-1 font-semibold">Log (plain text)</h2><pre className="overflow-auto rounded border bg-white p-3 text-xs whitespace-pre-wrap">{log}</pre></section>}
    </div>);
}
