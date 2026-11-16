# Train AI model: backend contract (TrOCR demo)

Status: **not implemented.** The customer **Train AI model** page shows this flow but keeps **Start training** disabled until each item below exists. Checked against `core/` on 15 November 2026.

## What the backend supports today

| Capability | Today |
| --- | --- |
| Job types | `sum_numbers_v1`, `linear_regression_v1` only (`core/api/schemas.py`) |
| Job states | QUEUED, DISPATCHING, RUNNING, SUCCEEDED, FAILED, CANCELLED |
| Artifacts | JSON input/output and text logs, **64 KiB maximum**, 24-hour API access |
| Workers | One local Ray node on the backend computer; `/v1/workers` is admin-only |
| Logs and metrics | Collected after the job ends; nothing streamed |
| Routing | No way to send a stage to a specific computer |

## Minimum changes for the demo

1. **Job type `trocr_finetune_v1`** in `Submission.template_id`, with fixed, server-side settings: model `microsoft/trocr-small-printed` (fallback `facebook/deit-tiny-patch16-224`), a curated sample dataset ID, and `time_budget_minutes` (default 30, bounded). No customer code.
2. **Stages inside one job**: add a `stage` field to the job/attempt record with values `preparing_dataset`, `training`, `evaluating`, `saving_model`. The job state stays RUNNING while the stage changes; the UI maps them to *Preparing dataset / Training / Evaluating / Saving model*.
3. **Stage routing with Ray custom resources**: the ThinkPad joins Ray with `--resources '{"stage_prep": 1}'` and the Mac with `--resources '{"stage_train": 1}'`; each stage is a Ray task requesting that resource. Record each stage's actual hostname and device (`cpu` / `mps`). Multi-computer Ray on Windows and macOS is experimental, and a mixed Windows+Mac cluster is untested, so this needs a two-computer test first.
4. **Large artifacts**: a `checkpoint` artifact kind stored in the existing S3-compatible storage with a much higher size limit (about 300 MB for TrOCR-small), plus a streamed download endpoint. The 64 KiB JSON limit stays for other kinds.
5. **Progress record**: `GET /v1/jobs/{id}` adds `stage`, `stage_started_at`, `steps_completed`, `last_train_loss` and participating hosts, written by the worker as it runs. Polling every 2 seconds is enough; no fabricated percentages.
6. **Evaluation report artifact**: JSON with character error rate (CER) before and after fine-tuning on the held-out set, sample counts, device, and elapsed time per stage.
7. **Time budget**: stop at the budget, save the last valid checkpoint, and finish with a clear `ended_early: true` in the report.
8. **Test the model**: `POST /v1/jobs/{id}/predict` taking one small image (for example under 2 MB, PNG/JPEG) and returning the recognized text, owner-only.

## Before a live demo

- Pre-download the model and dataset on both computers.
- Benchmark a few training steps on the Mac (MPS and CPU) to choose settings that fit in 30 minutes.
- Choose a dataset whose license allows this use, with about 100 training images and a separate evaluation set.
