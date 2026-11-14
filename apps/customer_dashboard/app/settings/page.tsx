"use client";
import { useApp } from "@/components/AppProvider";
export default function Settings() {
  const { mode, setMode, user } = useApp();
  return <div className="space-y-4"><h1 className="text-2xl font-semibold">Settings</h1>
    <fieldset className="rounded border bg-white p-4"><legend className="px-1 font-medium">Data mode</legend>
      {(["mock", "live"] as const).map((m) => <label key={m} className="mb-2 block"><input type="radio" name="mode" checked={mode === m} onChange={() => setMode(m)} className="mr-2" />
        {m === "mock" ? "Mock — fake in-memory data, backend not needed" : "Live — real local FastAPI via the proxy (needs the local stack running)"}</label>)}</fieldset>
    <p className="text-sm text-neutral-600">Development identity: <strong>{user}</strong> (change it in the top bar). These are nonsecret selectors, not accounts. There is no profile or billing API.</p></div>;
}
