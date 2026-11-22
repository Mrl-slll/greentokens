# Training assets / 模型与数据文件

## What GitHub contains

`model/` contains the **actual pretrained BERT-Tiny weights**, configuration,
vocabulary and the upstream model card, copied byte-for-byte from
[`prajjwal1/bert-tiny`](https://huggingface.co/prajjwal1/bert-tiny/tree/6f75de8b60a9f8a2fdf7b69cbd86d9e64bcb3837).
The upstream model card declares MIT. It is retained as `model/README.md`, including
the author, original BERT attribution and requested paper citations. The source
snapshot does not contain a separate LICENSE file; no additional rights or
copyright ownership are asserted by GreenTokens.

These are starting weights, not a checkpoint fine-tuned by GreenTokens.
The 17,756,393-byte `pytorch_model.bin` is an ordinary Git blob, not an LFS
pointer; cloning or downloading this branch includes it. Load it using the
documented PyTorch >=2.6 environment.

## Dataset download

SST-2's [upstream dataset card](https://huggingface.co/datasets/stanfordnlp/sst2/blob/8d51e7e4887a4caaa95b3fbebbf53c0490b58bbb/README.md)
states **license: unknown**. Dataset files are therefore not republished in this
public Git repository. This is a provenance limitation, not a claim that the
dataset is prohibited for every use. Check upstream terms for your intended use.

From `examples/bert_tiny_cpu`, after installing the documented environment:

```bash
.venv/bin/python download_assets.py
.venv/bin/python download_assets.py --verify-only
.venv/bin/python train_bert_tiny.py
```

On Windows use `.\.venv\Scripts\python.exe` instead.
The downloader fetches the original train, validation and test Parquet splits
(3,331,058 bytes total) into `dataset/`. Those files are ignored by Git. Training
selects 999 seeded training examples and evaluates on validation; it never trains
on validation or the unlabeled test split. The downloaded test split is retained
for completeness and is not used by the training script.

`manifest.json` records immutable source revisions, URLs, exact byte lengths and
SHA-256 checksums. Already verified files are skipped. Downloads use temporary
files and replace the destination only after checksum verification. TLS
certificate checking stays enabled. With an incomplete Python certificate setup
on macOS, install the example requirements (which include certifi transitively),
or repair Python's certificate installation; do not disable HTTPS verification.
On macOS, the system CA bundle was verified with:

```bash
SSL_CERT_FILE=/etc/ssl/cert.pem .venv/bin/python download_assets.py
```

After preparing the environment and assets once, the training script reads local
files and does not fetch models or datasets from Hugging Face. Download time is
separate from its reported training and total run times.

## 中文说明

- **模型已在 GitHub**：`model/` 中有真实权重、配置、词表和上游说明，约 18 MB。
- **数据下载到本地仓库目录**：运行 `download_assets.py` 后，`dataset/` 中有 SST-2 数据。
  由于上游许可证为 unknown，GitHub 仅保存来源和下载清单，不公开转载原始数据。
- **版本固定**：每个文件都有固定来源版本、大小和 SHA-256 校验值。
- **可离线训练**：先安装 Python 依赖并下载数据，再运行 `train_bert_tiny.py`。
- **这不是训练完成的模型**：仍需要实际微调、保存并验证新的检查点。
