# Development security boundaries

- Only this trusted host is supported. All published ports bind loopback. The
  observed Windows Ray listeners also bind loopback; verify this again if changing
  OS, Ray configuration, or deployment topology.
- `X-Dev-User` is a development selector, not secure authentication. Production
  startup is disabled. Local processes are trusted; never expose this API through
  a reverse proxy/tunnel or put sensitive customer data in this pilot.
- The only execution template is `sum_numbers_v1`. Inputs are bounded integers
  in JSON. No customer Python, shell commands, model downloads, or repository
  execution is supported.
- Organization checks cover jobs, input references, outputs, logs, cancellation,
  and usage. Foreign identifiers return 404. Workers are admin-only.
- Resource checks use server-registered logical capacity and heartbeat freshness,
  not customer hardware claims. Requests do not provide memory/CPU isolation.
  GPU/multi-node/provider registration is outside these milestones.
- Service credentials are held in memory and local container configuration. They
  are not source files or API responses. Anyone controlling Docker or this host
  can access them; no hostile workload is permitted in Ray.
- API request bodies are not logged. Job logs contain operational metadata, and
  job exceptions emit their type rather than secret-bearing exception text.
- The database and S3 use dedicated persistent local volumes. Expiry blocks API
  access but does not erase stored bytes. Backups, deletion policy, encryption at
  rest, secret rotation, real authentication, rate limiting, and public tenancy
  need separate implementation and review before production.
- Ray ObjectRefs are temporary execution handles only. Durable attempts and Ray
  submission IDs live in MySQL. Lost/ambiguous execution is failed, not blindly
  retried. Usage is uniquely recorded per attempt and is always nonbillable.
