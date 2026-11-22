# Local CPU training result ? 14 November 2026

Successfully fine-tuned the feature branch's BERT-Tiny example on this computer. This is a single-computer CPU run, separate from the GreenTokens API and Ray jobs.

| Item | Recorded value |
| --- | --- |
| CPU | AMD Ryzen 7 PRO 5850U, 8 cores / 16 logical processors |
| Training threads | 2 |
| Python | 3.12.10 |
| PyTorch | 2.15.0+cpu |
| Transformers | 4.57.6 |
| Datasets | 4.8.5 |
| Training samples | 999 SST-2 samples, seed 42 |
| Epochs / batch size | 3 / 24 |
| Validation samples | 872, separate from training |
| Validation accuracy | 63.7615% |
| Training-loop wall time | 48.97 seconds |
| Training process CPU time | 95.23 seconds |
| Measured pipeline time | 55.83 seconds |
| Epoch training losses | 0.6805, 0.6642, 0.6377 |
| Checkpoint reload | Passed |

Pipeline timing starts after library imports and excludes dependency installation. This full run used downloads cached by the earlier 30-example smoke test. It is not a first-install elapsed-time benchmark.

Saved model: `bert-tiny-run-20261114-170717/model.safetensors`. Tokenizer/config files and `metrics.json` are in the same directory. The full checkpoint directory is needed for reload.

Reloaded-model prediction: ?This movie was wonderful.? ? POSITIVE, probability 0.6518. This is one sample prediction, not the validation accuracy. Accuracy is a small baseline and is not a production-quality claim.

## Run again from the repository root

```powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass -File scripts/train_cpu.ps1
```

For a 30-example, one-epoch installation check, add `-SmokeTest`. Each run creates a new timestamped output directory. The wrapper uses the isolated `.tools/bert-tiny-venv` environment and two CPU threads by default. No GPU or Ray cluster is used.

Exact installed package versions are recorded in `requirements-windows-cpu.lock.txt`. On another Windows x64 computer with Python 3.12, install its CPU PyTorch version from the official CPU wheel index first, then install that lockfile in a fresh environment. Other operating systems need separately verified wheels.

Model/cache files are excluded from Git by this example's `.gitignore`. No commits, pushes, or public model publication were performed.

## Demo checkpoint — larger run (14 November 2026)

The `/demo` page and `scripts/predict_cpu.py` automatically use the newest `bert-tiny-run-*` directory whose `metrics.json` records a verified reload, so a new run replaces the demo model with no code change.

| Item | Recorded value |
| --- | --- |
| Checkpoint | `bert-tiny-run-20261114-171619` |
| Training samples / epochs | 30,000 SST-2 samples (seed 42) / 3 |
| Max length / learning rate / threads | 64 / 2e-4 / 8 |
| Validation accuracy | 80.05% (872 held-out samples) |
| Epoch training losses | 0.390, 0.234, 0.173 |
| Training-loop wall time | 1,014.9 seconds |
| Checkpoint reload | Passed |

Reproduce:

```powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass -File scripts/train_cpu.ps1 -Threads 8 -Examples 30000 -Epochs 3 -MaxLength 64 -LearningRate 2e-4
```

The demo API keeps one Python worker loaded: the first prediction takes about 12 seconds, later ones about 25 ms. The worker exits after 10 idle minutes.
