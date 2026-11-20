# Operator checklist: remote provider pilot

[System guide](../README.md) · [Full operations guide](../scripts/README.md) · [Provider owner instructions](provider-guide.md)

## Before connecting other computers

1. Keep the operator PC awake with working internet and Docker ready.
2. Start the backend and verify local `/health`. A website on port 3000 is not this backend.
3. Verify the current public HTTPS tunnel's `/health` separately. The API stays loopback-bound behind the connector.
4. Confirm that the provider installer was built for that exact public origin and matching Tauri CSP. Changing local source or downloading the same old asset does not update an installed app.
5. Sign in and connect from a real remote computer, then inspect recent provider heartbeats.
6. Submit an approved job and verify outputs, not just the Connected indicator.

The convenience command `powershell -ExecutionPolicy Bypass -File scripts/start_server.ps1` starts/reuses backend and temporary tunnel, rewrites provider source configuration and attempts a Databricks secret update. It does not build/publish an installer. Read [its side effects](../scripts/README.md) before running it.

## During operation

```powershell
.\.venv\Scripts\python.exe -m scripts.providers
```

Check device identity, freshness, pause state and usable GPU reporting. The server counts a GPU only when the provider reports usable PyTorch CUDA. Ordinary text fine-tuning runs one job on one provider; multiple jobs can use multiple providers. The shared four-PC experiment is a separate operator workflow.

Databricks users need a customer credential and the current endpoint, plus working workspace egress/secrets. Provider credentials cannot submit customer jobs.

## Failure handling

- DNS failure: wrong/expired public address.
- Public tunnel failure with healthy local API: connector/network layer.
- Healthy API but login failure: verify installed origin, policy, credentials and session expiry.
- Login/heartbeat succeeds but work fails: inspect template, runtime, capability, lease and artifact status.

Never create a second account to fix an unreachable hostname. A hostname change does not remove accounts from the existing database.

## End of test

Stop only the processes started for this test. Do not kill unrelated tunnels or all Python/Ray processes. Stop dedicated containers if desired, preserving volumes. Save relevant job IDs/results before artifact expiry. The server PC is still a single availability dependency; permanent hosting work is [planned](roadmap.md).
