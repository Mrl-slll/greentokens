# GreenTokens — Frontend & Provider App Teammate Handoff

Project: GreenTokens Applications (Project 2 of 3)

Version 1.1 — 14 November 2026. Audience: frontend/desktop teammate and core developer.

**Current status:** Core Milestones 0–3 are implemented and locally tested. The customer frontend is not built. Provider UI is design/mock scope only. This handoff is checked against the current repository; it does not authorize new dependencies, a public deployment or a production installer.

## First day: deliver one working customer job

1. Read Sections 5, 9 and 12. Confirm the customer folder and dependency plan before installing frontend packages.

2. Start the local backend and verify /health from the same machine. A teammate on another PC cannot use the core developer's loopback address; run an approved local stack or use mocks until a separate integration environment is agreed.

3. Implement the typed adapter and fixed local proxy, then one form using CPU-only defaults. Keep the first screen focused on submitting and inspecting one job.

4. Submit [1,2,3,4] in live mode, display the returned job_id, poll actual status and fetch result 10. Preserve the same submission key/body if the response is uncertain.

5. Refresh the job page, verify the result again, and switch identities to confirm prior data clears. Supply a screenshot, actual commands and a short live walkthrough before expanding the UI.

## 0. Start here

GreenTokens is a compute platform. Customers bring supported workloads; GreenTokens manages approved execution, status, usage records and results. The permanent backend is FastAPI + MySQL + Ray Jobs/Core + S3-compatible storage. SeaweedFS is the approved local storage implementation.

Today, one trusted development machine runs one approved CPU template: `sum_numbers_v1`. Data processing, inference, GPU execution and training are future capabilities. The four-PC coordinated training experiment is separate from the core product and this assignment.

There are two audiences: customers submitting jobs, and hardware owners deciding whether to share capacity. Build the customer journey first. Provider consent, hardware display and pause controls can be designed with clearly labeled mocks; they must not imply real agent enforcement.

The first UI is an internal, non-sensitive local demo. Keep a visible **Local development — identity stub** banner. There is no secure account login, public marketplace, billing or payout. Distinguish mock results from real local execution.

## 1. Ownership and boundaries

| Applications teammate owns | Core team owns |
| --- | --- |
| Customer routes, components, forms and accessibility | API validation, ownership and policy decisions |
| Typed client adapters, mock fixtures and UI tests | Durable jobs/attempts, dispatcher and Ray execution |
| Status, result, artifact and usage presentation | Storage access, integrity, expiry and metering |
| Provider wireframes and simulated onboarding | Worker agent, hardware discovery and enforcement |
| Proposed provider pause/preferences UX | Actual pause, approval and worker lifecycle |
| Later installer UX/packaging proposals | Signing, updates, privileged operations and security |

The browser calls only the GreenTokens API, through a fixed local frontend proxy where needed. Never connect to Ray, MySQL, SeaweedFS or worker-control sockets from the UI. Do not access or copy service credentials. Coordinate backend changes; do not build a competing scheduler or database.

## 2. Stack and repository scope

Next.js + React + TypeScript is the proposed customer stack, not an installed or approved package set. Follow `AGENTS.md`: inspect existing code, reuse libraries, verify versions/licenses and obtain approval before adding dependencies. Start with native fetch and simple form validation. No frontend package manifest exists at this inspection.

| Area | Proposed approach | Scope |
| --- | --- | --- |
| Customer UI | Next.js, React, TypeScript | First approved task |
| Styling | Small CSS layer or approved Tailwind setup | One approach; restrained green accents |
| Components/types | App-local modules initially | Extract shared packages only when reuse exists |
| Forms | Native validation; add a form/schema library only if justified | Match backend bounds |
| Data | Typed fetch adapter; explicit mock/live modes | No unnecessary query framework |
| Tests | Consider Vitest/Testing Library and Playwright | Approve minimal test dependencies first |
| Provider UI | Wireframes or browser mock initially | Tauri/React is a later option |
| Agent/installer | Core-owned agent; separately reviewed packaging | Not part of the first deliverable |

