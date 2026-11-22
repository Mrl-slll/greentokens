"use client";
import { useEffect, useRef, useState } from "react";
import { useRouter } from "next/navigation";
import { useApp } from "@/components/AppProvider";
import { addRecent } from "@/lib/recent";
import { CPU_ONLY, ApiError } from "@/lib/types";
import { newIdempotencyKey, parseInline, parseUpload } from "@/lib/validation";

export default function NewJob() {
  const { client, user, mode } = useApp(), router = useRouter();
  const [text, setText] = useState("1, 2, 3, 4"), [err, setErr] = useState<string | null>(null), [busy, setBusy] = useState(false);
  const file = useRef<HTMLInputElement>(null);
  const pending = useRef<{ content: string; key: string; artifactId?: string } | null>(null);
  const controller = useRef<AbortController | null>(null);
  const active = useRef(true);
  useEffect(() => { active.current = true; return () => { active.current = false; controller.current?.abort(); }; }, []);
  function requestFor(content: string) {
    if (pending.current?.content !== content) pending.current = { content, key: newIdempotencyKey() };
    return pending.current;
  }

  async function go(submit: (signal: AbortSignal) => Promise<{ job_id: string }>) {
    if (busy || user === "admin") return;
    controller.current = new AbortController();
    setBusy(true); setErr(null);
    try { const r = await submit(controller.current.signal); if (!active.current) return; addRecent(user, r.job_id, localStorage); pending.current = null; router.push(`/jobs/${r.job_id}`); }
    catch (e) {
      if (!active.current) return;
      setErr(e instanceof ApiError ? `${e.detail} (HTTP ${e.status})` : "Network error: the outcome is unknown. Press submit again to retry safely with the same key.");
      setBusy(false);
    }
  }
  const inline = (e: React.FormEvent) => { e.preventDefault(); const p = parseInline(text); if (!p.ok) return setErr(p.error);
    const request = requestFor(`inline:${JSON.stringify(p.values)}`);
    go((signal) => client.submitJob(user, { template_id: "sum_numbers_v1", parameters: { values: p.values }, requirements: CPU_ONLY, idempotency_key: request.key }, signal)); };
  const upload = async () => {
    const f = file.current?.files?.[0]; if (!f) return setErr("Choose a .json file first.");
    if (f.size > 65_536) return setErr("File is larger than 65,536 bytes.");
    let raw: string;
    try { raw = await f.text(); } catch { return setErr("Could not read the file."); }
    if (!active.current) return;
    const p = parseUpload(raw); if (!p.ok) return setErr(p.error);
    // Uploads are NOT idempotent: never auto-retried. A failed/ambiguous upload needs a deliberate new click.
    const request = requestFor(`upload:${raw}`);
    go(async (signal) => {
      if (!request.artifactId) request.artifactId = (await client.uploadInput(user, raw, signal)).artifact_id;
      return client.submitJob(user, { template_id: "sum_numbers_v1", input_artifact_id: request.artifactId, requirements: CPU_ONLY, idempotency_key: request.key }, signal);
    });
  };
  return (
    <div className="space-y-6"><h1 className="text-2xl font-semibold">Test your connection</h1>
      <p className="text-sm text-neutral-600">Template <code>sum_numbers_v1</code> · CPU only: 1 core, 0.125 GB RAM, 0 GPUs, trusted_cpu · {mode === "mock" ? "MOCK mode" : "live mode"}</p>
      {user === "admin" && <p>Admin is for diagnostics. Select alice or bob to submit a job.</p>}
      {err && <p role="alert" id="err" className="rounded border border-red-300 bg-red-50 p-3 text-red-800">{err}</p>}
      <form onSubmit={inline} className="space-y-3 rounded border bg-white p-4">
        <label htmlFor="vals" className="block font-medium">Numbers (whole numbers, comma or space separated; 1–1000 values)</label>
        <textarea id="vals" value={text} onChange={(e) => setText(e.target.value)} aria-describedby={err ? "err" : undefined} className="w-full rounded border p-2 font-mono" rows={3} />
        <button disabled={busy || user === "admin"} className="rounded bg-emerald-700 px-4 py-2 text-white hover:bg-emerald-800 disabled:opacity-50">{busy ? "Submitting…" : "Submit job"}</button>
      </form>
      <div className="space-y-3 rounded border bg-white p-4"><label htmlFor="f" className="block font-medium">Or upload a JSON file, e.g. {`{"values":[1,2,3,4]}`} (max 65,536 bytes)</label>
        <input id="f" ref={file} type="file" accept=".json,application/json" />
        <button type="button" onClick={upload} disabled={busy || user === "admin"} className="block rounded border border-emerald-700 px-4 py-2 text-emerald-800 hover:bg-emerald-50 disabled:opacity-50">Upload and submit</button></div>
    </div>);
}
