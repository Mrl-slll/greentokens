export type DevelopmentIdentity = "alice" | "bob" | "admin";

export type JobStatus =
  | "QUEUED"
  | "DISPATCHING"
  | "RUNNING"
  | "SUCCEEDED"
  | "FAILED"
  | "CANCELLED";

export interface ResourceRequest {
  cpu_cores?: number;
  ram_gb?: number;
  gpus?: 0;
  execution_class?: "trusted_cpu";
  max_runtime_seconds?: number;
}

export type SubmitJobRequest = {
  template_id: "sum_numbers_v1";
  requirements?: ResourceRequest;
  idempotency_key: string;
} & (
  | { parameters: { values: number[] }; input_artifact_id?: never }
  | { input_artifact_id: string; parameters?: never }
);

export interface SubmitJobResponse {
  job_id: string;
  status: JobStatus;
}

export interface JobAttempt {
  id: string;
  attempt_number: number;
  status: string;
  ray_submission_id: string;
  started_at: string | null;
  finished_at: string | null;
  worker_hostname: string | null;
  worker_pid: number | null;
  exit_code: number | null;
  error_code: string | null;
}

export interface ArtifactSummary {
  artifact_id: string;
  kind: "input" | "output" | "log";
  sha256: string;
  size_bytes: number;
  expires_at: string;
}

export interface JobDetail {
  job_id: string;
  template_id: "sum_numbers_v1";
  status: JobStatus;
  created_at: string;
  updated_at: string;
  cancel_requested: boolean;
  error_code: string | null;
  attempt_count: number;
  attempts: JobAttempt[];
  artifacts: ArtifactSummary[];
}

export interface JobResult {
  result: number;
  job_id: string;
  attempt_id: string;
}

export interface UploadedArtifact {
  artifact_id: string;
  sha256: string;
  size_bytes: number;
  expires_at: string;
}

export interface CancellationResponse {
  job_id: string;
  status: JobStatus;
  cancel_requested: boolean;
}

export interface UsageResponse {
  attempts: number;
  wall_seconds: number;
  billable: false;
  measurement: string;
}

export interface HealthResponse {
  status: string;
  authentication: "development-stub";
}

export interface DownloadedArtifact {
  blob: Blob;
  contentType: string;
}

export interface RequestOptions {
  signal?: AbortSignal;
}
