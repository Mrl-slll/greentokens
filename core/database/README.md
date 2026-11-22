# Database: durable metadata and identity

[System guide](../../README.md) · [Backend](../README.md)

## Purpose and tool choice

MySQL is a **relational database**: structured rows, foreign keys, transactions and locks preserve relationships even when API processes restart. The project uses it as both metadata store and durable queue. SQLAlchemy is the Python ORM/query layer, PyMySQL is the connection driver, and Alembic is the schema migration tool. These are separate responsibilities, not three databases.

This design lets a request persist before execution begins. It avoids treating Ray's temporary object references or browser state as the source of truth. It also makes database availability a dependency of login and submission.

## Source and tables

`models.py` defines ORM mappings; `session.py` creates engines/sessions; `migrations/` defines schema history.

| Table/model | What it stores and why |
| --- | --- |
| `organizations` / Organization | Ownership/tenant boundary for customer resources |
| `users` / User | Organization membership and role |
| `provider_logins` / ProviderLogin | Unique username, user ID and salted password hash |
| `provider_sessions` / ProviderSession | Session hash, user, device and expiry; no plaintext token |
| `auth_throttles` / AuthThrottle | Hashed throttle scope, window and attempt count |
| `workers` / Worker | Device/node ID, kind (`ray` or `provider`), owner, heartbeat, pause/trust and capacity |
| `jobs` / Job | Requested template, parameters, requirements, state and idempotency identity |
| `job_attempts` / Attempt | Individual execution, runtime ID, assigned worker, timestamps, errors and provider lease |
| `artifacts` / Artifact | Ownership, object key, checksum, size, kind and expiry; not the file bytes |
| `usage_records` / Usage | One record per finished attempt, elapsed time, nonbillable flag |

A job may have several attempts. Provider loss can create a new attempt for the same job; it must not look like a second customer submission. `ray_submission_id` is also used for provider attempts with a `prov-` prefix, despite the historical field name. Do not interpret every value as an actual Ray job.

```text
Organization → User → ProviderLogin / ProviderSession
Organization → Job → Attempt → Artifact / Usage
Worker ← assigned Attempt
```

Some relationships are enforced by application logic rather than declared foreign keys; inspect the model before assuming SQL enforces a relationship. Timestamps are stored as naive UTC values by `now()`; frontend adapters normalize them for display.

## Concurrency and durability

- Submission locks the organization's row before quota/idempotency decisions.
- The organization/idempotency-key unique constraint rejects duplicate identities.
- Provider assignment uses transactional row locking with `skip_locked`.
- The dispatcher uses a MySQL advisory lock so only one process owns its loop.
- Attempt numbers are unique within a job; usage records are unique per attempt.

These mechanisms reduce races; they do not make remote execution exactly-once. A worker can disappear after computing but before reporting success.

## Migrations and persistence

Current migrations are `0001` (durable jobs/artifacts), `0002` (independent providers), and `0003` (provider login/session/throttling). The launcher runs Alembic upgrades before starting the API. The API does not create tables itself.

Compose maps MySQL to host `127.0.0.1:3307`, leaving another host MySQL installation alone. A named Docker volume holds database files. Stopping a container preserves it; deleting a volume destroys its contents. The launcher recovers generated credentials from labeled container configuration, so deleting containers while keeping volumes can also lose the credential association.

Do not dump database rows or inspect container environment into shared logs. Backups and restoration are not automated. A successful restart is not proof of a usable backup.

## Changes and verification

When adding a field: update the model, write a migration, consider defaults/backfill for existing rows, adjust readers/writers, and test both fresh schema and upgrade. Unit tests commonly use SQLite; they cannot establish MySQL advisory-lock behavior. Use the live pipeline verification only in a controlled local stack, as described in [testing](../../tests/README.md).
