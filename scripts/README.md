# Operations and developer scripts

[System guide](../README.md) · [Infrastructure](../infrastructure/README.md)

These scripts are **orchestration and operational tooling**: they assemble services, configure environments and inspect state. They are not interchangeable with running the website or installing a provider app.

## Script map

| Script | Role and side effects |
| --- | --- |
| `local_stack.py` | Generates/recovers service credentials, starts containers, waits, migrates, seeds local users, starts Ray, API and dispatcher |
| `start_server.ps1` | Starts/reuses backend, starts/reuses temporary public tunnel, changes provider source origin/CSP, attempts Databricks URL-secret update |
| `providers.py` | Reports worker/provider inventory from the configured local database |
| `add_account.py`, `make_api_key.py` | Account/key provisioning helpers; sensitive credential workflows, not routine diagnostic output |
| `set_databricks_url.py` | Updates external Databricks configuration; not needed merely to display the local UI |
| `verify_pipeline.py`, `verify_developer.py`, `verify_frontend.py` | Live integration checks; inspect scope before running against active work |
| `provider_check.ps1`, `provider_check.sh` | Provider-environment diagnostics |
| `demo_cluster.py`, `spike_job_cluster.py`, `open_firewall.ps1` | Older trusted LAN/Ray-group experiment tooling; not the current HTTPS provider onboarding path |
| `ray_smoke_test.py` | Ray development smoke checks |
| `train_cpu.ps1`, `predict_cpu.py` | Standalone BERT baseline and inference helper |
| `run_job.py`, `terminal.ps1` | Developer convenience entry points; inspect their arguments before use |

## Default local stack

From the outer repository, with Docker ready:

```powershell
.\.venv\Scripts\python.exe -m scripts.local_stack
```

The startup order is container readiness → Alembic upgrades → development-user seed → private Ray → API and dispatcher. The launcher then publishes Ray worker heartbeats. The API binds `127.0.0.1:8000`, Ray dashboard/Jobs binds `127.0.0.1:8265`, and proxy-header trust is disabled in Uvicorn.

`--prepare` prepares services/schema/identities without running the full stack. `--attach` is a separate legacy trusted-group mode requiring an existing group code in the environment; it does not make independent HTTPS providers into Ray nodes. `--verify` owns a stack and exercises real jobs/restarts, so stop the ordinary launcher before using it.

Ctrl+C stops its API, dispatcher and Ray; containers/volumes remain. The launcher does not supervise arbitrary externally launched stacks, and it does not provide Windows boot recovery. Do not indiscriminately kill every Python, Node or Ray process.

## Remote provider test-day startup

The existing convenience command is:

```powershell
powershell -ExecutionPolicy Bypass -File scripts/start_server.ps1
```

Read its side effects first: it creates/reuses files under the operator's `.greentokens` directory, starts hidden processes, can stop existing cloudflared processes when replacing a stale tunnel, rewrites provider origin/CSP, and invokes the Databricks URL updater. It is not a narrowly scoped “start only the API” command. Use deliberate scoped steps when other tunnels or external configuration must be preserved.

It uses `cloudflared tunnel --url http://127.0.0.1:8000`, a temporary Quick Tunnel. It does **not** rebuild or publish installers. Existing providers retain the origin compiled into their installed build. Do not advertise the script's “Ready” output as proof that installed providers can connect.

## Connectivity checklist

1. Local API: `Invoke-RestMethod http://127.0.0.1:8000/health`. Expect `status: ok` and the provider-auth marker for the current implementation.
2. Public API: check `/health` on the actual current public origin. DNS failure, tunnel failure and API failure are different layers.
3. Installer: compare built origin, Tauri CSP, release version and downloaded checksum. Source configuration alone is insufficient.
4. Provider: sign in and connect on a real remote machine. Verify a recent heartbeat through `python -m scripts.providers` using the server venv.
5. Workload: submit an approved job and inspect completion/artifacts. Heartbeat or login alone is not an execution test.

Do not use placeholder origins literally, and do not paste bearer keys into shell commands or shared logs.

## Availability limitations

API startup is coupled to Ray startup even for provider-only use. Low available memory can prevent Ray from allocating its object store and thus block login. Diagnose the specific allocation error; do not silently disable memory protection or kill unrelated applications.

Current background processes, Docker Desktop, temporary hostname and operator sleep/reboot behavior make this a test-day setup. A persistent hostname, tunnel service, backend supervision, coherent backup and tested boot recovery are separate planned work in [the roadmap](../docs/roadmap.md).
