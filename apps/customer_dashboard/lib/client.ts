import { ApiError, type CancelResponse, type DevUser, type JobDetail, type JobResult, type SubmitJobRequest, type SubmitJobResponse, type UploadResponse, type Usage } from "./types";

export type Mode = "mock" | "live";
export interface ApiClient {
  readonly mode: Mode;
  submitJob(user: DevUser, body: SubmitJobRequest, signal?: AbortSignal): Promise<SubmitJobResponse>;
  getJob(user: DevUser, id: string, signal?: AbortSignal): Promise<JobDetail>;
  getResult(user: DevUser, id: string, signal?: AbortSignal): Promise<JobResult>;
  cancelJob(user: DevUser, id: string, signal?: AbortSignal): Promise<CancelResponse>;
  uploadInput(user: DevUser, rawJson: string, signal?: AbortSignal): Promise<UploadResponse>;
  getArtifactText(user: DevUser, id: string, signal?: AbortSignal): Promise<{ text: string; contentType: string }>;
  getUsage(user: DevUser, signal?: AbortSignal): Promise<Usage>;
}

/** API timestamps are UTC even without a suffix (handoff §13). Null stays null. */
export function utc(ts: string | null): string | null {
  if (!ts) return null;
  return /(Z|[+-]\d\d:?\d\d)$/.test(ts) ? ts : `${ts}Z`;
}
function normalize(j: JobDetail): JobDetail {
  return { ...j, created_at: utc(j.created_at)!, updated_at: utc(j.updated_at)!,
    attempts: j.attempts.map((a) => ({ ...a, started_at: utc(a.started_at), finished_at: utc(a.finished_at) })),
    artifacts: j.artifacts.map((a) => ({ ...a, expires_at: utc(a.expires_at)! })) };
}

async function call(user: DevUser, method: string, path: string, opts: { body?: string; signal?: AbortSignal } = {}): Promise<Response> {
  const res = await fetch(`/api/core/${path}`, { method, headers: { "X-Dev-User": user }, body: opts.body, signal: opts.signal, cache: "no-store" });
  if (!res.ok) {
    let detail = `HTTP ${res.status}`;
    try { const j = await res.json(); if (typeof j.detail === "string") detail = j.detail; } catch { /* keep generic */ }
    throw new ApiError(res.status, detail);
  }
  return res;
}

export const liveClient: ApiClient = {
  mode: "live",
  submitJob: async (u, b, s) => (await call(u, "POST", "v1/jobs", { body: JSON.stringify(b), signal: s })).json(),
  getJob: async (u, id, s) => normalize(await (await call(u, "GET", `v1/jobs/${id}`, { signal: s })).json()),
  getResult: async (u, id, s) => (await call(u, "GET", `v1/jobs/${id}/result`, { signal: s })).json(),
  cancelJob: async (u, id, s) => (await call(u, "POST", `v1/jobs/${id}/cancel`, { signal: s })).json(),
  uploadInput: async (u, raw, s) => (await call(u, "POST", "v1/artifacts", { body: raw, signal: s })).json(),
  getArtifactText: async (u, id, s) => { const r = await call(u, "GET", `v1/artifacts/${id}`, { signal: s }); return { text: await r.text(), contentType: r.headers.get("content-type") ?? "" }; },
  getUsage: async (u, s) => (await call(u, "GET", "v1/usage", { signal: s })).json(),
};
