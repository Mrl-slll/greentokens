# Current security and trust boundaries

Reviewed against the current checkout on 19 November 2026. This replaces the older sum-only/local-only description. [System guide](../README.md) · [Backend](../core/README.md)

## Network and identities

- `GT_MODE=development` is required; production mode is rejected by configuration. Service endpoints for database/storage/Ray are required to be loopback.
- The API rejects direct nonloopback peers. Public provider/customer traffic reaches it through a local reverse-tunnel connector.
- Proxy-header detection disallows `X-Dev-User` fallback on tunneled requests. Direct local selectors remain deliberately insecure development identities. Deployment must preserve this proxy boundary; local processes on the host are trusted.
- Provider signup/login/logout is implemented with salted scrypt password hashes, hashed device-bound 24-hour sessions, request-size limits and database-backed throttling. It is not a customer/admin signup flow.
- Customer/operator API keys are separate mappings to existing users. Do not expose those mappings or raw keys in repository files, logs or chat.
- CORS allows specified desktop/development origins; the Tauri webview also has a connection policy. Neither policy replaces server authorization.

## Authorization and execution

Jobs, results, cancellation and normal artifacts are organization-scoped. Worker inventory is admin-only. Providers cannot submit customer jobs; they operate owned devices and assigned attempts. Public provider registration does not establish that the hardware owner or computation is trustworthy.

The backend accepts approved templates, not arbitrary customer repositories or shell commands. Model/data downloads are implemented inside approved training workloads. Ray and provider subprocesses do not implement hostile-code containment. CPU/RAM declarations and reported GPU capacity are not physical resource isolation or hardware attestation.

Normal provider completion requires an output artifact record but does not independently prove correct training. Hashes establish byte consistency, not scientific correctness or honest computation. The four-PC experiment assumes trusted participants and verifies synchronized final weights, not independent attestation.

## Secrets and persistence

The launcher keeps generated service credentials in memory and dedicated container configuration. Docker/host administrators can access them. Provider session credentials are passed to subprocess environments and remain sensitive to local administrators. Avoid environment dumps, command-line credentials, full container inspection and resolved Compose configuration in shared output.

Passwords and session tokens are not intentionally persisted in plaintext by the provider account/client flow. Local account-provisioning workflows may create sensitive operator files outside the repository; their presence is not permission to print them.

Normal artifacts expire for API access after the configured TTL, but physical cleanup is not guaranteed. Model artifacts have a larger size allowance than ordinary JSON/log payloads. Database, object volumes and experiment files are not automatically backed up or replicated. Encryption-at-rest, retention/deletion operations and recovery procedures require separate work.

## Development versus production readiness

Authentication now exists for remote providers and bearer clients, but the system is still a pilot. Password recovery, durable client sign-in, complete public customer identity, billing, hostile-provider verification, unattended service recovery and a permanent API origin are not implemented as a complete product.

The local Next.js dashboard uses development identities and must not be treated as a production customer portal. Public health checks report API/database availability only. A passing health route does not prove authorization, worker correctness or artifact durability.

Use [tests](../tests/README.md) to verify the specific boundary changed. Before altering proxy topology, bindings, account roles or workload permissions, review the corresponding checks rather than assuming the old deployment assumptions still hold.
