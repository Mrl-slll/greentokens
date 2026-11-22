"use client";
import { useRef, useState } from "react";
import { useRouter } from "next/navigation";
import { useApp } from "@/components/AppProvider";
import { addRecent, storeFor } from "@/lib/recent";
import { CPU_ONLY, ApiError } from "@/lib/types";
import { newIdempotencyKey, parseInline, parseUpload } from "@/lib/validation";

export default function NewJob() {
  const { client, user, mode } = useApp(), router = useRouter();
  const [text, setText] = useState("1, 2, 3, 4"), [err, setErr] = useState<string | null>(null), [busy, setBusy] = useState(false);
  const file = useRef<HTMLInputElement>(null);
  const key = useRef(newIdempotencyKey()); // reused on retry of the same content; new key after a definite outcome

  async function go(submit: () => Promise<{ job_id: string }>) {
    setBusy(true); setErr(null);
    try { const r = await submit(); addRecent(mode, user, r.job_id, storeFor(mode)); key.current = newIdempotencyKey(); router.push(`/jobs/${r.job_id}`); }
    catch (e) {
      setErr(e instanceof ApiError ? `${e.detail} (HTTP ${e.status})` : "Network error: the outcome is unknown. Press submit again to retry safely with the same key.");
      setBusy(false);
    }
  }
  const inline = (e: React.FormEvent) => { e.preventDefault(); const p = parseInline(text); if (!p.ok) return setErr(p.error);
    go(() => client.submitJob(user, { template_id: "sum_numbers_v1", parameters: { values: p.values }, requirements: CPU_ONLY, idempotency_key: key.current })); };
  const upload = async () => {
    const f = file.current?.files?.[0]; if (!f) return setErr("Choose a .json file first.");
    const raw = await f.text(), p = parseUpload(raw); if (!p.ok) return setErr(p.error);
    // Uploads are NOT idempotent: never auto-retried. A failed/ambiguous upload needs a deliberate new click.
    go(async () => { const a = await client.uploadInput(user, raw); return client.submitJob(user, { template_id: "sum_numbers_v1", input_artifact_id: a.artifact_id, requirements: CPU_ONLY, idempotency_key: newIdempotencyKey() }); });
  };
  return (
    <div className="space-y-6"><h1 className="text-2xl font-semibold">New Job</h1>
      <p className="text-sm text-neutral-600">Template <code>sum_numbers_v1</code> · CPU only: 1 core, 0.125 GB RAM, 0 GPUs, trusted_cpu · {mode === "mock" ? "MOCK mode" : "live mode"}</p>
      {err && <p role="alert" id="err" className="rounded border border-red-300 bg-red-50 p-3 text-red-800">{err}</p>}
      <form onSubmit={inline} className="space-y-3 rounded border bg-white p-4">
        <label htmlFor="vals" className="block font-medium">Numbers (whole numbers, comma or space separated; 1–1000 values)</label>
        <textarea id="vals" value={text} onChange={(e) => setText(e.target.value)} aria-describedby={err ? "err" : undefined} className="w-full rounded border p-2 font-mono" rows={3} />
        <button disabled={busy} className="rounded bg-emerald-700 px-4 py-2 text-white hover:bg-emerald-800 disabled:opacity-50">{busy ? "Submitting…" : "Submit job"}</button>
      </form>
      <div className="space-y-3 rounded border bg-white p-4"><label htmlFor="f" className="block font-medium">Or upload a JSON file, e.g. {`{"values":[1,2,3,4]}`} (max 65,536 bytes)</label>
        <input id="f" ref={file} type="file" accept=".json,application/json" />
        <button type="button" onClick={upload} disabled={busy} className="block rounded border border-emerald-700 px-4 py-2 text-emerald-800 hover:bg-emerald-50 disabled:opacity-50">Upload and submit</button></div>
    </div>);
}
