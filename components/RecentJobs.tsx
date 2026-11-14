"use client";
import Link from "next/link";
import { useEffect, useState } from "react";
import { useApp } from "./AppProvider";
import { loadRecent } from "@/lib/recent";

export function RecentJobs({ limit }: { limit?: number }) {
  const { user, mode } = useApp();
  const [ids, setIds] = useState<string[] | null>(null);
  // eslint-disable-next-line react-hooks/set-state-in-effect -- post-mount localStorage read; re-runs when identity changes
  useEffect(() => { setIds(loadRecent(user, localStorage)); }, [user]);
  if (ids === null) return <p>Loading…</p>;
  const shown = limit ? ids.slice(0, limit) : ids;
  return (
    <section aria-labelledby="rj">
      <h2 id="rj" className="mb-1 text-lg font-semibold">Recent jobs on this browser</h2>
      <p className="mb-3 text-sm text-neutral-600">IDs saved in this browser for “{user}”. This is not full account history{mode === "mock" ? "; mock jobs disappear on reload" : ""}.</p>
      {shown.length === 0 ? <p className="rounded border border-dashed p-4 text-neutral-600">No jobs yet. <Link className="underline" href="/jobs/new">Create one</Link>.</p> :
        <ul className="divide-y rounded border bg-white">{shown.map((id) => <li key={id}><Link className="block p-3 font-mono text-sm hover:bg-neutral-50" href={`/jobs/${id}`}>{id}</Link></li>)}</ul>}
    </section>
  );
}