```text
Existing: core/, scripts/, infrastructure/, tests/, docs/ — preserve these.
First approved frontend work:
  apps/customer_dashboard/     # UI, app-local contracts and local API proxy
Later, only when needed and approved:
  apps/provider_app/           # Provider UI source
  apps/provider_agent/         # Core team's worker agent
  apps/provider_installer/     # Packaging/signing, not UI source
  packages/ui/                 # Only after actual shared-component reuse
  packages/contracts/          # Only after multiple apps need shared types
  experiments/four_pc_training/ # Separate experiment
```

Do not create empty scaffolding. At this inspection the workspace is not an initialized Git repository. Confirm repository/remote and review workflow before assuming branches or PRs exist.

## 3. Customer dashboard

The first live journey is: submit `[1,2,3,4]`, retain the returned `job_id`, follow the actual state, and display result `10`. Repeat using an uploaded JSON input artifact. Only `sum_numbers_v1` is enabled; dataset-transform and inference templates remain future proposals.

| Screen | Must show | Available integration |
| --- | --- | --- |
| Dashboard | Known recent jobs, create-job action, optional aggregate usage | No server-side job-list endpoint |
| New job | Inline values or JSON file; CPU-only defaults | POST jobs and artifacts |
| Jobs | “Recent jobs on this browser,” scoped by development identity | Refetch individually by known ID |
| Job detail | Actual state, attempts, UTC timestamps, error_code, artifacts | GET job; POST cancel |
| Results | Result, size/hash/expiry, output download and plain-text logs | GET result and artifacts |
| Usage | Attempt count and elapsed wall time; nonbillable label | GET usage; no range filters/prices |
| Settings | Mock/live mode and development identity selector | No account/profile/settings API |

Store only the bounded list of known job IDs per development identity for refresh recovery; refetch authoritative records from the API. This is not complete organization history. Do not silently call an unavailable list endpoint or present fixtures as live jobs.

Use 1 CPU, `ram_gb: 0.125` (128 MiB), zero GPUs and `trusted_cpu`. Larger memory requests may fail admission on this machine. Do not enable GPU/VRAM fields or send unsupported fields.

Poll about every two seconds while detail is active and the job is nonterminal. Stop on terminal state, navigation or identity change; cancel stale requests. Back off on transport errors while retaining the job ID. Fast jobs may skip observable intermediate states: never fabricate progress percentages, transitions or timestamps.

Render QUEUED, DISPATCHING, RUNNING, SUCCEEDED, FAILED and CANCELLED. RETRY_PENDING is future-only. Attempt status can include SUBMITTING; it is not a job status. Include loading, empty, offline, validation/resource rejection, queue-limit, cancellation-pending and expired-result states.

GitHub login/repository workflows are future scope. Never request a personal access token in the browser or execute arbitrary repository code. A placeholder is optional and must be visibly disabled.

## 4. Provider app — later, mock-only scope

The intended provider experience is understandable without Python, Ray, Docker or a terminal. That is a future UX goal, not a claim that the current backend installs or controls a PC.

| Step | Proposed screen | Required behavior in the mock |
| --- | --- | --- |
| 1 | Welcome | Explain pilot status, eligibility and no guaranteed earnings |
| 2 | Consent | Explain power/performance/privacy limits; explicit unchecked consent |
| 3 | Account/invite | Clearly simulated; no real provider identity endpoint exists |
| 4 | Hardware | Separate CPU, system RAM, GPU, VRAM and free disk; label mock values |
| 5 | Preferences | Availability, CPU/RAM/GPU limits and stop conditions are simulated |
| 6 | Ready check | Pending approval until simulated checks pass; real readiness needs an agent |
| 7 | Provider home | Default paused; prominent pause; clear offline/unsupported/error states |

