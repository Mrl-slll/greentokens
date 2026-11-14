# Local development: Milestones 2–3

This pilot supports `sum_numbers_v1` on this trusted Windows machine. It uses
MySQL 8.4 and SeaweedFS 4.53 containers plus a host Python 3.12/Ray 2.60.0 runtime.
SeaweedFS was explicitly approved as the S3-compatible alternative to MinIO.

## Start and stop

From the repository root in PowerShell, with Docker Desktop running:

```powershell
# Initial setup only; already performed in this workspace:
.\.venv\Scripts\python.exe -m pip install -r requirements-core.txt

# Foreground local stack; leave this terminal running:
.\.venv\Scripts\python.exe -m scripts.local_stack
```

The launcher starts dedicated containers, waits for MySQL/S3, runs `alembic
upgrade head`, seeds development identities, starts Ray Jobs on loopback,
registers the local worker, and starts separate API and dispatcher processes.
Press Ctrl+C to stop API/dispatcher/Ray; the database and storage containers and
their persistent volumes remain. Stop those containers without deleting data:

```powershell
docker stop greentokens-dev-mysql greentokens-dev-storage
```

The next launcher run starts them again. Do not remove the containers or volumes
as routine shutdown: generated credentials are recovered from the named
containers' configuration. If the containers are deleted while volumes remain,
their credential configuration must be recovered separately. There is no
automatic password reset, volume reset, or data deletion.

| Service | Local address |
| --- | --- |
| API/docs | `http://127.0.0.1:8000/docs` |
| Private Ray Jobs/dashboard | `http://127.0.0.1:8265` |
| Dedicated MySQL | `127.0.0.1:3307` |
| S3-compatible API | `http://127.0.0.1:8333` |

The existing MySQL installation on the host is not modified. No firewall rules,
public listeners, paid cloud resources, or other computers are configured.

## Development identity

Send `X-Dev-User: alice` for organization A or `X-Dev-User: bob` for organization B.
`admin` belongs to A and can view worker inventory. These names are deliberately
nonsecret development selectors, not passwords or real authentication. Any local
caller can impersonate them. Never expose this API to a network or use real data.

`Settings.from_env()` requires `GT_MODE=development`; all other values, including
production, fail startup. Organization ownership is resolved from the seeded
user record, never from job request bodies. The API also rejects nonloopback
clients, and the launcher disables Uvicorn proxy-header trust.

## Submit an inline job

In a second PowerShell terminal:

```powershell
$headers = @{ 'X-Dev-User' = 'alice' }
$body = @{
  template_id = 'sum_numbers_v1'
  parameters = @{ values = @(1, 2, 3, 4) }
  requirements = @{ cpu_cores = 1; ram_gb = 0.125; gpus = 0 }
  idempotency_key = [guid]::NewGuid().ToString()
} | ConvertTo-Json -Depth 5
$job = Invoke-RestMethod -Method Post -Uri 'http://127.0.0.1:8000/v1/jobs' -Headers $headers -ContentType 'application/json' -Body $body
$jobId = $job.job_id
Invoke-RestMethod -Uri "http://127.0.0.1:8000/v1/jobs/$jobId" -Headers $headers
# Repeat the status request until SUCCEEDED, then:
Invoke-RestMethod -Uri "http://127.0.0.1:8000/v1/jobs/$jobId/result" -Headers $headers
```

The result contains `result: 10`, a job ID, and an attempt ID. Reusing the same
idempotency key and content returns the original job; changed content returns 409.
CPU/GPU/memory requirements are checked against the registered local runtime.
The example uses 128 MiB rather than 2 GiB because this tiny sum needs little
memory and Ray may have less than 2 GiB available while Docker is running.

## Submit a stored input file

