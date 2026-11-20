"use client";

import {
  useCallback,
  useRef,
  useState,
  useSyncExternalStore,
  type FormEvent,
} from "react";

import {
  createInlineSubmission,
  GreenTokensApiError,
  validateValues,
} from "@/lib/api/client";
import type { DevelopmentIdentity, JobStatus, SubmitJobRequest } from "@/lib/api/types";
import {
  isJobId,
  parseRecentJobs,
  recentJobsKey,
  recentJobsUpdatedEvent,
  saveRecentJob,
} from "@/lib/recent-jobs";
import { useDevelopmentSession } from "./development-session";
import Link from "next/link";

const MAX_INPUT_CHARACTERS = 16_000;
const MAX_VALUES = 1_000;
const JOB_STATUSES = new Set<JobStatus>([
  "QUEUED", "DISPATCHING", "RUNNING", "SUCCEEDED", "FAILED", "CANCELLED",
]);

function isJobStatus(value: unknown): value is JobStatus {
  return typeof value === "string" && JOB_STATUSES.has(value as JobStatus);
}

function parseValues(input: string): number[] {
  if (input.length > MAX_INPUT_CHARACTERS) {
    throw new RangeError("Input is too long");
  }

  const trimmed = input.trim();
  if (!trimmed) throw new RangeError("Enter at least one integer");

  if (/^,|,$|,\s*,/.test(trimmed)) {
    throw new TypeError("Use whole numbers separated by commas or spaces");
  }

  const entries = trimmed.split(/[\s,]+/);
  if (entries.length > MAX_VALUES) {
    throw new RangeError("Enter at most 1,000 integers");
  }
  if (entries.some((entry) => !/^-?\d+$/.test(entry))) {
    throw new TypeError("Use whole numbers separated by commas or spaces");
  }

  const values = entries.map(Number);
  validateValues(values);
  return values;
}

function subscribeToRecentJobs(notify: () => void): () => void {
  window.addEventListener("storage", notify);
  window.addEventListener(recentJobsUpdatedEvent, notify);
  return () => {
    window.removeEventListener("storage", notify);
    window.removeEventListener(recentJobsUpdatedEvent, notify);
  };
}

function useRecentJobs(identity: DevelopmentIdentity): string[] {
  const getSnapshot = useCallback(() => {
    try {
      return window.localStorage.getItem(recentJobsKey(identity)) ?? "[]";
    } catch {
      return "[]";
    }
  }, [identity]);

  const value = useSyncExternalStore(
    subscribeToRecentJobs,
    getSnapshot,
    () => "[]",
  );

  return parseRecentJobs(value);
}

