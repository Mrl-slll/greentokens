// Shapes match core/api/main.py and docs/applications-handoff.md Section 5.
export type JobStatus = "QUEUED" | "DISPATCHING" | "RUNNING" | "SUCCEEDED" | "FAILED" | "CANCELLED";
export const TERMINAL: readonly JobStatus[] = ["SUCCEEDED", "FAILED", "CANCELLED"];
export type DevUser = "alice" | "bob" | "admin";
export const DEV_USERS: readonly DevUser[] = ["alice", "bob", "admin"];

export type ResourceRequest = { cpu_cores: 1; ram_gb: 0.125; gpus: 0; execution_class: "trusted_cpu"; max_runtime_seconds: 60 };
export const CPU_ONLY: ResourceRequest = { cpu_cores: 1, ram_gb: 0.125, gpus: 0, execution_class: "trusted_cpu", max_runtime_seconds: 60 };

export type SubmitJobRequest = {
  template_id: "sum_numbers_v1";
  requirements: ResourceRequest;
  idempotency_key: string;
} & ({ parameters: { values: number[] } } | { input_artifact_id: string });

export type SubmitJobResponse = { job_id: string; status: JobStatus };
export type ArtifactSummary = { artifact_id: string; kind: "input" | "output" | "log"; sha256: string; size_bytes: number; expires_at: string };
export type Attempt = { id: string; attempt_number: number; status: string; ray_submission_id: string; started_at: string | null; finished_at: string | null; worker_hostname: string | null; worker_pid: number | null; exit_code: number | null; error_code: string | null };
export type JobDetail = { job_id: string; template_id: "sum_numbers_v1" | "linear_regression_v1"; requirements?: ResourceRequest; input_source?: string; input_artifact_id?: string | null; status: JobStatus; created_at: string; updated_at: string; cancel_requested: boolean; error_code: string | null; attempt_count: number; attempts: Attempt[]; artifacts: ArtifactSummary[] };
export type LinearModel = { model_type: "linear_regression"; slope: number; intercept: number; training_mse: number; samples: number; prediction: string };
export type JobResult = { result: number | LinearModel; job_id: string; attempt_id: string };
export type CancelResponse = { job_id: string; status: JobStatus; cancel_requested: boolean };
export type UploadResponse = { artifact_id: string; sha256: string; size_bytes: number; expires_at: string };
export type Usage = { attempts: number; wall_seconds: number; billable: false; measurement: string };

export class ApiError extends Error {
  constructor(public status: number, public detail: string) { super(detail); }
}
