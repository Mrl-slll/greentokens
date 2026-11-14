# Milestones 2–3 implementation plan

Status: dependencies and dedicated local services approved by the user; SeaweedFS
4.53 selected. Implementation is in place; see local-development.md for execution
and validation records.

## Repository and runtime findings

The repository contains the proven Ray smoke script and its integration test.
There is no reusable HTTP API, persistence layer, dispatcher, or artifact client.
Ray 2.60.0 and Pydantic 2.14.3 are already installed in `.venv`. Docker Compose
5.6.1 is installed, but the Docker engine is stopped. Existing MySQL processes
are unrelated to this project; their databases and credentials must not be changed.

Use a dedicated MySQL container on a separate loopback port and a persistent
Docker volume. Use a dedicated local S3-compatible container and persistent volume.
Keep generated local credentials out of repository files, command output, and
logs. A launcher can hold credentials in memory and supply child process
environments; Docker administrators can still inspect container configuration.

## Proposed dependencies

| Package | Pin | License | Published (UTC) | Reason |
| --- | --- | --- | --- | --- |
| FastAPI | 0.162.7 | MIT | 2026-11-13 | Validated HTTP endpoints |
| Uvicorn | 0.54.0 | BSD-3-Clause | 2026-09-25 | Local ASGI server |
| SQLAlchemy | 2.1.8 | MIT | 2026-11-04 | Transactional persistence |
| PyMySQL | 1.2.4 | MIT | 2026-11-09 | MySQL driver |
| Alembic | 1.20.1 | MIT | 2026-10-22 | Versioned database migrations |
| boto3 | 1.44.3 | Apache-2.0 | 2026-11-13 | Portable S3 client |
| HTTPX | 0.28.1 | BSD-3-Clause | 2024-12-06 | FastAPI integration tests |

Metadata obtained from each package's public PyPI JSON endpoint. Retain the
already installed Ray and Pydantic versions. Use standard-library unittest
rather than introducing another test framework.

MySQL Community Server 8.4 is GPL-2.0; approval is required under AGENTS.md.
The storage comparison is limited to two candidates:

| Name | License | Maintenance evidence | Fit |
| --- | --- | --- | --- |
| [SeaweedFS](https://github.com/seaweedfs/seaweedfs) | Apache-2.0 | Current release 4.53; repository displayed 36.1k stars, 640 issues, 70 PRs | Recommended local S3 alternative; retained behind boto3 |
| [MinIO](https://github.com/minio/minio) | AGPL-3.0 | Archived April 25, 2026; repository displayed 61.3k stars, 44 issues, 34 PRs | Blueprint choice, but archive status and license require explicit selection |

Exact latest commit dates and issue resolution rates were not verified. Counts
are snapshots, not a maintenance guarantee. No third-party source will be copied.
GitHub MCP and Context7 are unavailable; use official docs and read-only source
pages. Version-specific documentation is used where available; record exceptions.

## Implementation contract

1. FastAPI runs on loopback. A development identity stub accepts only configured
   pilot identities and resolves organizations on the server. Identity is never
   accepted in a job body. Production startup with this stub is rejected.
2. Validate only `sum_numbers_v1`: bounded integer lists, either inline or an
   authorized uploaded JSON artifact, CPU-only requirements, and finite runtime.
3. MySQL owns organizations, jobs, attempts, artifact pointers, and usage. Enforce
   organization/idempotency uniqueness, attempt numbering, and one usage row per
   attempt. Reuse with changed request content returns a conflict.
4. A single dispatcher claims queued rows transactionally and commits a stable
   Ray submission ID before submission. Use the Ray Jobs API and a fixed internal
   entrypoint; customer input never becomes a command or runtime environment.
5. A reconciler polls durable submission IDs. Persist RUNNING and terminal states,
   errors, timestamps, logs, and nonbillable duration. Never silently resubmit a
   known lost execution. Initial retry limit is zero automatic retries.
6. Store input, output, and logs in S3 with organization-specific object keys,
   SHA-256, byte size, and expiry. Serve through authorized API reads that verify
   integrity. Do not expose arbitrary keys or accept customer-selected URLs.
7. Cancellation requests are persisted. Terminal updates are idempotent and
   cannot duplicate usage. Missing output is a failure even if Ray exits zero.

## Acceptance tests

- Submit inline `[1,2,3,4]`; poll to SUCCEEDED; result equals 10.
- Upload an authorized input JSON file and return its sum through the same path.
- Restart the API and confirm job records and result access remain valid.
- Deny another organization access to jobs, input artifacts, outputs, and logs.
- Reject unknown templates, arbitrary commands, unsupported GPU requests,
  excessive input, expired artifacts, and mismatched checksums.
- Check idempotency, duplicate reconciliation, cancellation, missing execution,
  failed execution, and runtime bounds.
- Run migrations against actual MySQL and inspect actual object storage results.
  SQLite/fakes can supplement unit tests but cannot prove the milestones.

## Documentation consulted

- [Ray Jobs 2.60.0](https://docs.ray.io/en/latest/cluster/running-applications/job-submission/doc/ray.job_submission.JobSubmissionClient.html)
- [SQLAlchemy 2.1 sessions](https://docs.sqlalchemy.org/en/21/orm/session_basics.html)
- [FastAPI releases](https://fastapi.tiangolo.com/release-notes/)
- [Alembic 1.20.1 tutorial](https://alembic.sqlalchemy.org/en/latest/tutorial.html)
- [Docker Compose environment](https://docs.docker.com/compose/how-tos/environment-variables/set-environment-variables/)
- [SeaweedFS 4.53 release](https://github.com/seaweedfs/seaweedfs/releases/tag/4.53)

The versioned boto3 reference URL was unavailable. PyMySQL's latest examples page
reported an older documentation version; confirm the installed driver API before
implementation. No credentials have been accessed for this planning step.
