# GreenTokens

GreenTokens is a compute platform for submitting approved workloads, monitoring execution, and retrieving results. The customer application is the first frontend deliverable. A hardware-provider application is planned separately.

## Project scope

The existing local backend uses FastAPI, MySQL, Ray Jobs/Core, and S3-compatible storage (SeaweedFS in development). The initial workload is `sum_numbers_v1`, executed on a trusted local CPU worker. The backend source and local setup instructions are included in this repository. The pipeline has been tested in the core developer's local environment.

**First deliverable:** A customer can submit `[1, 2, 3, 4]`, receive a job ID, follow its actual status, and view the result `10`. The complete customer MVP will also accept an uploaded JSON input file and support job history, results, logs, cancellation, and usage information.

Public accounts, GPU workloads, payments, provider agents, and installer software are outside the current customer MVP. Any provider screens are prototypes until backend support exists.

## Team ownership

| Area | Owner | Deliverables | Primary files |
| --- | --- | --- | --- |
| **Person A - shell, proxy, and submission** | **chaewon-research** | Customer app setup, navigation, fixed same-origin proxy, typed API adapters, development identity selector, inline job submission, browser-local recent job IDs | `apps/customer_dashboard/` app shell, API proxy, client/types, submission and identity modules |
| **Person B - job lifecycle and outputs** | **Michelle Lyu ([@Mrl-slll](https://github.com/Mrl-slll))** | Job detail and ~2-second polling, status/error presentation, results, authorized logs and artifacts, raw JSON file upload, cancellation | `apps/customer_dashboard/` job detail, results, file upload and cancellation modules |
| **Core backend** | **Core developer** | Backend source and local stack, API policy, job execution, storage, worker/agent implementation | `core/`, `scripts/`, `infrastructure/`, backend docs |
| **Integration and quality** | **Persons A + B** | Agree on adapter interfaces, wire pages to the API, test identity isolation and end-to-end execution, review and document the demo | Joint integration and review |

**Interface agreement:** Person A owns the shared typed client, proxy and identity state. Person B calls that client for job detail, results, artifacts and cancellation rather than building a second proxy or transport layer. Agree on function signatures and error handling before parallel implementation. Changes to backend code remain with the core developer.

## Delivery order

| Priority | Deliverable | Acceptance |
| --- | --- | --- |
| **P0** | Local customer dashboard + inline job | A real `sum_numbers_v1` submission returns `10` through the frontend |
| **P1** | Complete customer MVP | JSON upload, recent jobs, results/artifacts, cancellation, usage, and identity isolation work |
| **P1** | Quality and documentation | Tested error cases, accessible layouts, reproducible setup, screenshots, and demo walkthrough |
| **P2** | Provider interface prototype | Clearly simulated onboarding, hardware, preferences, and pause states |

## Task checklist

### P0 — Repository and setup

- [x] **Core:** Add the backend source, `AGENTS.md`, `docs/applications-handoff.md` and local setup documentation to the shared repository. Exclude credentials, `.env`, `.venv`, storage volumes and private datasets.
- [x] **Core:** Document the backend API contract and command for starting the local stack.
- [ ] **A + B:** Confirm the Next.js, React, TypeScript and styling choices; review newly installed dependencies and the reported npm audit findings under `AGENTS.md`.
- [x] **A:** Initialize `apps/customer_dashboard/` with Next.js 16.4.6, TypeScript, ESLint, Tailwind CSS and the App Router. Local lint, production build and development-server startup passed on 14 November 2026.
- [x] **A:** Commit and push the frontend source and package lockfile on `feat/customer-dashboard-ui` (`8cc069c`). Open draft pull request [#1](https://github.com/Mrl-slll/greentokens/pull/1) against `main` for review; do not merge before integration checks.
- [ ] **A + B:** Agree on adapter methods, component props, error behavior and separate feature branches before simultaneous work.
- [ ] **A + Core:** Start the approved local backend and verify `GET /health`. The core developer's `127.0.0.1` cannot be reached from another PC without separate configuration.
- [ ] **A:** Document verified frontend installation, start, mock/live configuration and API proxy steps after they are reproducible.

### P0 — Person A: application shell, proxy and job submission

**Frontend status (14 November 2026):** The customer console renders locally, and the API proxy, typed client and frontend compile and pass ESLint. The initial source is committed on `feat/customer-dashboard-ui` and available for review in [draft PR #1](https://github.com/Mrl-slll/greentokens/pull/1). The proxy returned HTTP 404 for the blocked `/v1/workers` route and HTTP 502 for `/health` while FastAPI was offline at `127.0.0.1:8000`. Identity switching, form validation, live submissions and end-to-end execution still require testing.

- [x] Build the initial customer dashboard with a visible **New job** form. The local page renders.
- [ ] Add persistent navigation when the job-detail, usage and settings views are integrated.
- [x] Display **Recent jobs on this browser**, including an empty state, using browser-local IDs rather than a nonexistent server-side job-list API.
- [ ] Verify recent-job display and loading/error behavior when IDs exist and job detail is integrated.
- [x] Define TypeScript types for submissions, job detail, attempts, statuses, artifacts, results and usage from the backend implementation.
- [x] Implement a typed live API client for job submission, detail, results, artifacts, cancellation and usage.
- [ ] Add a separate mock adapter behind the agreed client interface. Never present mock data as live execution.
- [x] Implement the fixed same-origin server proxy (`/api/core/[...path]`) to `http://127.0.0.1:8000`: allowlist methods and endpoints, validate IDs, bound request sizes and preserve upstream status/content type. Route blocking and production build are verified; live backend connectivity is pending.
- [x] Implement a **Local development - identity stub** banner and selector (`alice`, `bob`; `admin` for diagnostics only), with `X-Dev-User` forwarding and no `organization_id` in job bodies. Browser testing remains pending.
- [x] Implement request abortion and submission-state reset on identity change, with separately keyed browser-local recent job IDs.
- [ ] Verify identity switching, stale-request teardown and cross-identity isolation in the browser and against the live backend.
- [x] Implement the inline **New job** form for `sum_numbers_v1` with 1-1,000 integer inputs, each from -1,000,000,000 to 1,000,000,000. Browser testing remains pending.
- [x] Configure CPU-only submission defaults: 1 CPU core, `ram_gb: 0.125`, 0 GPUs, `trusted_cpu`, and `max_runtime_seconds: 60`.
- [x] Implement the `POST /v1/jobs` client method and reuse the same `idempotency_key` and request body for an uncertain retry. Live submission behavior remains unverified.
- [ ] Retain and display the backend's real `job_id` and status from HTTP 202; never invent submission success.
- [x] Implement bounded browser-local recent job ID storage, scoped by development identity.
- [ ] Link recent IDs to the job-detail view and refetch authoritative records after reload.
- [ ] Verify accessible form validation and offline request-failure states in the browser; coordinate the handoff from successful submission to Person B's job-detail route.

### P0 — Person B: job detail, polling and results

- [x] Implement **Job detail** with authoritative `GET /v1/jobs/{id}` data: job ID, status, attempts, timestamps, error code, artifacts and cancellation state.
- [x] Poll active jobs approximately every 2 seconds. Stop on terminal status, navigation or identity change; abort stale requests and back off on transport errors.
- [x] Render `QUEUED`, `DISPATCHING`, `RUNNING`, `SUCCEEDED`, `FAILED` and `CANCELLED` using actual API states, without fabricated progress or timestamps.
- [x] Show actionable states for validation/resource rejection (422), result not ready or idempotency conflict (409, depending on operation), queue limit (429), expired result (410), artifact failure (502), inaccessible job (404) and offline transport errors.
- [x] Fetch `GET /v1/jobs/{id}/result` after success, display the real output and keep successful jobs marked `SUCCEEDED` when an output expires.
- [x] Implement authorized artifact/output retrieval and plain-text log rendering through Person A's client and proxy.
- [x] Display cancellation-pending and status transitions accurately. Person A supplies the shared API methods; Person B owns this screen's request lifecycle.
- [x] Support keyboard, focus, text status labels, responsive layout, and loading/empty/error states on job-detail and results screens.

### P0 — First integration (Frontend A + B)

- [ ] Connect the New Job form to the live submission adapter and display the backend's returned job ID.
- [ ] Connect the detail view to actual job states: `QUEUED`, `DISPATCHING`, `RUNNING`, `SUCCEEDED`, `FAILED`, `CANCELLED`.
- [ ] Submit `[1, 2, 3, 4]` through the frontend, wait for `SUCCEEDED`, and display the actual result `10`.
- [ ] Refresh the job page and verify that the known job loads again from the API.
- [ ] Switch from `alice` to `bob` and verify that Alice's visible job and result data are cleared.
- [ ] Record the setup commands and a screenshot or short walkthrough of the live flow.

### P1 — Uploads, artifacts, cancellation and usage

**Person A**

- [x] Define typed live client methods for file upload, artifacts, cancellation and usage through the allowlisted proxy. Runtime integration with Person B remains pending.
- [ ] Keep development identity scoping and known-job recovery correct for jobs created from uploaded artifacts.
- [ ] Add a **Settings** view for development identity and mock/live selection; no real account profile or billing settings.
- [ ] Add a **Usage** view showing actual `attempts`, `wall_seconds`, `billable: false` and `measurement` from `GET /v1/usage`, without invented GPU metrics or pricing.

**Person B**

- [ ] Add a JSON-file input option (maximum 65,536 bytes), validating `values` against the same bounds as inline submission.
- [ ] Send raw JSON to `POST /v1/artifacts` (not multipart form data), then submit the returned `input_artifact_id` without inline `parameters`.
- [ ] Never blindly retry an ambiguous artifact upload: the upload endpoint has no idempotency contract.
- [ ] Download authorized input/output JSON and plain-text logs using `GET /v1/artifacts/{id}` through the shared proxy; show actual hash, size and expiry, use safe filenames and release temporary object URLs.
- [ ] Implement `POST /v1/jobs/{id}/cancel`; show **Cancellation requested** and continue polling until the backend confirms its actual outcome.
- [ ] Handle result expiry independently of job status: an expired artifact does not turn `SUCCEEDED` into `FAILED`.

**Joint acceptance**

- [ ] Submit uploaded `{"values":[1,2,3,4]}` through the real backend and retrieve result `10`.
- [ ] Verify Bob cannot fetch Alice's job/result/artifact IDs (expected `404`) and identity switching clears previously displayed data.
- [ ] Verify cancellation stays pending until the backend confirms the final state.

### P1 — Tests and release checks (Frontend A + B)

- [ ] Test empty input, non-integers, out-of-range values, overlong arrays, invalid JSON, and oversized files.
- [ ] Test submission outcomes: validation/resource rejection (`422`), idempotency conflict (`409`), and queue limit (`429`).
- [ ] Test result/artifact states: result not ready (`409`), expiry (`410`), artifact failure (`502`), and inaccessible IDs (`404`).
- [ ] Test offline mode, request timeouts, stalled polling, cancellation, and rapid navigation/identity changes.
- [ ] Verify that pending requests do not update the UI after switching users or leaving a job page.
- [ ] Verify that replaying the same submission key and body returns the same job ID after an uncertain response.
- [ ] Verify that logs are rendered as text and no frontend bundle or network request exposes infrastructure credentials.
- [ ] Check keyboard navigation, contrast, focus states, error messages, and responsive layout.
- [ ] Run the approved frontend unit/integration/end-to-end checks; record actual results and known failures.
- [ ] Review the final live flow together and include reproducible commands, screenshots, and outstanding limitations in the handoff.

### P2 — Provider interface prototype (owner to be assigned; review with Core)

Start this only after the customer MVP is accepted.

- [ ] Design provider welcome and consent screens, including resource/privacy implications and unchecked consent.
- [ ] Design simulated invitation/approval steps; do not imply that real provider accounts are available.
- [ ] Design a hardware panel separating CPU, system RAM, GPU, VRAM, and free disk; label all mock values.
- [ ] Design availability and resource-limit preferences with a simulated readiness check.
- [ ] Design the provider home screen with a paused-by-default state, pause control, and offline/missing-agent states.
- [ ] Label earnings **Unavailable during pilot**. A mock pause must not claim to stop real jobs.
- [ ] Review pause semantics and future worker-agent API requirements with Core before any live integration.

## Backend endpoints used by the customer app

| Method | Endpoint | Use |
| --- | --- | --- |
| `GET` | `/health` | Local API/database health |
| `POST` | `/v1/jobs` | Submit the approved CPU job |
| `GET` | `/v1/jobs/{id}` | Job status, attempts, timestamps, errors, artifacts |
| `GET` | `/v1/jobs/{id}/result` | Successful job output |
| `POST` | `/v1/jobs/{id}/cancel` | Request cancellation |
| `POST` | `/v1/artifacts` | Upload raw JSON input |
| `GET` | `/v1/artifacts/{id}` | Retrieve authorized artifact or log |
| `GET` | `/v1/usage` | Attempt count and elapsed wall time |
| `GET` | `/openapi.json` | API reference (current responses/header documentation is incomplete) |

The development API requires `X-Dev-User` for protected requests. The current backend has no browser CORS configuration; browser requests should use the local same-origin proxy. `GET /v1/jobs`, `/v1/job-templates`, `/v1/me`, and `/v1/provider/*` are not available. `/v1/workers` is admin diagnostics, not a customer screen.

Example submission body:

```json
{
  "template_id": "sum_numbers_v1",
  "parameters": { "values": [1, 2, 3, 4] },
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

Generate an appropriate key for each new submission; the example key is not a permanent shared value.

## Local development

For backend setup, follow `docs/local-development.md`. On the core developer's Windows environment, the documented command from the repository root is:

```powershell
.\.venv\Scripts\python.exe -m scripts.local_stack
```

API documentation: `http://127.0.0.1:8000/docs`
Schema: `http://127.0.0.1:8000/openapi.json`

The customer application is tracked in `apps/customer_dashboard/` on the `feat/customer-dashboard-ui` branch and is under review in [draft PR #1](https://github.com/Mrl-slll/greentokens/pull/1). It uses Next.js 16.4.6, TypeScript, ESLint and Tailwind CSS. The following commands were verified on Windows PowerShell:

```powershell
cd apps\customer_dashboard
npm.cmd run lint
npm.cmd run build
npm.cmd run dev -- --hostname 127.0.0.1
```

The development server was accessible at `http://127.0.0.1:3000`; the customer dashboard was rendered and visually inspected in the browser. A second `npm run dev` instance is unnecessary while one is already running. The production-only npm audit reported zero vulnerabilities; the full audit reported seven moderate findings through development tooling. Review dependency updates before applying them.

The proxy allows the documented customer API routes under `/api/core/` and forwards them to `http://127.0.0.1:8000` on the same machine. The blocked `/api/core/v1/workers` route returned HTTP 404. The `/api/core/health` request returned HTTP 502 while the local FastAPI backend was offline. No live job or result has been verified. For a fresh checkout, run `npm.cmd ci` in `apps/customer_dashboard/` before the commands above. Do not copy virtual environments or credentials between machines.

## Completion criteria

The customer MVP is ready for review when both input modes run successfully against the real backend, job and result data remain isolated between development identities, unsupported API calls are absent, error conditions have useful feedback, and a teammate can reproduce the demo using the written setup instructions. Frontend test results and a live walkthrough must accompany the handoff.

## Backend implementation and handoff references

- [Local development and API instructions](docs/local-development.md)
- [Frontend teammate handoff](docs/applications-handoff.md)
- [Architecture](docs/architecture.md) and [security boundaries](docs/security-boundaries.md)
- [Recorded Milestones 2-3 validation](docs/validation-milestones-2-3.md)
- [Original environment and Ray smoke-test setup](docs/core-setup-history.md)

The backend uses a local development identity stub. Production startup is blocked; real authentication and public deployment remain future work.