The proposed provider home shows connection state, sharing state, hardware, preferences and current/completed test jobs. Earnings must say “Unavailable during pilot,” not show invented income. System RAM and GPU VRAM are separate and do not pool across PCs.

Agree on pause semantics before real integration: stopping new work differs from stopping an active job. A mock action must never claim to have paused a real worker. Show a clear missing-agent state. Owner/admin permission is required for shared or institution-owned hardware; no sensitive customer data belongs on volunteer machines.

The core-owned agent will detect hardware, enforce limits/pause, communicate with the backend and run approved workloads. A future UI bridge must be narrow and authenticated; it must not expose shell execution. Tauri is not an execution sandbox. Desktop dependencies, installers, updates, signing, drivers and privileged operations require separate review and approval.

## 5. Live API contract and genuine gaps

| Method/path | Current behavior |
| --- | --- |
| GET /health | Database check; status and development-stub marker |
| POST /v1/jobs | HTTP 202; job_id and status |
| GET /v1/jobs/{id} | Job state, attempts, timestamps, errors and artifact metadata |
| GET /v1/jobs/{id}/result | Authorized result JSON after success |
| POST /v1/jobs/{id}/cancel | job_id, status and cancel_requested |
| POST /v1/artifacts | Raw JSON input upload; HTTP 201 with ID/checksum/size/expiry |
| GET /v1/artifacts/{id} | Authorized JSON input/output or text/plain log |
| GET /v1/usage | attempts, wall_seconds, billable:false, measurement |
| GET /v1/workers | Admin-only diagnostic inventory; not customer/provider UI data |
| GET /openapi.json | Developer reference; response/header typing is incomplete |

