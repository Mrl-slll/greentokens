import type {
  CancellationResponse,
  DevelopmentIdentity,
  DownloadedArtifact,
  HealthResponse,
  JobDetail,
  JobResult,
  RequestOptions,
  SubmitJobRequest,
  SubmitJobResponse,
  UploadedArtifact,
  UsageResponse,
} from "./types";

const API_PREFIX = "/api/core";
const UUID_PATTERN = /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i;
const MAX_UPLOAD_BYTES = 65_536;
const MAX_VALUES = 1_000;
const MAX_INTEGER_MAGNITUDE = 1_000_000_000;

const DEFAULT_REQUIREMENTS = {
  cpu_cores: 1,
  ram_gb: 0.125,
  gpus: 0,
  execution_class: "trusted_cpu",
  max_runtime_seconds: 60,
} as const;

export class GreenTokensApiError extends Error {
  constructor(
    public readonly status: number,
    public readonly detail: string,
  ) {
    super(detail);
    this.name = "GreenTokensApiError";
  }
}

function validateId(id: string): string {
  if (!UUID_PATTERN.test(id)) {
    throw new TypeError("Invalid job or artifact ID");
  }
  return id;
}

export function validateValues(values: readonly number[]): void {
  if (!Array.isArray(values) || values.length < 1 || values.length > MAX_VALUES) {
    throw new RangeError("Provide between 1 and 1,000 integers");
  }
  if (
    !values.every(
      (value) => Number.isInteger(value) && Math.abs(value) <= MAX_INTEGER_MAGNITUDE,
    )
  ) {
    throw new RangeError("Values must be integers between -1,000,000,000 and 1,000,000,000");
  }
}

export function createInlineSubmission(values: readonly number[]): SubmitJobRequest {
  validateValues(values);
  return {
    template_id: "sum_numbers_v1",
    parameters: { values: [...values] },
    requirements: { ...DEFAULT_REQUIREMENTS },
    idempotency_key: crypto.randomUUID(),
  };
}

export function createArtifactSubmission(artifactId: string): SubmitJobRequest {
  return {
    template_id: "sum_numbers_v1",
    input_artifact_id: validateId(artifactId),
    requirements: { ...DEFAULT_REQUIREMENTS },
    idempotency_key: crypto.randomUUID(),
  };
}

export function parseUtcTimestamp(value: string | null): Date | null {
  if (value === null) return null;
  const withTimezone = /(?:Z|[+-]\d{2}:\d{2})$/i.test(value) ? value : `${value}Z`;
  const date = new Date(withTimezone);
  return Number.isNaN(date.valueOf()) ? null : date;
}

async function readError(response: Response): Promise<GreenTokensApiError> {
  let detail = `Request failed (HTTP ${response.status})`;
  try {
    const payload: unknown = await response.json();
    if (payload !== null && typeof payload === "object" && "detail" in payload) {
      const message = payload.detail;
      if (typeof message === "string" && message.length > 0) detail = message;
    }
  } catch {
    return new GreenTokensApiError(response.status, detail);
  }
  return new GreenTokensApiError(response.status, detail);
}

function validateUploadJson(json: string): void {
  const byteLength = new TextEncoder().encode(json).byteLength;
  if (byteLength > MAX_UPLOAD_BYTES) {
    throw new RangeError("Input file exceeds 65,536 bytes");
  }

  let parsed: unknown;
  try {
    parsed = JSON.parse(json);
  } catch {
    throw new TypeError("Input file must contain valid JSON");
  }

  if (
    parsed === null ||
    typeof parsed !== "object" ||
    Array.isArray(parsed) ||
    Object.keys(parsed).length !== 1 ||
    !("values" in parsed) ||
    !Array.isArray(parsed.values)
  ) {
    throw new TypeError('Input file must contain only a "values" array');
  }
  validateValues(parsed.values);
}

export function createGreenTokensClient(identity: DevelopmentIdentity) {
  const controller = new AbortController();

  async function request(
    path: string,
    method: "GET" | "POST",
    options: RequestOptions = {},
    jsonBody?: string,
  ): Promise<Response> {
    const headers = new Headers({ "X-Dev-User": identity });
    if (jsonBody !== undefined) headers.set("Content-Type", "application/json");

    const signal = options.signal
      ? AbortSignal.any([controller.signal, options.signal])
      : controller.signal;

    const response = await fetch(`${API_PREFIX}${path}`, {
      method,
      headers,
      body: jsonBody,
      signal,
      cache: "no-store",
    });

    if (!response.ok) throw await readError(response);
    return response;
  }

  async function getJson<T>(path: string, options?: RequestOptions): Promise<T> {
    const response = await request(path, "GET", options);
    return (await response.json()) as T;
  }

  async function postJson<T>(
    path: string,
    data: unknown,
    options?: RequestOptions,
  ): Promise<T> {
    const response = await request(path, "POST", options, JSON.stringify(data));
    return (await response.json()) as T;
  }

  return {
    getHealth: (options?: RequestOptions) =>
      getJson<HealthResponse>("/health", options),

    submitJob: (body: SubmitJobRequest, options?: RequestOptions) =>
      postJson<SubmitJobResponse>("/v1/jobs", body, options),

    getJob: (jobId: string, options?: RequestOptions) =>
      getJson<JobDetail>(`/v1/jobs/${validateId(jobId)}`, options),

    getJobResult: (jobId: string, options?: RequestOptions) =>
      getJson<JobResult>(`/v1/jobs/${validateId(jobId)}/result`, options),

    cancelJob: async (jobId: string, options?: RequestOptions) => {
      const response = await request(`/v1/jobs/${validateId(jobId)}/cancel`, "POST", options);
      return (await response.json()) as CancellationResponse;
    },

    getUsage: (options?: RequestOptions) =>
      getJson<UsageResponse>("/v1/usage", options),

    uploadInputArtifact: async (rawJson: string, options?: RequestOptions) => {
      validateUploadJson(rawJson);
      const response = await request("/v1/artifacts", "POST", options, rawJson);
      return (await response.json()) as UploadedArtifact;
    },

    downloadArtifact: async (
      artifactId: string,
      options?: RequestOptions,
    ): Promise<DownloadedArtifact> => {
      const response = await request(
        `/v1/artifacts/${validateId(artifactId)}`,
        "GET",
        options,
      );
      return {
        blob: await response.blob(),
        contentType: response.headers.get("content-type") ?? "application/octet-stream",
      };
    },

    dispose: () => controller.abort(),
  };
}

export type GreenTokensClient = ReturnType<typeof createGreenTokensClient>;
