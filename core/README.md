# Backend: API and control plane

[System guide](../README.md) · [Database](database/README.md) · [Execution](jobs/README.md) · [Storage](artifacts/README.md)

## What this component is

The backend is the **control plane**: it accepts requests, checks identities and inputs, persists jobs, assigns provider work, and exposes results. It is a Python application served by Uvicorn using the FastAPI framework. An API is a machine-facing HTTP interface, so both a desktop agent and a notebook can call it without opening the website.

FastAPI fits this role because route functions, dependency-injected identity checks and typed request models keep policy close to the operation. Pydantic validates data before that operation runs. Neither tool schedules training by itself. Ray and provider processes perform the computation.

## Entry points and source map

| File | Responsibility |
| --- | --- |
| `api/main.py:create_app` | Application factory, middleware, common identity resolver, job/artifact/worker/usage routes |
| `api/schemas.py` | Strict request models, accepted templates, parameter and resource bounds |
| `api/provider_auth.py` | Signup/login/logout, password hashing, device sessions and throttling |
| `api/provider.py` | Heartbeats, transactional work assignment, package download, lease renewal and completion |
| `api/shared_test.py` | Local operator-specific four-PC experiment API; not the general submission contract |
| `config.py:Settings.from_env` | Required development mode, database/storage endpoints and bearer-key mapping |
| `database/session.py` | Database engine/session construction |
| `jobs/dispatcher.py` | Separate background reconciliation process |

An **application factory** builds the app after configuration is available. Tests can supply alternative settings, sessions and storage. Production-like local startup uses `scripts.local_stack`, which prepares credentials and services before starting Uvicorn with `core.api.main:create_app --factory`.

## Configuration reference

| Variable / default | Meaning and owner |
| --- | --- |
| `GT_MODE=development` | Required explicit mode; other values reject startup |
| `GT_DATABASE_URL` | SQLAlchemy database connection string; secret-bearing, prepared by launcher |
| `GT_S3_ACCESS_KEY`, `GT_S3_SECRET_KEY` | Storage credentials; prepared/recovered by launcher, never print them |
| `GT_S3_ENDPOINT` | Defaults to loopback port 8333 |
| `GT_RAY_ENDPOINT` | Defaults to loopback port 8265 |
| `GT_API_KEYS` | Optional JSON mapping of bearer-key hashes to user IDs; not a list of raw credentials |
| `Settings.bucket` | Default `greentokens`; a Python settings field, not automatically an environment override |
| `Settings.artifact_ttl_seconds` | Default 86,400; expiry enforcement, not physical deletion |
| `Settings.max_bytes` | Default 65,536; ordinary payload bound, with model-kind exception in storage code |

Do not assume every dataclass field has an environment-variable override; `from_env()` defines the actual supported inputs. `.env.example` is a reference rather than an automatically loaded configuration source.

## Main HTTP contracts

| Method and route | Caller / function |
| --- | --- |
| `GET /health` | API/database check and authentication-mode markers |
| `POST /v1/jobs` | Customer/admin submits a validated approved job; providers are rejected |
| `GET /v1/jobs/{id}` | Organization-scoped status, attempts and artifact metadata |
| `GET /v1/jobs/{id}/result` | Successful result JSON; 409 before success |
| `POST /v1/jobs/{id}/cancel` | Records cancellation intent; does not prove immediate process exit |
| `POST /v1/artifacts` | Bounded sum or regression JSON upload |
| `GET /v1/artifacts/{id}` | Authorized, integrity-checked artifact bytes |
| `GET /v1/workers` | Admin inventory |
| `GET /v1/usage` | Organization usage, not billing |
| `POST /v1/provider/auth/signup`, `/login`, `/logout` | Provider accounts and device sessions |
| `POST /v1/provider/heartbeat`, `/work` | Provider registration/capabilities and long polling |
| `GET /v1/provider/packages/{name}` | Approved package ZIP and checksum |
| `POST /v1/provider/work/{attempt}/lease` | Lease renewal and continue/cancel response |
| `PUT /v1/provider/work/{attempt}/artifacts/{kind}` | Attempt-owned output upload, with device ID query parameter |
| `POST /v1/provider/work/{attempt}/complete` | Attempt completion |
| `/v1/shared-test...` | Separate admin/participant experiment routes |

Local `/docs` provides generated API documentation. The middleware hides non-`/v1/` routes other than `/health` from detected proxy requests, so exposing the tunnel does not imply public Swagger UI.

## Identity and authorization

There are three identity mechanisms:

1. Direct local calls may use seeded `X-Dev-User` selectors. These are development conveniences, not secrets.
2. Provider login creates a random bearer session. MySQL stores its hash, expiry and device ID. Passwords use salted scrypt; login has database-backed throttles and bounded concurrent password hashing. The session lifetime is 24 hours.
3. Customer/operator bearer keys map a key hash to an existing user. `Settings` loads mappings from environment and, if present, the operator's external local key file. Do not print that file.

The resolver tries a provider session first and then an API-key mapping. Organization ownership is taken from the resolved user, not trusted from request JSON. Foreign object identifiers generally return 404 to avoid exposing another organization's records. Provider work assignment is intentionally cross-customer scheduling; providers can operate only their assigned device/attempt, not browse customer data arbitrarily.

The API binds loopback and rejects nonloopback peers. Cloudflared is local, so its connections arrive as loopback. Proxy headers trigger the rule requiring bearer authentication. This is a **trusted reverse-proxy boundary**, not a claim that any arbitrary proxy or public bind is safe. See [security](../docs/security-boundaries.md).

## Validation, durable submission and errors

`StrictModel` forbids extra fields. A submission selects a known template and exactly one of inline parameters or an input artifact. Organization row locking serializes quota/idempotency checks. `(organization_id, idempotency_key)` is unique: a matching repeated request returns the existing job; different content under the same key returns 409. At most 20 nonterminal jobs per organization are admitted through the general submit route.

Useful distinctions: 401 means credentials failed; 403 means the role/origin is not allowed; 422 means input/capability validation failed; 429 means a queue or authentication limit; 409 means a state conflict. Validation responses deliberately avoid reflecting submitted secrets. A network failure before receiving a response does not prove submission failed—retry with the same key.

## Running, diagnosing and changing

Start through [the launcher](../scripts/README.md), not a bare Uvicorn command without prepared environment. `/health` executes a database query; it does not exercise S3, Ray execution, provider login or the public tunnel. Check each boundary independently.

To add an ordinary template, coordinate `schemas.py`, worker admission, dispatch/package selection, runtime, client/UI affordances and tests. To change account/session fields, coordinate ORM models and Alembic migrations. Do not change the API to `0.0.0.0` merely to fix an expired tunnel URL.

Relevant tests: `tests/test_core.py`, `tests/test_provider_auth.py`, `tests/test_shared_training.py`. Existing local experiment imports mean a partial copy of edited `main.py` without `shared_test.py` will fail startup. Commit/deploy a coherent set when separately authorized.