**Unavailable proposals:** GET /v1/jobs with filters/pagination; GET /v1/job-templates; GET /v1/me; all /v1/provider/* profile/device/preferences/pause/resume APIs. There is no real auth, pricing, signed-download-URL or account settings API. Do not call these in live mode.

```typescript
export type JobStatus =
  | 'QUEUED' | 'DISPATCHING' | 'RUNNING'
  | 'SUCCEEDED' | 'FAILED' | 'CANCELLED';

export type ResourceRequest = {
  cpu_cores?: number;             // integer 1–4; default 1
  ram_gb?: number;                // 0.0625–4; default 0.125
  gpus?: 0;
  execution_class?: 'trusted_cpu';
  max_runtime_seconds?: number;  // integer 1–300; default 60
};
type JobInput =
  | { parameters: { values: number[] }; input_artifact_id?: never }
  | { input_artifact_id: string; parameters?: never };
export type SubmitJobRequest = JobInput & {
  template_id: 'sum_numbers_v1';
  requirements?: ResourceRequest;
  idempotency_key: string;
};
export type SubmitJobResponse = { job_id: string; status: JobStatus };
export type ArtifactSummary = {
  artifact_id: string; kind: 'output' | 'log';
  sha256: string; size_bytes: number; expires_at: string;
};
export type JobDetail = {
  job_id: string;                  // NOT id
  template_id: 'sum_numbers_v1'; status: JobStatus;
  created_at: string; updated_at: string;
  cancel_requested: boolean;
  error_code: string | null;       // NOT error_message
  attempt_count: number;
  attempts: Array<{
    id: string; attempt_number: number; status: string;
    ray_submission_id: string;
    started_at: string | null; finished_at: string | null;
    worker_hostname: string | null; worker_pid: number | null;
    exit_code: number | null; error_code: string | null;
  }>;
  artifacts: ArtifactSummary[];
};
export type JobResult = {
  result: number; job_id: string; attempt_id: string;
};
```

TypeScript number does not enforce integers or bounds; validate those explicitly. Reject extra request fields. Job detail does not return submitted parameters or requirements, so do not assume they can be reconstructed after refresh.

FastAPI exposes OpenAPI, but most responses are untyped dictionaries and X-Dev-User is read manually. Generated types alone will not capture the full response/header contract. Keep checked fixtures alongside the adapter until explicit response models are added. Provider mock contracts must remain separate.

Live development selectors are alice → org-a, bob → org-b and admin → org-a with admin role. These are nonsecret selectors, not real accounts. Mock fixtures must use live field shapes. Resource rejection at submission is HTTP 422 with no created job; execution-time failure is a persisted FAILED job with error_code.

## 6. Visual style and accessibility

Use a neutral background, restrained green accents, readable type and clear status text. GreenTokens is a compute platform, not a token-trading dashboard. Never rely on color alone. Keep forms usable on smaller screens and support keyboard navigation, visible focus, labeled controls, associated field errors and accessible dialogs.

Make mock/live state obvious. Do not invent live metrics, timestamps, estimates or earnings. Render logs as plain text. Loading, empty, error and offline states belong in each primary screen. Reuse components within the app before introducing a shared package.

## 7. Suggested four-week sequence and workflow

This is a sequence, not a delivery promise. The local backend already exists.

| Week | Customer work | Provider scope / review |
| --- | --- | --- |
| 1 | Confirm toolchain; shell, typed adapters, local proxy and fixtures | Wireframes only; verify live API connectivity |
| 2 | Live inline job, polling/detail/result and browser-local IDs | Review consent/paused-state concepts |
| 3 | File input, artifacts/logs, cancellation and isolation/error tests | Mock walkthrough only if separately agreed |
| 4 | Accessibility, responsive checks, E2E tests and run instructions | Acceptance evidence and later agent requirements |

Suggested task titles: customer shell; typed adapters/local proxy; new-job form; detail/polling; artifact/results; browser-local recent jobs; usage; accessibility and live acceptance. These are proposed tasks, not already-created issues. Provider onboarding and installer tasks come later.

Agree on repository/remote and contribution workflow first. Create issues, branches, commits and PRs only when explicitly authorized. Keep changes focused, run the relevant checks, and provide screenshots, a live walkthrough and known API gaps for review. Do not alter core/ or push to main independently. Never commit credentials or personal datasets.

## 8. Acceptance checklist

- Dashboard, new-job, recent-jobs, detail and result views exist; recent jobs are explicitly browser-local and identity-scoped.
- A real inline sum job and an uploaded-file sum job both return 10. Mock mode is clearly separate and works with the backend offline.
- Polling handles skipped states, navigation and identity changes without stale updates. Cancellation remains pending until confirmed.
- Retrying an uncertain submission with the same key/body returns the same job ID.
- Refresh recovers known IDs and refetches authoritative status; there is no call to a nonexistent job-list endpoint.
- Switching alice to bob clears prior visible data. Alice's job/result/artifact IDs are denied to bob with 404. No organization override exists in submission bodies.
- Invalid input, resource rejection, queue limit, offline state, expired result and artifact failure have clear feedback. Mark simulated error tests as simulated.
- Output/log downloads use the API; logs are plain text and metadata is real. No direct infrastructure calls or secret-bearing client bundles.
- Keyboard, focus, errors, contrast and responsive layout are checked.
- Actual commands, pass/fail results, screenshots and a live walkthrough are supplied. Backend test results are not frontend test evidence.

Later provider acceptance is separate: clearly simulated consent, approval, hardware and pause/resume; paused by default; offline/missing-agent/unsupported states; no earnings claims or shell bridge. A real desktop build needs its own approved scope and agent contract.

## 9. First assignment

Build the smallest reviewable customer change set: an app shell, browser-local recent IDs, sum form, detail/polling, result/artifact views, typed mock/live adapters and a fixed local API proxy. Use the already working backend to prove a live result 10. Include setup instructions and focused UI/integration tests. Open a PR only when authorized.

Before implementation, confirm app folder names, dependency choices, proxy behavior, development identity handling and acceptance tests. Do not wait for the smoke test or API to be built; they already exist. Provider wireframes can follow customer acceptance. Tauri, real agents, installers, payments and GitHub OAuth are excluded from this first task.

## 10. Teammate coding-agent prompt

Read docs/applications-handoff.md and AGENTS.md, then inspect this repository. Work on Section 9 only. The local FastAPI/MySQL/Ray/SeaweedFS pipeline exists; the frontend does not. Propose minimal Next.js/TypeScript files, dependencies and acceptance tests, and obtain the approvals required by project rules. Build a customer dashboard, browser-local recent jobs, sum_numbers_v1 form, detail/polling, result 10 and authorized artifact downloads. Keep typed mock/live adapters and a fixed allowlisted same-origin local proxy. The backend has no CORS setup, job-list endpoint or real authentication. Never send organization ownership in job bodies. Do not modify core/, expose infrastructure, run customer code, install provider agents, add payments/GitHub OAuth or create GitHub artifacts without authorization. Report actual commands/tests, live versus mocked checks, screenshots and remaining gaps.

## 11. What done means

A teammate can run the local customer UI, submit an approved job through the real API, follow observed status and retrieve result 10 and authorized artifacts. Refresh recovers known IDs; identity changes clear prior visible data. The provider experience is a separate simulated design until real agent interfaces are approved. Neither this UI nor the backend's development identity stub is production authentication.

## 12. Local setup and browser integration

Start Docker Desktop. From the repository root in PowerShell:

```powershell
.\.venv\Scripts\python.exe -m scripts.local_stack
```

The current environment is installed on the core developer's machine; a teammate needs their own approved setup. Do not copy .venv or service credentials between computers. Keep the launcher running; Ctrl+C stops API/dispatcher/Ray while retaining the dedicated database/storage containers. See docs/local-development.md for full setup and safe shutdown.

API docs: http://127.0.0.1:8000/docs. Schema: http://127.0.0.1:8000/openapi.json.

Swagger caveat: /docs shows routes, but X-Dev-User is not declared as an OpenAPI header parameter. Its default Try it out controls do not provide this identity header. Use the documented PowerShell requests or the frontend adapter for protected endpoints; a 401 from an unauthenticated Swagger request does not mean the API is unavailable.

**Transport gap:** the API has no CORSMiddleware. Browser calls from frontend port 3000 to backend port 8000 with JSON and X-Dev-User are not an established cross-origin integration. Build a same-origin frontend server proxy, for example /api/core/..., or coordinate explicit CORS support with the core developer. Do not use no-cors mode or weaken backend host restrictions.

The proxy must target only http://127.0.0.1:8000 and allow only needed routes/methods. Validate identifiers, preserve upstream status/content type, forward bounded bodies and cancel abandoned requests. Never accept arbitrary upstream URLs or proxy Ray/storage/database ports. Bind the frontend server to loopback too. This is a local design, not real authentication or permission to deploy publicly.

Send X-Dev-User: alice or bob. Label the selector Development identity. Cancel pending calls and clear visible/cache data on changes before loading that identity's known IDs. Use admin only for diagnostics. The API resolves organization membership; organization_id is forbidden in job bodies.

## 13. Exact requests and UI behavior

### Inline submission — HTTP 202

```json
{
  "template_id": "sum_numbers_v1",
  "parameters": {"values": [1, 2, 3, 4]},
  "requirements": {
    "cpu_cores": 1,
    "ram_gb": 0.125,
    "gpus": 0,
    "execution_class": "trusted_cpu",
    "max_runtime_seconds": 60
  },
  "idempotency_key": "frontend-demo-001"
}
```

Send to POST /v1/jobs with Content-Type: application/json and X-Dev-User: alice. Response shape is `{"job_id":"<uuid>","status":"QUEUED"}`; use the actual returned ID. An idempotent replay can return a terminal state. Preserve the same key and identical body after an uncertain network outcome. A deliberately new submission gets a new key; changed content with an old key returns 409. Keys contain 1–128 letters, digits, underscores, periods, colons or hyphens.

### File input

POST /v1/artifacts accepts raw JSON such as {"values":[1,2,3,4]}, not multipart/form-data. HTTP 201 returns artifact_id, sha256, size_bytes and expires_at. JSON is normalized before storage; returned checksum/size describe stored bytes, not necessarily original formatting. Submit the returned ID:

```json
{
  "template_id": "sum_numbers_v1",
  "input_artifact_id": "<artifact_id returned by upload>",
  "idempotency_key": "frontend-file-demo-001"
}
```

Use exactly one input mode: parameters OR input_artifact_id. Accept 1–1000 integers, each between -1,000,000,000 and 1,000,000,000; reject strings, fractions and booleans. Files must be at most 65,536 bytes. Uploads have no idempotency contract; do not automatically repeat an upload after an ambiguous response.

### Cancellation, results and time

POST cancel returns job_id, status and cancel_requested. Show Cancellation requested while the job is nonterminal and continue polling. Do not promise immediate termination, fabricate retries or change terminal state locally.

After success, GET result returns `{"result":10,"job_id":"<uuid>","attempt_id":"<uuid>"}`. GET artifact returns application/json for input/output and text/plain for logs. Fetch downloads through the adapter/proxy so the identity header is included. Use safe filenames, render logs as text and revoke temporary browser object URLs. There are no presigned URLs.

Artifacts expire after 24 hours for API access. A succeeded job can later have an expired result: retain SUCCEEDED and show Result expired. Physical deletion is not automatic. The backend verifies size and checksum before returning bytes.

Current timestamps are UTC even when serialized without a timezone suffix. Normalize timezone-less API timestamps as UTC at the adapter boundary before formatting for the viewer. Null timestamps stay unavailable; do not invent them. Submitted parameters/requirements are absent from job detail.

### Error handling and usage

Errors use a detail field. Interpret 409 by operation: idempotency conflict on submission versus no successful result on result fetch. Show actionable validation/resource feedback for 422, queue limit for 429, expiry for 410 and artifact failure for 502. Preserve IDs on network errors and do not infer execution failure from a failed HTTP call.

GET usage returns attempts, wall_seconds, billable:false and measurement. Display elapsed attempt time, not CPU utilization, GPU time, credits, currency or earnings. No date-range filters or pricing exist.

Quick troubleshooting: a browser CORS error means check the local proxy path; 422 means inspect input bounds or worker capacity; 409 means inspect idempotency or result readiness for that operation; 404 after an identity switch can be the expected ownership denial. A running /health check proves database/API availability, not Ray or storage readiness.

## 14. Source of truth and revision notes

Checked sources: core/api/main.py; core/api/schemas.py; core/config.py; core/artifacts/storage.py; core/jobs/dispatcher.py; scripts/local_stack.py. Keep adapters and fixtures aligned when contracts change. Executable backend code is authoritative.

Related docs: docs/local-development.md, docs/architecture.md, docs/security-boundaries.md and docs/validation-milestones-2-3.md. The backend record reports 15 core tests, one original smoke integration test and real MySQL/Ray/S3 acceptance checks. Frontend tests still need to be written and run.

Version 1.1 corrects backend status, live field names, templates/resources, artifact/usage support and the first assignment. It adds local transport, identity, idempotency, cancellation, UTC, expiry and live acceptance guidance. Provider work remains separately scoped.

The original Word v1.0 is preserved as GreenTokens_Frontend_Teammate_Handoff.original-v1.docx. This Markdown and the revised Word document contain the same handoff; keep both aligned when updating the contract.

Version 1.2 adds a first-day delivery checklist, clarifies same-machine connectivity and Swagger's missing identity-header control, and provides operation-specific troubleshooting.
