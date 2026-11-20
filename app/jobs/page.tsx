"use client";
import { useState } from "react";
import { useRouter } from "next/navigation";
import { RecentJobs } from "@/components/RecentJobs";
export default function Jobs() {
  const [id, setId] = useState("");
  const router = useRouter();
  return <div className="space-y-6"><h1 className="text-2xl font-semibold">Jobs</h1>
    <form className="space-y-3 rounded border bg-white p-4" onSubmit={e => { e.preventDefault(); router.push(`/jobs/${id.trim()}`); }}>
      <label className="block" htmlFor="job-id">Open a job submitted from Python or the CLI</label>
      <p className="text-sm text-neutral-600">Select Live in Settings and the same identity used for submission. CLI jobs do not automatically enter this browser&apos;s recent list.</p>
      <input id="job-id" required pattern="[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}" value={id} onChange={e => setId(e.target.value)} placeholder="Job ID" className="w-full rounded border p-2 font-mono text-sm" />
      <button className="rounded border px-4 py-2">Open job</button>
    </form><RecentJobs /></div>;
}
