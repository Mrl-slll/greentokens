import type { DevelopmentIdentity } from "@/lib/api/types";

const STORAGE_PREFIX = "greentokens:recent-jobs:";
const STORAGE_EVENT = "greentokens:recent-jobs-updated";
const MAX_RECENT_JOBS = 20;
const UUID_PATTERN = /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i;

export const recentJobsUpdatedEvent = STORAGE_EVENT;

export function isJobId(value: string): boolean {
  return UUID_PATTERN.test(value);
}

export function recentJobsKey(identity: DevelopmentIdentity): string {
  return `${STORAGE_PREFIX}${identity}`;
}

export function parseRecentJobs(value: string | null): string[] {
  try {
    const parsed: unknown = JSON.parse(value ?? "[]");
    if (!Array.isArray(parsed)) return [];

    const ids = parsed.filter(
      (item): item is string => typeof item === "string" && isJobId(item),
    );
    return [...new Set(ids)].slice(0, MAX_RECENT_JOBS);
  } catch {
    return [];
  }
}

export function readRecentJobs(identity: DevelopmentIdentity): string[] {
  if (typeof window === "undefined") return [];

  try {
    return parseRecentJobs(window.localStorage.getItem(recentJobsKey(identity)));
  } catch {
    return [];
  }
}

export function saveRecentJob(identity: DevelopmentIdentity, jobId: string): boolean {
  if (typeof window === "undefined" || !isJobId(jobId)) return false;

  const ids = [jobId, ...readRecentJobs(identity).filter((id) => id !== jobId)]
    .slice(0, MAX_RECENT_JOBS);

  try {
    window.localStorage.setItem(recentJobsKey(identity), JSON.stringify(ids));
    window.dispatchEvent(new Event(STORAGE_EVENT));
    return true;
  } catch {
    return false;
  }
}
