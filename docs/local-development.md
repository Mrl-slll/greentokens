# Local development runbook

[System guide](../README.md) · [Detailed operations](../scripts/README.md) · [Containers](../infrastructure/README.md)

This page covers the operator's local backend. Remote provider execution is supported through the separate authenticated tunnel path; the local SDK and web dashboard still use development identities.

## Start

From the outer repository root, with Python dependencies installed and Docker Desktop ready:

```powershell
.\.venv\Scripts\python.exe -m scripts.local_stack
```

The launcher starts dedicated MySQL/SeaweedFS, waits for readiness, applies migrations, seeds local development users, starts private Ray, and starts separate API/dispatcher processes. Leave it running. Start the root website separately with `npm.cmd run dev`.

Verify the API:

```powershell
Invoke-RestMethod http://127.0.0.1:8000/health
```

Use [the local SDK quickstart](developer-quickstart.md) for a real sum/regression submission. The website defaults to mock mode; select Live and the same development identity to inspect real jobs.

## Addresses

| Service | Address |
| --- | --- |
| Customer UI | `http://127.0.0.1:3000` |
| API / local API docs | `http://127.0.0.1:8000`, `/docs` |
| Private Ray Jobs/dashboard | `http://127.0.0.1:8265` |
| MySQL | `127.0.0.1:3307` |
| SeaweedFS S3 | `http://127.0.0.1:8333` |

These addresses are relative to the operator PC. A remote provider needs its configured public HTTPS origin; opening the website does not start that tunnel.

## Stop and preserve data

Ctrl+C in the launcher stops its API/dispatcher/Ray. Database/storage containers remain. To stop those without deleting their volumes:

```powershell
docker stop greentokens-dev-mysql greentokens-dev-storage
```

Do not delete volumes or containers as a routine troubleshooting reset. Credentials are recovered from labeled container configuration; deleting containers while keeping volumes can require separate credential recovery.

## Checks and limitations

Use `--prepare` for service/schema preparation and `--verify` for real integration verification. Verification owns ports and restarts components; do not run it over an active ordinary stack. See [test scopes](../tests/README.md).

`.env.example` is documentation, not automatically loaded by the launcher. Credentials are generated/reused internally; do not print environment or container configuration. Ray startup can fail under low available memory, and the current launcher then cannot start the API. Read sanitized startup errors before changing configuration.

The Windows-oriented launcher and temporary tunnel are a pilot setup. Persistent address and unattended recovery remain in [the roadmap](roadmap.md).
