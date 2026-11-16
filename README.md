# GreenTokens

Run approved CPU pipelines from Python or the terminal, and inspect their data flow, status, logs, and outputs in a simple developer dashboard.

**Local MVP:** includes a sum connection test and real single-feature linear-regression training. Custom training scripts, GPU training, remote authentication, and external database connectors are not implemented. The SDK is not published on PyPI.

## Start here

1. Prepare the backend using [local development](docs/local-development.md). Keep `python -m scripts.local_stack` running on this computer.
2. Follow the [developer quickstart](docs/developer-quickstart.md) for the Python client and pipeline example.
3. Run the frontend from this repository root:

```powershell
npm.cmd ci
npm.cmd run dev
```

Open **http://127.0.0.1:3000**. The homepage explains the workflow. Choose **Settings > Live** to inspect real jobs under the same identity used by your client.

For this workspace's portable Node.js installation, first run:

```powershell
$nodeDir = (Get-ChildItem .tools -Directory -Filter 'node-*-win-x64' | Select-Object -First 1).FullName
$env:PATH = "$nodeDir;$env:PATH"
```

## How data moves

```text
Your JSON dataset + TOML configuration
  -> Python client -> FastAPI -> MySQL job record
  -> Ray CPU worker -> S3-compatible outputs/logs
  -> API ownership/integrity checks -> client or dashboard
```

Inline submission copies the dataset into the job record. Alternatively, the SDK can upload JSON into S3 and submit its artifact ID. You do not need direct access to the internal database. Artifact access expires after 24 hours; physical cleanup is not guaranteed.

## Project layout

| Path | Purpose |
| --- | --- |
| `sdk/greentokens/` | Dependency-free Python client and CLI |
| `examples/training/` | Small reproducible CPU training dataset and pipeline |
| `app/`, `components/`, `lib/` | Next.js developer guide and job views |
| `core/` | FastAPI, validation, Ray runner, MySQL and object-storage integration |
| `scripts/` | Local stack and integration verification |
| `tests/` | Backend, SDK, and frontend regression tests |

## Validation

```powershell
.\.venv\Scripts\python.exe -m unittest discover -s tests -p test_core.py
.\.venv\Scripts\python.exe -m unittest discover -s tests -p test_sdk.py
npm.cmd test
npm.cmd run lint
npm.cmd run build
```

See [developer MVP validation](docs/developer-mvp-validation.md), [frontend integration validation](docs/frontend-integration-validation.md), [architecture](docs/architecture.md), and [security boundaries](docs/security-boundaries.md). Earlier teammate assignments/checklists are preserved in [frontend team history](docs/frontend-team-checklist-history.md); they are not the current product status.
