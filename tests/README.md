# Testing: what each check proves

[System guide](../README.md)

Unit tests isolate behavior with temporary databases/fake transports; integration checks exercise real services; acceptance tests verify the actual user path on another machine. Passing one category does not replace the others.

| Check/source | Scope | Does not prove |
| --- | --- | --- |
| `test_core.py` | Backend validation, ownership, job/reconciliation/storage logic | Real MySQL locks, public routing, native app |
| `test_sdk.py` | Local Python API client and CLI | A deployed server or published SDK |
| `test_provider_auth.py` | Signup/session/device/role behavior | Installer URL or live desktop connection |
| `test_databricks_client.py` | Adapter and result formatting | Databricks workspace permissions/egress |
| `test_shared_training.py` | Local experiment coordination behavior | Four real computers contributing useful training |
| `test_ray_smoke.py` | Ray-related smoke coverage; inspect setup before running | Full provider HTTPS path |
| Root Vitest suites | Web client, policy and component behavior | Native Tauri or real model execution |
| Provider Vitest suites | Provider UI/service flows | Native packaging and GPU drivers |
| Provider Python agent tests | Worker protocol/helpers | Hardware-specific installed runtime |

## Focused commands

From the outer repository root:

```powershell
.\.venv\Scripts\python.exe -m unittest discover -s tests -p test_core.py
.\.venv\Scripts\python.exe -m unittest discover -s tests -p test_sdk.py
.\.venv\Scripts\python.exe -m unittest discover -s tests -p test_provider_auth.py
.\.venv\Scripts\python.exe -m unittest discover -s tests -p test_databricks_client.py
.\.venv\Scripts\python.exe -m unittest discover -s tests -p test_shared_training.py
npm.cmd test
npm.cmd run typecheck
npm.cmd run lint
npm.cmd run build
```

Select checks for the files/behavior changed; do not launch every environment-heavy test for a documentation edit. Provider frontend checks run from `apps/provider_app` using its own package scripts. The agent suite can run via Python unittest discovery in `apps/provider_app/src-tauri/agent` with pattern `test_gt_agent.py`.

## Real services

`python -m scripts.local_stack --verify` owns local API/Ray ports, migrates/seeds services, submits real jobs and exercises restarts. It must not collide with an ordinary stack. `verify_developer.py` and `verify_frontend.py` provide additional local acceptance paths; inspect their startup assumptions before running.

SQLite unit tests do not reproduce MySQL's advisory locks/transaction behavior. Mocked storage does not prove a real object survives restart. A successful public health request tests neither provider login nor model execution.

## Remote acceptance evidence

For a provider release, record the source commit, configured public origin, version, installer checksum, real machine sign-in, heartbeat, approved job completion and stop/reconnect behavior. Verify result retrieval and isolate tests from other active jobs. Do not print credentials or reuse real user passwords as fixtures.

For shared training, record participating device IDs/hostnames, shards, timing definition, algorithm, synchronized model hashes and result artifacts. Reports under ignored experiment run directories are local evidence, not automatically available in a GitHub checkout.