function SubmissionPanel() {
  const { identity, client } = useDevelopmentSession();
  const [input, setInput] = useState("1, 2, 3, 4");
  const [submitting, setSubmitting] = useState(false);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [retryable, setRetryable] = useState(false);
  const [jobId, setJobId] = useState<string | null>(null);
  const [jobStatus, setJobStatus] = useState<string | null>(null);
  const [storageWarning, setStorageWarning] = useState(false);
  const pending = useRef<{ input: string; body: SubmitJobRequest } | null>(null);
  const submittingRef = useRef(false);
  const recentJobs = useRecentJobs(identity);

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (submittingRef.current) return;
    if (identity === "admin") {
      setErrorMessage("Job submission is unavailable for the admin identity.");
      return;
    }

    setErrorMessage(null);
    setJobId(null);
    setJobStatus(null);
    setStorageWarning(false);

    try {
      const values = parseValues(input);
      const body = pending.current?.input === input
        ? pending.current.body
        : createInlineSubmission(values);
      pending.current = { input, body };

      submittingRef.current = true;
      setSubmitting(true);
      const result = await client.submitJob(body);
      if (!result || typeof result.job_id !== "string" || !isJobId(result.job_id)) {
        throw new Error("API response did not contain a valid job ID");
      }
      if (!isJobStatus(result.status)) {
        throw new Error("API response did not contain a job status");
      }

      pending.current = null;
      setRetryable(false);
      const saved = saveRecentJob(identity, result.job_id);
      setStorageWarning(!saved);
      setJobId(result.job_id);
      setJobStatus(result.status);
    } catch (error) {
      if (error instanceof Error && error.name === "AbortError") return;

      const definitiveRejection = error instanceof GreenTokensApiError
        && error.status >= 400 && error.status < 500;
      if (definitiveRejection) pending.current = null;
      setRetryable(!definitiveRejection && pending.current !== null);

      const message = error instanceof GreenTokensApiError
        ? error.detail
        : error instanceof Error ? error.message : "Submission failed";
      setErrorMessage(message);
    } finally {
      submittingRef.current = false;
      setSubmitting(false);
    }
  }

  function changeInput(value: string) {
    setInput(value);
    pending.current = null;
    setRetryable(false);
    setErrorMessage(null);
    setJobId(null);
    setJobStatus(null);
    setStorageWarning(false);
  }

  return (
    <div className="grid gap-6 lg:grid-cols-[minmax(0,1.5fr)_minmax(260px,1fr)]">
      <section className="rounded-xl border border-zinc-200 bg-white p-6 shadow-sm dark:border-zinc-800 dark:bg-zinc-950">
        <h2 className="text-lg font-semibold">New job</h2>
        <p className="mt-1 text-sm text-zinc-600 dark:text-zinc-400">
          Submit an inline integer array using the supported CPU template.
        </p>
        <form onSubmit={submit} className="mt-5 space-y-4" aria-busy={submitting}>
          <div>
            <label htmlFor="job-values" className="block text-sm font-medium">
              Integer values
            </label>
            <textarea
              id="job-values"
              value={input}
              onChange={(event) => changeInput(event.target.value)}
              rows={3}
              maxLength={MAX_INPUT_CHARACTERS}
              spellCheck={false}
              disabled={submitting || identity === "admin"}
              aria-describedby="values-help"
              className="mt-2 w-full rounded-lg border border-zinc-300 bg-transparent p-3 font-mono text-sm outline-offset-2 focus-visible:outline-2 focus-visible:outline-emerald-600 dark:border-zinc-700"
            />
            <p id="values-help" className="mt-1 text-xs text-zinc-500 dark:text-zinc-400">
              1 to 1,000 integers, each between -1,000,000,000 and 1,000,000,000.
            </p>
          </div>

          <div className="rounded-lg bg-zinc-50 px-4 py-3 text-sm dark:bg-zinc-900">
            <p className="font-medium">sum_numbers_v1</p>
            <p className="mt-1 text-zinc-600 dark:text-zinc-400">
              1 CPU · 0.125 GB RAM · 0 GPUs · 60-second limit
            </p>
          </div>

          <button
            type="submit"
            disabled={submitting || identity === "admin"}
            className="rounded-lg bg-emerald-700 px-5 py-2.5 text-sm font-medium text-white hover:bg-emerald-800 focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-emerald-600 disabled:cursor-not-allowed disabled:opacity-60"
          >
            {submitting ? "Submitting..." : retryable ? "Retry submission" : "Submit job"}
          </button>

          {retryable && (
            <p className="text-xs text-zinc-600 dark:text-zinc-400">
              Retry sends the same request and idempotency key to avoid creating a duplicate job.
            </p>
          )}
          {errorMessage && (
            <p role="alert" className="text-sm text-red-700 dark:text-red-400">
              {errorMessage}
            </p>
          )}
          {jobId && (
            <div
              role="status"
              className="rounded-lg border border-emerald-200 bg-emerald-50 p-3 text-sm dark:border-emerald-900 dark:bg-emerald-950"
            >
              <p className="font-medium">Job accepted: {jobStatus}</p>
              <Link href={`/jobs/${jobId}`} className="mt-1 block break-all font-mono text-xs underline underline-offset-2">{jobId}</Link>
              {storageWarning && (
                <p className="mt-2 text-sm text-amber-800 dark:text-amber-300">
                  This browser could not save the job ID. Copy it before leaving this page.
                </p>
              )}
            </div>
          )}
        </form>
      </section>

      <section className="rounded-xl border border-zinc-200 bg-white p-6 shadow-sm dark:border-zinc-800 dark:bg-zinc-950">
        <h2 className="text-lg font-semibold">Recent jobs on this browser</h2>
        <p className="mt-1 text-sm text-zinc-600 dark:text-zinc-400">
          Saved job IDs for the selected development identity. This is not complete job history.
        </p>
        {recentJobs.length === 0 ? (
          <p className="mt-5 text-sm text-zinc-500">
            No submitted jobs saved for this identity.
          </p>
        ) : (
          <ul className="mt-5 space-y-3">
            {recentJobs.map((id) => (
              <li
                key={id}
                className="break-all rounded-lg bg-zinc-50 p-3 font-mono text-xs dark:bg-zinc-900"
              >
                <Link href={`/jobs/${id}`} className="underline underline-offset-2">
                  {id}
                </Link>
              </li>
            ))}
          </ul>
        )}
      </section>
    </div>
  );
}

function IdentitySelector() {
  const { identity, selectIdentity } = useDevelopmentSession();

  return (
    <div className="flex flex-wrap items-center gap-3">
      <label htmlFor="dev-identity" className="text-sm font-medium">
        Development identity
      </label>
      <select
        id="dev-identity"
        value={identity}
        onChange={(event) => {
          const value = event.target.value;
          if (value === "alice" || value === "bob" || value === "admin") {
            selectIdentity(value);
          }
        }}
        className="rounded-lg border border-zinc-300 bg-white px-3 py-2 text-sm outline-offset-2 focus-visible:outline-2 focus-visible:outline-emerald-600 dark:border-zinc-700 dark:bg-zinc-900"
      >
        <option value="alice">alice (org-a)</option>
        <option value="bob">bob (org-b)</option>
        <option value="admin">admin (diagnostics)</option>
      </select>
    </div>
  );
}

function ConsoleContent() {
  const { identity } = useDevelopmentSession();

  return (
    <main className="mx-auto max-w-6xl px-5 py-8 sm:px-8">
      <header className="mb-9 flex flex-wrap items-center justify-between gap-5">
        <div>
          <p className="text-sm font-semibold tracking-wide text-emerald-700 dark:text-emerald-400">
            GREENTOKENS
          </p>
          <h1 className="mt-1 text-3xl font-semibold tracking-tight">
            Customer dashboard
          </h1>
        </div>
        <IdentitySelector />
      </header>

      <div className="mb-7 rounded-lg border border-amber-200 bg-amber-50 px-4 py-3 text-sm text-amber-950 dark:border-amber-900 dark:bg-amber-950 dark:text-amber-100">
        <div className="flex flex-wrap items-center gap-2">
          <strong>Local development - identity stub</strong>
          <span className="rounded bg-amber-100 px-2 py-0.5 text-xs font-semibold dark:bg-amber-900">
            Live API
          </span>
        </div>
        <p className="mt-1">
          Development identities are not secure authentication. Job submission requires the
          local FastAPI backend at 127.0.0.1:8000.
        </p>
      </div>

      <SubmissionPanel key={identity} />
    </main>
  );
}

export function CustomerConsole() {
  return <ConsoleContent />;
}
