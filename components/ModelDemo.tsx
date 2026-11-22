"use client";
import { useState } from "react";

const EXAMPLES = ["A warm, funny, beautifully acted film.", "Dull, predictable, and far too long.", "Not as bad as I expected."];

export function ModelDemo() {
  const [text, setText] = useState("This movie was wonderful.");
  const [busy, setBusy] = useState(false);
  const [result, setResult] = useState<{ label: string; probability: number; checkpoint?: string } | null>(null);
  const [error, setError] = useState("");
  async function predict(e: React.FormEvent) {
    e.preventDefault(); setBusy(true); setResult(null); setError("");
    try {
      const response = await fetch("/api/demo/predict", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ text }) });
      const data = await response.json();
      if (!response.ok) throw new Error(data.error);
      setResult(data);
    } catch (e) { setError(e instanceof Error ? e.message : "Prediction unavailable"); }
    finally { setBusy(false); }
  }
  return <form onSubmit={predict} className="space-y-4">
    <label htmlFor="sentence" className="block text-sm font-medium">Type an English movie review</label>
    <textarea id="sentence" className="w-full rounded-lg border border-slate-300 bg-white p-3 text-slate-900" rows={2} maxLength={1000} required value={text} onChange={e => { setText(e.target.value); setResult(null); }} disabled={busy} />
    <div className="flex flex-wrap gap-2">{EXAMPLES.map(example => <button key={example} type="button" disabled={busy} onClick={() => { setText(example); setResult(null); }} className="rounded-full border border-slate-300 px-3 py-1 text-xs text-slate-700 hover:bg-slate-100 disabled:opacity-60">{example}</button>)}</div>
    <button disabled={busy} className="rounded-lg bg-emerald-700 px-5 py-3 font-medium text-white disabled:opacity-60">{busy ? "Running your saved model on the CPU…" : "Run live prediction"}</button>
    <div aria-live="polite">{result && <p className="rounded-lg border border-emerald-300 bg-emerald-50 p-4 text-emerald-950"><strong>{result.label}</strong> · model score {(result.probability * 100).toFixed(1)}%<span className="mt-1 block text-sm">Computed now from the saved checkpoint{result.checkpoint ? ` ${result.checkpoint}` : ""}. This score is not validation accuracy.</span></p>}
    {error && <p role="alert" className="text-red-700">{error}</p>}</div>
    <p className="text-xs text-slate-500">Real local inference, not a simulated response. First load can take up to 90 seconds. A small model can make mistakes.</p>
  </form>;
}
