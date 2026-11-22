# BERT-Tiny CPU training baseline

[中文完整操作说明](README_zh.md) · [中文队友交接说明](START_HERE_zh.txt)

This standalone experiment fine-tunes `prajjwal1/bert-tiny` for positive/negative
English sentiment classification with 999 SST-2 training examples. It provides a
single-computer baseline for a later **three-computer** Ray Train experiment.
The platform's existing four-machine milestone is separate.

## Relationship to GreenTokens

The current customer workload is `sum_numbers_v1`. Its FastAPI schema, Ray Jobs
runner, MySQL records, and S3 artifact handling do not yet support model training.
Run this example from the terminal; it is not a dashboard submission template.
No backend services, credentials, Ray cluster, Docker, or GPU are required for
this baseline. The optional ML dependencies live in a separate virtual environment.

## Run on an Apple Silicon Mac (including M4)

Install Python 3.11, then run from the repository root:

```bash
cd examples/bert_tiny_cpu
python3.11 -m venv .venv
.venv/bin/python -m pip install --upgrade pip
.venv/bin/python -m pip install 'torch>=2.6,<3'
.venv/bin/python -m pip install -r requirements.txt
.venv/bin/python download_assets.py
.venv/bin/python train_bert_tiny.py
```

The script explicitly selects CPU; it does not use Apple's MPS accelerator.
Intel Macs need a separately verified dependency setup.

## Run on Windows (Intel/AMD x64)

Install Python 3.11, then use PowerShell from the repository root:

```powershell
cd examples/bert_tiny_cpu
py -3.11 -m venv .venv
.\.venv\Scripts\python.exe -m pip install --upgrade pip
.\.venv\Scripts\python.exe -m pip install "torch>=2.6,<3" --index-url https://download.pytorch.org/whl/cpu
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe download_assets.py
.\.venv\Scripts\python.exe train_bert_tiny.py
```

The actual pretrained weights, configuration and vocabulary are included in
[`assets/model/`](assets/model/). Run `download_assets.py` once to fetch pinned
SST-2 files into the local `assets/dataset/` directory and verify all hashes.
SST-2 has unknown upstream license metadata, so raw data is not republished
on GitHub. See [asset provenance and local download instructions](assets/README.md).
After dependencies and assets are prepared, training uses local files only.
The newly initialized classification-head warning is expected when loading this
pretrained encoder for a new classification task.

## Settings and outputs

| Setting | Default |
| --- | --- |
| Training examples | 999, fixed seed 42; divisible by three |
| Epochs | 3 |
| Global batch size | 24 |
| Maximum sequence length | 128 |
| CPU threads | 2 |
| Optimizer | PyTorch AdamW, learning rate 5e-5, weight decay 0.01 |
| Evaluation | SST-2 validation split, never used for training |

A successful run prints `COMPLETE` and creates `bert-tiny-sst2-cpu/` containing
the model, tokenizer, and `metrics.json`. It reloads the saved checkpoint before
classifying `This movie was wonderful.` The predicted label and validation
accuracy are measured outputs, not guaranteed outcomes.

The report includes training-loop wall time, process CPU time, overall time
(including preparation, evaluation, saving and reload, but excluding the separate asset download),
hostname, dependency versions, pinned model/dataset revisions, the selected-data hash, and checkpoint-reload
verification. CPU percent uses 100% for one fully occupied logical core and may
exceed 100%. Model files support inference; optimizer state for exact training
resumption is not saved.

Existing output directories are rejected. To run again, use a new path:

```bash
.venv/bin/python train_bert_tiny.py --output bert-tiny-run2
```

Use the Windows interpreter path on Windows. For a short installation check,
add `--examples 30 --epochs 1 --output smoke-test`. This does not replace the
999-example performance baseline.

## Validation status

Python syntax, CLI help, argument rejection, asset integrity and downloader
regression checks have passed. All seven original model/data files were downloaded
and verified against upstream blob hashes or LFS SHA-256 digests. Only model files
are committed. The downloader also completed a fresh end-to-end download with
TLS verification enabled using the macOS system CA bundle (`SSL_CERT_FILE=/etc/ssl/cert.pem`). Training dependencies are not installed in the authoring environment;
model loading, fine-tuning, accuracy, checkpoint reload and multi-node execution
remain unverified. This example must pass a real single-machine run before being used as
a benchmark. The model and dataset content revisions are pinned; Python dependency ranges are not a tested lockfile: record resolved packages
after a successful run and use consistent versions across benchmark machines.

## Next: three real computers

Ray's supported multi-node platform is Linux. Native Windows/macOS multi-node
clusters are experimental. Determine a Linux environment on each physical
computer and verify bidirectional private connectivity; campus Wi-Fi alone does
not establish this, and a Linux VM or WSL2 does not automatically fix routing.

The next implementation should reuse Ray Train's `TorchTrainer` and PyTorch
DDP/Gloo, with one worker per physical computer, disjoint data shards, and
synchronized gradients. Record three host/node identities, ranks 0–2, CPU
activity, progress, completion, and a reloadable checkpoint. Three independent
executions of this script are not distributed training.

Keep the same dataset, initialization, epochs, learning rate, sequence length,
and global batch for timing comparisons (three workers can each use batch 8).
If the distributed setup uses Linux, rerun the single-worker baseline in that
environment. Report both training-loop and overall time, even if three workers
are slower. API integration will also require explicit template, resource,
timeout, cancellation, and artifact design with the core backend owner.

## References and reuse

- [BERT-Tiny model](https://huggingface.co/prajjwal1/bert-tiny)
- [SST-2 dataset](https://huggingface.co/datasets/stanfordnlp/sst2)
- [Ray official PyTorch CPU example reviewed for this work](https://github.com/ray-project/ray/blob/master/python/ray/train/examples/pytorch/torch_quick_start.py)
- [Ray PyTorch integration guide](https://docs.ray.io/en/latest/train/getting-started-pytorch.html)
- [Ray cluster platform support](https://docs.ray.io/en/latest/cluster/getting-started.html)

The starter uses Transformers model/tokenizer APIs, Hugging Face Datasets,
PyTorch's existing optimizer and data loader, and safetensors serialization.
There is no custom distributed protocol or vendored third-party training framework.

Downloader tests (standard library only):

```bash
python3.11 -m unittest discover -s tests -v
```
