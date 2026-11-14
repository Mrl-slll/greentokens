# GreenTokens

GreenTokens is a compute platform for submitting approved workloads, monitoring execution, and retrieving results. The customer application is the first frontend deliverable. A hardware-provider application is planned separately.

## Project scope

The existing local backend uses FastAPI, MySQL, Ray Jobs/Core, and S3-compatible storage (SeaweedFS in development). The initial workload is `sum_numbers_v1`, executed on a trusted local CPU worker. The backend currently runs in the core developer's environment; its source and setup instructions need to be available in this repository before live frontend integration.

**First deliverable:** A customer can submit `[1, 2, 3, 4]`, receive a job ID, follow its actual status, and view the result `10`. The complete customer MVP will also accept an uploaded JSON input file and support job history, results, logs, cancellation, and usage information.

Public accounts, GPU workloads, payments, provider agents, and installer software are outside the current customer MVP. Any provider screens are prototypes until backend support exists.

## Team ownership

| Area | Owner | Deliverables | Primary files |
| --- | --- | --- | --- |
| Customer interface | **Frontend A** | Navigation, dashboard, submission form, job detail, results, usage, settings, responsive styles, accessibility | `apps/customer_dashboard/` pages, components, styles |
| Frontend integration | **Frontend B** | API contracts/client, local proxy, mock fixtures, job polling, browser-local job IDs, identity switching, error handling, integration tests | `apps/customer_dashboard/` API, state, test modules |
| Backend | **Core developer** | Existing source and setup, API behavior, job execution, storage, resource policy, provider-agent work | `core/`, `scripts/`, `infrastructure/`, backend docs |
| Final integration | **Frontend A + B** | Connect components to real data, test end-to-end flows, review and document the demo | Shared |

**Handoff between A and B:** Frontend B defines typed response contracts and exposes adapter functions. Frontend A uses those functions through agreed component interfaces; neither developer changes the other's modules without coordination. The core developer owns backend modifications.

## Delivery order

| Priority | Deliverable | Acceptance |
| --- | --- | --- |
| **P0** | Local customer dashboard + inline job | A real `sum_numbers_v1` submission returns `10` through the frontend |
| **P1** | Complete customer MVP | JSON upload, recent jobs, results/artifacts, cancellation, usage, and identity isolation work |
| **P1** | Quality and documentation | Tested error cases, accessible layouts, reproducible setup, screenshots, and demo walkthrough |
| **P2** | Provider interface prototype | Clearly simulated onboarding, hardware, preferences, and pause states |

## Task checklist

### P0 — Repository and setup

- [ ] **Core:** Add the existing backend code, `AGENTS.md`, `docs/applications-handoff.md`, and local setup documentation to the shared repository. Exclude credentials, `.env`, `.venv`, storage volumes, and private datasets.
- [ ] **Core:** Confirm the backend API contract and the command for starting the local stack.
- [ ] **A + B:** Agree on `apps/customer_dashboard/`, the framework and approved dependencies. The handoff proposes Next.js, React, and TypeScript; check project rules before installing packages.
- [ ] **A + B:** Use separate feature branches and review changes before merging. Agree on component props and adapter function signatures.
- [ ] **B:** Start the backend in an approved local environment and verify `GET /health`. The backend developer's `127.0.0.1` is not accessible from another computer.
- [ ] **B:** Create run instructions for the frontend, including required environment setup and how to switch between mock and live modes.

### P0 — Customer screens (Frontend A)

- [ ] Create the app shell with persistent navigation and a prominent **New job** action.
- [ ] Build the **Dashboard** with recent browser-known jobs, status labels, and a link to each job.
- [ ] Build **New job** with the single supported template, `sum_numbers_v1`, and an inline integer-input form.
- [ ] Validate 1–1,000 integers, each from -1,000,000,000 to 1,000,000,000; reject non-integers and malformed input before submission.
- [ ] Display the initial resource configuration: 1 CPU core, 0.125 GB RAM, 0 GPUs, `trusted_cpu`, 60-second maximum runtime. Do not expose unsupported resource controls.
- [ ] Build **Job detail** with job ID, actual status, attempts, timestamps, errors, and cancellation state.
- [ ] Build **Results** with the returned value and available artifact/log links.
- [ ] Add explicit **Local development - identity stub** and **Mock/Live** indicators.
- [ ] Provide keyboard-accessible controls, visible focus, field errors, text-based statuses, and usable narrow-screen layouts.

### P0 — API and state (Frontend B)

