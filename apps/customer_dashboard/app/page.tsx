import Link from "next/link";
import { RecentJobs } from "@/components/RecentJobs";
export default function Dashboard() {
  return <div className="space-y-6"><h1 className="text-2xl font-semibold">Dashboard</h1>
    <Link href="/jobs/new" className="inline-block rounded bg-emerald-700 px-4 py-2 text-white hover:bg-emerald-800">New job</Link>
    <RecentJobs limit={5} /></div>;
}
