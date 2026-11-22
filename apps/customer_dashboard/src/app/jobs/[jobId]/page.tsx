import Link from "next/link";

export const instant = false;
import { notFound } from "next/navigation";

const UUID_PATTERN = /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i;

type JobPageProps = {
  params: Promise<{ jobId: string }>;
};

export default async function JobPage({ params }: JobPageProps) {
  const { jobId } = await params;
  if (!UUID_PATTERN.test(jobId)) notFound();

  return (
    <main className="mx-auto w-full max-w-4xl px-5 py-8 sm:px-8">
      <Link href="/" className="text-sm font-medium text-emerald-700 underline underline-offset-2 dark:text-emerald-400">
        Back to dashboard
      </Link>
      <h1 className="mt-6 text-3xl font-semibold tracking-tight">Job details</h1>
      <p className="mt-3 break-all font-mono text-sm text-zinc-600 dark:text-zinc-400">{jobId}</p>
      <section className="mt-7 rounded-xl border border-zinc-200 bg-white p-6 dark:border-zinc-800 dark:bg-zinc-950">
        <h2 className="font-semibold">Job details are not connected yet</h2>
        <p className="mt-2 text-sm text-zinc-600 dark:text-zinc-400">
          This page establishes the job-detail route. Status, attempts, results, logs, and cancellation
          will appear after the job-detail component is integrated. The job ID shown here has not been
          verified against the API.
        </p>
      </section>
    </main>
  );
}