- [ ] Define TypeScript types for job submission, job detail, statuses, attempts, artifacts, results, and usage, matched to the backend implementation.
- [ ] Build separate mock and live implementations behind one typed client interface. Mock responses must never be displayed as live jobs.
- [ ] Implement a same-origin frontend server proxy (for example, `/api/core/...`) targeting only `http://127.0.0.1:8000`. Allowlist paths and HTTP methods, validate IDs, limit request sizes, and preserve upstream status/content type.
- [ ] Attach `X-Dev-User` with the selected development identity (`alice` or `bob`) to backend requests. Do not place `organization_id` in submission payloads.
- [ ] Implement `POST /v1/jobs` using a new `idempotency_key` per distinct submission. Preserve the identical key **and body** when retrying an uncertain response.
- [ ] Keep the actual `job_id` returned by the backend and load `GET /v1/jobs/{id}`; do not invent an ID or status.
- [ ] Poll active jobs approximately every 2 seconds; stop on terminal status, navigation, or identity change. Abort stale requests and back off on connection errors.
- [ ] Fetch `GET /v1/jobs/{id}/result` after success. Normalize timezone-less API timestamps as UTC.
- [ ] Save a bounded list of known job IDs per development identity in browser storage. Refetch details by ID on reload; there is no job-list endpoint.
- [ ] Cancel in-flight requests and clear visible/cached data when switching identities before loading the newly selected identity's jobs.

### P0 — First integration (Frontend A + B)

- [ ] Connect the New Job form to the live submission adapter and display the backend's returned job ID.
- [ ] Connect the detail view to actual job states: `QUEUED`, `DISPATCHING`, `RUNNING`, `SUCCEEDED`, `FAILED`, `CANCELLED`.
- [ ] Submit `[1, 2, 3, 4]` through the frontend, wait for `SUCCEEDED`, and display the actual result `10`.
- [ ] Refresh the job page and verify that the known job loads again from the API.
- [ ] Switch from `alice` to `bob` and verify that Alice's visible job and result data are cleared.
- [ ] Record the setup commands and a screenshot or short walkthrough of the live flow.

### P1 — Uploads, artifacts, cancellation, and usage

**Frontend A**

- [ ] Add a JSON-file input option to New Job, with file-size and validation errors.
- [ ] Add output download controls, artifact metadata (size, SHA-256, expiration), and plain-text log views.
- [ ] Add a **Cancel job** action and a distinct **Cancellation requested** state.
- [ ] Add **Recent jobs on this browser**, with appropriate empty and unavailable states.
- [ ] Add **Usage** showing actual attempts and elapsed wall time, clearly marked nonbillable.
- [ ] Add **Settings** with mock/live selection and development identity; no account profile or payment settings.

**Frontend B**

- [ ] Accept JSON input files of at most 65,536 bytes; validate their `values` content against the inline-input constraints.
- [ ] Upload the file as raw JSON using `POST /v1/artifacts`, then submit the returned `input_artifact_id`. Do not use multipart form upload or combine file and inline input.
- [ ] Do not automatically repeat an artifact upload if the response is uncertain; uploads have no idempotency contract.
- [ ] Fetch output/input artifacts and text logs through `GET /v1/artifacts/{id}` using the same authorized proxy. Use safe download filenames and release temporary object URLs.
- [ ] Call `POST /v1/jobs/{id}/cancel`; continue showing/polling the backend status until cancellation is confirmed.
- [ ] Fetch `GET /v1/usage` and expose only returned `attempts`, `wall_seconds`, `billable`, and `measurement` values.
- [ ] Handle expired outputs independently of job status: a completed job remains `SUCCEEDED` if its result is no longer available.

**Joint acceptance**

- [ ] Submit an uploaded JSON file containing `{"values":[1,2,3,4]}` and retrieve result `10` from the real backend.
- [ ] Verify Alice's job, result, and artifact IDs are not accessible under Bob's identity (expected `404`).
- [ ] Verify cancellation is presented as a request until the backend confirms the actual outcome.

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

### P2 — Provider interface prototype (Frontend A; review with Core)

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

After the core developer has added the backend and setup files, follow `docs/local-development.md`. On the core developer's Windows environment, the documented command from the repository root is:

```powershell
.\.venv\Scripts\python.exe -m scripts.local_stack
```

API documentation: `http://127.0.0.1:8000/docs`  
Schema: `http://127.0.0.1:8000/openapi.json`

The frontend toolchain and start command will be documented here after the package manifest is approved and committed. Do not copy virtual environments or credentials between machines.

## Completion criteria

The customer MVP is ready for review when both input modes run successfully against the real backend, job and result data remain isolated between development identities, unsupported API calls are absent, error conditions have useful feedback, and a teammate can reproduce the demo using the written setup instructions. Frontend test results and a live walkthrough must accompany the handoff.