```powershell
$inputJson = '{"values":[1,2,3,4]}'
$artifact = Invoke-RestMethod -Method Post -Uri 'http://127.0.0.1:8000/v1/artifacts' -Headers $headers -ContentType 'application/json' -Body $inputJson
$fileJob = @{
  template_id = 'sum_numbers_v1'
  input_artifact_id = $artifact.artifact_id
  idempotency_key = [guid]::NewGuid().ToString()
} | ConvertTo-Json
Invoke-RestMethod -Method Post -Uri 'http://127.0.0.1:8000/v1/jobs' -Headers $headers -ContentType 'application/json' -Body $fileJob
```

For an existing JSON file use `-InFile .\input.json` instead of `-Body $inputJson`.
The bounded format is `{"values":[...]}` with 1–1000 integers, each between
-1 billion and +1 billion. Maximum upload/object size is 64 KiB. Arbitrary file
formats, remote URLs, containers, commands, and code are rejected.

## Endpoints

| Endpoint | Behavior |
| --- | --- |
| `GET /health` | Database availability and identity-stub marker |
| `POST /v1/jobs` | Validate, apply queue/resource policy, persist job; 202 |
| `GET /v1/jobs/{id}` | State, attempts, timestamps, errors, artifact metadata |
| `GET /v1/jobs/{id}/result` | Authorized checksum-verified JSON result |
| `POST /v1/jobs/{id}/cancel` | Persist cancellation request |
| `POST /v1/artifacts` | Validate and store bounded input JSON; 201 |
| `GET /v1/artifacts/{id}` | Authorized checksum-verified input/output/log |
| `GET /v1/workers` | Development admin only |
| `GET /v1/usage` | Organization-scoped nonbillable attempt elapsed time |

Artifacts expire for API access after 24 hours. Expired objects remain on disk;
physical deletion, orphan-object cleanup, backups, and configurable retention
are not implemented. Outputs/logs use unique organization-specific keys.
The API proxies verified reads rather than issuing unverified public URLs.

## Tests

See [the recorded validation results](validation-milestones-2-3.md) for actual
commands, stdout, service versions, failures, and test limitations. All persisted
timestamps in this prototype use UTC.

```powershell
.\.venv\Scripts\python.exe -m unittest discover -s tests -p test_core.py -v
.\.venv\Scripts\python.exe -m scripts.local_stack --verify
.\.venv\Scripts\python.exe -m pip check
```

Stop a foreground local stack before `--verify`, which owns ports 8000/8265.
The acceptance harness starts real services, submits inline/file jobs, restarts
the API and dispatcher, verifies durable results and tenant separation, checks
concurrent idempotent submissions, and tests actual S3 integrity/expiry rejection.
It stops its API/dispatcher/Ray on exit while retaining MySQL/S3 and test records.
Core unit tests use SQLite and fake Ray/S3 for deterministic failure scenarios;
they supplement rather than replace the real MySQL/Ray/S3 acceptance test.

## Credential handling

The launcher generates random database/S3 credentials in memory on first use,
passes them through child/container environments, and reuses only the two
containers carrying the expected Compose project label. Credentials are never
printed or written into repository files. `.env.example` documents variable
names only; it is not loaded automatically. Container logging is disabled to
avoid persisting service bootstrap credentials. Local Docker administrators can
inspect container configuration; this is a trusted single-user environment.

Do not run `docker inspect` or `docker compose config` into shared logs: they can
reveal environment credentials. The launcher reads this configuration internally
and prints only readiness/status. The trusted Ray job driver inherits its service
environment; credentials are not passed as customer-visible Ray runtime metadata.

## Known boundaries

Windows Ray remains beta. The fixed Ray entrypoint uses this host's Python and
repository paths; it is not yet a portable multi-machine execution image.
Logical Ray memory/CPU admission is not OS-enforced isolation. One job is
dispatched at a time, with a maximum of 20 queued/active jobs per organization.
There are zero automatic retries: uncertain/lost execution fails visibly.
No payment or billing-grade metering exists. The identity stub must be replaced
before any authenticated pilot involving other users or sensitive data.
