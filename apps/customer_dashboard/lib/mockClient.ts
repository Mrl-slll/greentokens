// MOCK ONLY: in-memory fake. Nothing here ran on the real backend. The UI must show a MOCK badge.
import type { ApiClient } from "./client";
import { ApiError, type ArtifactSummary, type DevUser, type JobDetail, type SubmitJobRequest } from "./types";

type Rec = { owner: DevUser; hash: string; detail: JobDetail; sum: number };
const ORG = (u: DevUser) => (u === "bob" ? "org-b" : "org-a");

export function createMockClient(): ApiClient {
  const jobs = new Map<string, Rec>(), keys = new Map<string, string>();
  const arts = new Map<string, { org: string; values?: number[]; text: string; type: string }>();
  const id = () => crypto.randomUUID();
  const own = (u: DevUser, jid: string) => { const r = jobs.get(jid); if (!r || ORG(r.owner) !== ORG(u)) throw new ApiError(404, "Not found"); return r; };
  const mkArt = (u: DevUser, kind: ArtifactSummary["kind"], text: string, type: string): ArtifactSummary => {
    const artifact_id = id();
    arts.set(artifact_id, { org: ORG(u), text, type });
    return { artifact_id, kind, sha256: "mock-not-a-real-hash", size_bytes: text.length, expires_at: new Date(Date.now() + 864e5).toISOString() };
  };
  return {
    mode: "mock",
    async submitJob(u: DevUser, b: SubmitJobRequest) {
      const hash = JSON.stringify(b), k = `${ORG(u)}:${b.idempotency_key}`, old = keys.get(k);
      if (old) { const r = jobs.get(old)!; if (r.hash !== hash) throw new ApiError(409, "Idempotency key already used with different content"); return { job_id: old, status: r.detail.status }; }
      let values: number[];
      if ("parameters" in b) values = b.parameters.values;
      else { const a = arts.get(b.input_artifact_id); if (!a || a.org !== ORG(u) || !a.values) throw new ApiError(404, "Not found"); values = a.values; }
      const job_id = id(), now = new Date().toISOString(), sum = values.reduce((x, y) => x + y, 0);
      const out = mkArt(u, "output", JSON.stringify({ result: sum }), "application/json");
      const log = mkArt(u, "log", "MOCK LOG: not produced by a real worker.\n", "text/plain");
      jobs.set(job_id, { owner: u, hash, sum, detail: { job_id, template_id: "sum_numbers_v1", status: "SUCCEEDED", created_at: now, updated_at: now, cancel_requested: false, error_code: null, attempt_count: 1,
        attempts: [{ id: id(), attempt_number: 1, status: "SUCCEEDED", ray_submission_id: "mock", started_at: null, finished_at: null, worker_hostname: null, worker_pid: null, exit_code: null, error_code: null }], artifacts: [out, log] } });
      keys.set(k, job_id);
      return { job_id, status: "QUEUED" };
    },
    async getJob(u, jid) { return own(u, jid).detail; },
    async getResult(u, jid) { const r = own(u, jid); return { result: r.sum, job_id: jid, attempt_id: "mock-attempt" }; },
    async cancelJob(u, jid) { const r = own(u, jid); return { job_id: jid, status: r.detail.status, cancel_requested: false }; },
    async uploadInput(u, raw) {
      const values = JSON.parse(raw).values as number[], a = mkArt(u, "input", JSON.stringify({ values }), "application/json");
      arts.get(a.artifact_id)!.values = values;
      return { artifact_id: a.artifact_id, sha256: a.sha256, size_bytes: a.size_bytes, expires_at: a.expires_at };
    },
    async getArtifactText(u, aid) { const a = arts.get(aid); if (!a || a.org !== ORG(u)) throw new ApiError(404, "Not found"); return { text: a.text, contentType: a.type }; },
    async getUsage(u) { const n = [...jobs.values()].filter((r) => ORG(r.owner) === ORG(u)).length; return { attempts: n, wall_seconds: 0, billable: false, measurement: "MOCK: no real measurement" }; },
  };
}
