# GreenTokens — exactly three RTX 5070 Ti PCs, 30-minute AI training test

## What this tests

- Fine-tune one real pretrained **DistilBERT** model on labeled IMDB movie reviews.
- Use **three physically separate PCs** with **one NVIDIA RTX 5070 Ti GPU on each**.
- Run one PyTorch **distributed data parallel (DDP)** training job managed by **Ray Train**.
- Train for **approximately 1,800 seconds (30 minutes)**, once all three PCs have loaded their data and are ready.
- Reject clusters with fewer or more than **3 active Ray computers**; `STRICT_SPREAD` forces each of the three training workers onto a different machine.
- Save a fine-tuned model on the rank-zero worker PC and save a JSON summary on the head PC.

**Important:** An AI model does not inherently *need exactly three PCs*. This test **enforces** exactly three participants through the scheduler and cluster checks. Training runtime will be within one training step of 1,800 seconds, rather than guaranteed to the millisecond. Installation, data download, tokenization, Ray startup, and saving the final model are outside the 30-minute training timer.

## Operating system and networking

Use **Linux** on all three PCs (Ubuntu 22.04/24.04 recommended, Python 3.11/3.12). For Windows gaming PCs, Linux/WSL2 may work but multi-node GPU networking can require additional configuration. This script expects Linux-style Ray and NCCL GPU communication: Windows-native NCCL is not supported.

All three PCs should initially be on the **same trusted LAN**, have current NVIDIA drivers compatible with CUDA 12.8, be reachable via their private IP addresses, and have a stable connection. Do **not** expose the Ray cluster or its ports to the public internet.

### Step A: On ALL THREE PCs

Copy this folder to each PC, open a terminal in it, and run:

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -U pip
python -m pip install torch --index-url https://download.pytorch.org/whl/cu128
python -m pip install -r requirements.txt
python download_model.py
```

The last command **actually downloads the pretrained model and real training dataset** to that PC. Each PC independently keeps its local copy, so model/data download is not part of the benchmark.

If `torch.cuda.is_available()` is false, first fix the NVIDIA driver and CUDA PyTorch installation. You can verify with:

```bash
nvidia-smi
python -c "import torch; print(torch.__version__, torch.cuda.is_available(), torch.cuda.get_device_name(0))"
```

### Step B: Start the three-node Ray cluster

Choose one of the three PCs as the **HEAD**. On that PC, with its virtual environment active:

```bash
ray start --head --port=6379 --num-gpus=1
```

The Ray command prints an address, such as `192.168.1.10:6379`. On each of the **two other** PCs, with its environment active, run (replace the example IP with the REAL head IP):

```bash
ray start --address=192.168.1.10:6379 --num-gpus=1
```

The same Ray and PyTorch versions should be installed on all three PCs. If hosts cannot connect, check local firewall rules, IP reachability, and LAN routing. Ray and NCCL require inter-PC networking beyond a single port. For remote internet-connected machines, first establish secure private networking; do not directly expose Ray services.

### Step C: Verify **exactly three** PCs

On the HEAD PC only:

```bash
python train_three_pcs.py --check-only
```

This must show **3 active PCs and 3 GPU-equipped PCs**. It will reject a cluster containing 1, 2, 4, or more Ray nodes. The full run separately verifies each assigned GPU is a **5070 Ti**.

### Step D: Recommended short connectivity smoke test

This quick test still uses EXACTLY three PCs, but only trains for 30 seconds, to catch environment/network issues before the full run:

```bash
python train_three_pcs.py --minutes 0.5
```

This **is not the official 30-minute test**; it just reduces the risk of wasting the full test on a setup error. If a 30-second run is too short to initialize successfully, you can use 2 minutes.

### Step E: THE 30-minute test

On the HEAD PC only:

```bash
python train_three_pcs.py --minutes 30
```

The training timer starts **after all three workers are initialized and synchronized**. Each GPU independently processes a different shard of review data; DDP synchronizes gradients across the machines. When 30 minutes has elapsed, the workers finish the current step, stop together, and report metrics.

### Outputs

- HEAD PC: `~/greentokens_results/greentokens_summary_YYYYMMDD_HHMMSS.json` (numbers of workers, training time, steps, recent loss, setup/run wall time, three node IPs).
- Rank-zero GPU PC: `~/greentokens_results/distilbert_finetuned_3pcs/` (trained Hugging Face model and tokenizer; checkpoint saved *after* the 30-minute window). Look for `TRAINED MODEL SAVED` in worker output to identify the machine.
- Console: lines starting `GREENTOKENS_WORKER` show rank, host, IP, Ray node ID, GPU model. Three distinct node IDs are expected.

## What a passing test really proves

**Pass:** Exactly 3 separate RTX 5070 Ti GPU hosts run and synchronize one training job for about 30 minutes, producing a trained model and logs.

**Does not prove:** That the neural network intrinsically requires 3 hosts, that 3 hosts are faster than 1, or that the approach is cheaper than cloud GPUs. Those require a later **apples-to-apples one-GPU vs three-GPU comparison** using fixed examples/epochs, with network and electricity costs included.

## Sources

- Model: https://huggingface.co/distilbert/distilbert-base-uncased (Apache-2.0)
- IMDB training data: https://huggingface.co/datasets/stanfordnlp/imdb
- Ray Train scaling: https://docs.ray.io/en/latest/train/api/doc/ray.air.config.ScalingConfig.html
- Ray strict placement: https://docs.ray.io/en/latest/ray-core/scheduling/placement-group.html
- RTX 5070 Ti specs: https://www.nvidia.com/en-us/geforce/graphics-cards/50-series/rtx-5070-family/
- PyTorch CUDA install: https://pytorch.org/get-started/locally/

### Troubleshooting

- **Wrong GPU/unsupported CUDA:** Install a Blackwell-compatible CUDA 12.8 PyTorch wheel and update GPU drivers.
- **Ray sees only 1 or 2 nodes:** Check that the two worker PC `ray start --address=...` commands completed; use `ray status` on the head.
- **Fourth computer joined:** Stop Ray on the extra PC (`ray stop`) so the cluster has only 3 active nodes.
- **Connection timeout/NCCL:** Verify private IP connectivity, interface selection, and firewall; first test all three on the same LAN.
- **Training fails before timer:** Pre-download everything with `python download_model.py` on each PC and ensure consistent environments.
- **Out of memory:** Reduce `--batch-size` from 16 to 8 on the full test, keeping 3 PCs and 30 minutes.
- **Loss is not improving:** This is a pipeline validation, not a tuned accuracy benchmark; test the saved model separately with held-out reviews.
