# Execution: dispatcher, reconciliation and Ray

[System guide](../../README.md) · [Provider worker](../../apps/provider_app/README.md) · [Workloads](../workloads/README.md)

## What runs where

`dispatcher.py` is a separate Python process. It implements a **reconciliation loop**: repeatedly compare recorded job/attempt state with actual runtime information and apply transitions. This is why a web request does not have to remain open for training to continue.

| File | Responsibility |
| --- | --- |
| `dispatcher.py:claim` | Claim eligible non-provider work and create a Ray attempt |
| `dispatcher.py:reconcile` | Check Ray status, cancellation, runtime, logs and output |
| `dispatcher.py:reconcile_provider` | Detect expired provider leases and requeue/fail work |
| `../ray_runtime/client.py` | Ray Jobs API adapter |
| `../ray_runtime/runner.py` | Fixed approved driver launched by Ray Jobs |
| `../workloads/ddp.py` | Trusted Ray multi-node training mechanics |

The driver and dispatcher are different processes. The driver computes and writes outputs; the dispatcher confirms terminal state and collects logs. `finish_attempt` records terminal status and nonbillable usage and is also used by provider completion.

## Ray execution path

The dispatcher holds a MySQL advisory lock during its lifetime and rechecks ownership each tick. The normal loop sleeps one second between ticks. It allows one in-flight Ray job in this pilot, which does not prevent independent providers from running other jobs concurrently.

The job becomes `DISPATCHING` with a durable submission ID. Submission intent is persisted before the external call. A lost/ambiguous Ray execution is reconciled by that ID or eventually failed; it is not blindly submitted again. Missing execution after the grace period becomes `EXECUTION_LOST`.

Ray's driver loads the persisted approved template and inputs, requests logical resources, and writes artifacts. The reconciler confirms output integrity before Ray success is committed. Cancellation/runtime expiry asks Ray to stop and waits for a terminal state rather than claiming the process stopped immediately. Runtime checks include a 60-second launch grace.

Ray provides remote functions, actors and placement groups. These are convenient for trusted multi-node scheduling and data exchange. They do not isolate malicious code, guarantee physical RAM/CPU enforcement, or make the cluster durable. MySQL is the durable record; Ray object references are temporary.

## Independent provider execution path

Assignment happens in `../api/provider.py`, not `claim()`. Providers poll the API and receive a package/attempt. A 90-second lease is renewed while the worker runs. If the lease expires, the reconciler either cancels, requeues, or fails after three total attempts.

A retry begins another attempt; there is no general checkpoint-resume protocol. Ordinary provider completion checks for output metadata; unlike the Ray reconciler, it is not a proof of training correctness. Artifact reads still validate hashes.

Shared four-PC training has stricter semantics: its membership checks reject a restarted participant attempt, and its monitor cancels remaining work after failure. A requeued participant is not a valid continuation of that collective experiment.

## Startup dependencies and debugging

`scripts.local_stack` starts Ray before the API. Therefore a Ray allocation/startup failure currently blocks even provider login, although HTTPS providers do not require Ray to execute. Separating service lifetimes is planned, not implemented.

Use job/attempt IDs to trace state across database, dispatcher and worker. Check worker kind (`ray` versus `provider`) before interpreting capacity. Never use a broad `ray stop` as routine troubleshooting on a machine that may host another session. See [operations](../../scripts/README.md) for scoped shutdown and [tests](../../tests/README.md) for real-service verification.
