# Workloads: the code that performs computation

[System guide](../../README.md) · [Execution](../jobs/README.md)

An **approved workload template** is a fixed implementation with validated parameters. The caller chooses a template and data, not a shell command or arbitrary repository. This bounds the execution surface while the platform is a trusted pilot.

## Workload map

| Template / source | Purpose | Runtime and limits |
| --- | --- | --- |
| `sum_numbers_v1`, Ray runner | Add bounded integers; connectivity test | One Ray CPU task |
| `linear_regression_v1`, `../training.py` | Fit a line and return slope/intercept/error | One Ray CPU task; paired finite JSON arrays |
| `bert_tiny_ddp_v1`, `bert_tiny.py`, `ddp.py` | BERT-tiny/SST-2 across trusted Ray nodes | Development Ray path; 1–8 requested workers with capacity checks |
| `text_finetune_v1`, `packages/text_finetune/workload.py` | Sentiment fine-tuning of approved BERT-tiny/mini/small | One independent provider; CPU or requested usable NVIDIA GPU |
| `distilbert_four_pc_test_v1`, `packages/distilbert_four_pc/workload.py` | One shared DistilBERT model across four pinned providers | Operator-only local experiment; not accepted by ordinary `Submission` |

`../api/schemas.py` is the general submission contract. The experiment constructs jobs through its own operator route. A name appearing in `PROVIDER_TEMPLATES` does not automatically make it public-submission input.

## Why the ML libraries are here

PyTorch provides tensors, automatic differentiation and optimizers. Transformers provides pretrained model architectures/tokenizers and model serialization. Datasets provides dataset loading and splits. These libraries run in the worker environment; the API routes do not perform model training.

Fine-tuning adapts an existing pretrained model. It is different from training a language model from scratch. These tasks classify sentiment, not general chatbot responses. Model checkpoints save learned parameters; a returned accuracy metric is evidence only for the evaluation procedure and dataset used.

## Two forms of distributed training

The Ray development implementation uses `STRICT_SPREAD` placement so selected workers are placed on separate Ray nodes. A reducer coordinates object references and transfers arrays through Ray rather than using a generic cross-platform Gloo/NCCL process group. `sync_every == 1` averages gradients each step; larger values average models periodically (local SGD).

The current four-PC HTTPS implementation trains locally for up to `sync_seconds` (240 in the recorded setup), transfers bfloat16 weight changes, averages on remote rank zero and verifies FP32 shared-weight hashes at barriers. Communication uses the operator API and files. It is not the same algorithm or transport as the Ray path. See [experiment evidence](../../experiments/four_pc_cpu/README.md).

## Package distribution

`../api/provider.py:build_package` creates a deterministic ZIP from an allowlisted package folder and returns a checksum. The provider checks the package and runs `workload.py` as a subprocess. Package bytes are cached in the API process, so edits to workload files may require an API restart before new assignments serve new bytes.

The package protocol lets approved workload code change without necessarily rebuilding the desktop UI. It does not update the installer's embedded API hostname, its native bridge or its runtime dependencies. Those are different release boundaries.

## Adding or modifying a workload

Coordinate parameter validation, worker admission, template-to-package/driver mapping, output schema, resource/time limits and clients. Define cancellation and retry behavior. For multi-worker work, define membership, barriers, failure handling and evidence of contribution. Do not advertise arbitrary code execution or GPU isolation just because one approved GPU template runs.

Run focused schema/runtime tests and a controlled real workload when needed. Record dataset size, split, seed, model/version, timing boundaries and checkpoint verification; do not turn a historical accuracy result into a general performance guarantee.
