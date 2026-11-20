# Four remote PCs training one DistilBERT model

[System guide](../../README.md) · [Experiment scope](../README.md) · Workload source: `core/workloads/packages/distilbert_four_pc/workload.py` (local-only implementation)

Status: completed in the recorded local run. See the local measured report under `runs/<run-id>/README.md`. Run artifacts are ignored local files and may be absent in another checkout; their absence is not evidence of a new successful run.

## What this experiment does

Four named provider computers fine-tune replicas of `distilbert/distilbert-base-uncased` for positive/negative IMDB review classification. This is full-model fine-tuning of a pretrained classifier, not training a general language model from scratch. Each machine processes a disjoint shard; periodic synchronization produces one shared model.

the development PC hosts API, MySQL job tracking, an authenticated file relay and timing/state. It performs no model forward/backward pass or averaging. Remote rank zero performs averaging and evaluation.

## Participants and configuration

| Computer | Rank | Role |
| --- | --- | --- |
| provider-rank-0 | 0 | Train own shard, average updates, evaluate and save model |
| provider-rank-1 | 1 | Train own shard and synchronize |
| provider-rank-2 | 2 | Train own shard and synchronize |
| provider-rank-3 | 3 | Train own shard and synchronize |
| the development PC | none | API, relay, metadata and output storage |

The names above are documentation placeholders. The current local operator route still pins device IDs after matching deployment-specific hostnames and requiring online providers with at least 12 GB reported RAM. It rejects ambiguous/missing matches and a second active shared test. This is deliberately specific to the experiment, not a generic dynamic cluster API.

Current configuration in `core/api/shared_test.py`: 12,000 seed-42-shuffled IMDB training reviews, 3,000 per provider; batch size 16 per provider; max length 256; learning rate 0.00002; requested timed interval 1,800 seconds; local training rounds up to 240 seconds. `threads: 0` leaves the PyTorch default rather than enforcing the earlier four-thread plan. Read per-run `results.json` for actual runtime/thread values. The experiment job timeout is separately set in the operator route.

## Actual synchronization method

1. The operator creates one run and four device-pinned jobs through `/v1/shared-test`.
2. Existing authenticated provider agents fetch and checksum the approved package.
3. Each provider loads the same model/data setup. Rank zero publishes exact initial weights; other ranks load them. Dataset and initial-weight checks precede timed training.
4. Each provider trains locally with AdamW for the round's time budget. Different machines can perform different numbers of steps.
5. Providers encode weight changes as bfloat16 and transfer them in checksum-verified 8 MiB chunks through the operator's HTTPS relay.
6. Remote rank zero averages changes. Providers apply the shared update to a shared FP32 model representation and synchronize using hash-checked barriers.
7. Rounds continue until the timed stopping decision. Rank zero evaluates and publishes the saved model; the operator collects results and verifies final agreement.

This is **periodic local training with model-change averaging** (described in the report as local SGD / DiLoCo-style). It is not per-step synchronous gradient averaging, not Ray DDP, and not a claim to implement every detail of a published DiLoCo algorithm.

The earlier design described four fixed CPU threads, per-step FP32 gradient exchange, and roughly 2.95 GB of relay traffic per step. Those are historical design assumptions, not the final measured run. Do not use them to explain the current code or report.

## Why HTTPS relay instead of a Ray group

Independent providers already have authenticated outbound API connections, which work without inbound provider ports. The experiment reuses that connection and package protocol. This simplifies reachability across networks, at the cost of relaying large transfers through the development PC and its uplink. The providers do not become members of a shared Ray cluster. Private Ray may still be running because the operator launcher starts it.

An approved workload package can be served by the backend without rebuilding the UI if the current worker/runtime supports it. This does not mean an installer with an expired embedded API origin can connect without being updated.

## Source and data map

| Path | Responsibility |
| --- | --- |
| `../../core/api/shared_test.py` | Admin creation/status and participant relay/barrier routes |
| `../../core/workloads/packages/distilbert_four_pc/workload.py` | Provider training, synchronization and output |
| `run.py` | Operator start/status/monitor/collect commands and report generation |
| `runs/<id>/run.json` | Run settings, hosts, device/job bindings |
| `runs/<id>/state.json` | Synchronization/timing state |
| `runs/<id>/results.json` | Returned participant metrics |
| `runs/<id>/README.md` | Generated measured report |
| `runs/<id>/model/`, `trained-model.zip` | Collected model and tokenizer |
| `original/` | Original supplied material; not the current runtime package |

The API uses local files and a process-local lock. It is not ready for multiple independent API replicas sharing experiment state. Normal S3 artifact backup alone does not capture this directory.

## Recorded result, not a current availability check

The completed report records all four jobs succeeding, six synchronization rounds, 1,900.1 seconds synchronized training elapsed, 14,640 review presentations and matching final model hashes. Reported accuracy on 256 held-out reviews changed from 39.84% to 87.11%.

These figures describe one trusted run with a small evaluation sample. They do not establish lower cost, speedup, production accuracy or that these computers are online now. A start/heartbeat is not proof of training; retain results and checkpoint verification as evidence.

## Operator commands and failure semantics

Only use after the complete local experiment source is present, the backend is running it, and all four intended providers are available:

```powershell
.\.venv\Scripts\python.exe experiments/four_pc_cpu/run.py start
.\.venv\Scripts\python.exe experiments/four_pc_cpu/run.py status RUN_ID
.\.venv\Scripts\python.exe experiments/four_pc_cpu/run.py monitor RUN_ID
.\.venv\Scripts\python.exe experiments/four_pc_cpu/run.py collect RUN_ID
```

The helper uses the operator's local API path. `monitor` checks jobs, cancels remaining participants if one fails, and collects only successful results. `collect` checks result/model agreement before reporting success. Restarted participants are rejected by membership checks; generic provider requeue does not resume this collective run. A failed run requires an explicit new experiment.

Run outputs may be large. Do not commit checkpoints or credentials just to make a report link portable. Share reviewed evidence/model artifacts separately when requested. The `Status:` and `## What` markers in this overview are also used by `run.py` when updating completion status; preserve them if editing this guide.
