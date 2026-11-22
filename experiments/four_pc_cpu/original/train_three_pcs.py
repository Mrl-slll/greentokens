"""GreenTokens: 30-minute, EXACTLY THREE DISTINCT RTX 5070 Ti machines, Ray Train + DDP.

Run from the Ray HEAD node after all three PCs have joined the cluster.
Each PC must previously run download_model.py to cache the initial model and dataset.
"""
import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import socket
import time

import ray
from ray.train import RunConfig, ScalingConfig
from ray.train.torch import TorchTrainer

MODEL_DIR = Path.home() / "greentokens_models" / "distilbert_imdb_initial"
RESULTS_DIR = Path.home() / "greentokens_results"
REQUIRED_PCS = 3


def train_on_one_pc(config):
    # These libraries run on EACH worker PC, not just the coordinator.
    import torch
    import torch.distributed as dist
    from datasets import load_dataset
    from torch.utils.data import DataLoader, DistributedSampler
    from transformers import AutoModelForSequenceClassification, AutoTokenizer
    from ray import train
    from ray.train.torch import prepare_model

    rank = train.get_context().get_world_rank()
    world_size = train.get_context().get_world_size()
    assert world_size == REQUIRED_PCS, f"Expected 3 training workers, got {world_size}"

    if not torch.cuda.is_available():
        raise RuntimeError(f"Worker {rank} does not have a CUDA GPU")
    device = torch.device("cuda", 0)
    gpu_name = torch.cuda.get_device_name(0)
    if "5070ti" not in gpu_name.lower().replace(" ", ""):
        raise RuntimeError(f"Worker {rank} has {gpu_name}, not an RTX 5070 Ti")
    if torch.cuda.get_device_capability(0)[0] < 12:
        raise RuntimeError("RTX 5070 Ti needs a CUDA 12.8 compatible PyTorch build")

    # Keep a durable per-worker record on each machine of which hardware participated.
    identity = {
        "rank": rank,
        "hostname": socket.gethostname(),
        "ip": ray.util.get_node_ip_address(),
        "ray_node_id": ray.get_runtime_context().get_node_id(),
        "gpu": gpu_name,
    }
    print("GREENTOKENS_WORKER " + json.dumps(identity), flush=True)

    local_model_dir = Path.home() / "greentokens_models" / "distilbert_imdb_initial"
    if not (local_model_dir / "config.json").exists():
        raise RuntimeError(f"Run download_model.py on {socket.gethostname()} first: {local_model_dir} missing")

    torch.manual_seed(42)
    tokenizer = AutoTokenizer.from_pretrained(str(local_model_dir), local_files_only=True)
    model = AutoModelForSequenceClassification.from_pretrained(
        str(local_model_dir), local_files_only=True
    )
    model = prepare_model(model)  # 1 GPU per node; DDP synchronizes updates among all three.
    optimizer = torch.optim.AdamW(model.parameters(), lr=2e-5)

    # Use genuine labeled movie reviews; every worker owns a different subset via DistributedSampler.
    ds = load_dataset("stanfordnlp/imdb", split="train")
    ds = ds.shuffle(seed=42).select(range(min(12000, len(ds))))

    def tokenize_batch(batch):
        return tokenizer(
            batch["text"],
            truncation=True,
            padding="max_length",
            max_length=256,
        )

    ds = ds.map(tokenize_batch, batched=True, remove_columns=["text"], desc=f"Tokenize rank {rank}")
    ds.set_format(type="torch", columns=["input_ids", "attention_mask", "label"])
    sampler = DistributedSampler(
        ds, num_replicas=world_size, rank=rank, shuffle=True, seed=42, drop_last=True
    )
    loader = DataLoader(ds, batch_size=config["batch_size"], sampler=sampler,
                        num_workers=2, pin_memory=True, drop_last=True)

    # Barrier starts the 30-minute CLOCK only once all three GPUs + data are ready.
    dist.barrier()
    start = time.monotonic()
    print(f"Rank {rank}: 30-minute synchronized training begins now", flush=True)
    steps = 0
    epoch = 0
    recent_losses = []
    stop = False
    model.train()

    while not stop:
        sampler.set_epoch(epoch)
        for batch in loader:
            # Check on ALL GPUs at the same point; synchronizing this condition prevents
            # one worker from stopping early and hanging the other two inside DDP.
            local_time_up = int(time.monotonic() - start >= config["duration_seconds"])
            global_time_up = torch.tensor([local_time_up], device=device, dtype=torch.int32)
            dist.all_reduce(global_time_up, op=dist.ReduceOp.MAX)
            if global_time_up.item() > 0:
                stop = True
                break

            batch = {key: val.to(device, non_blocking=True) for key, val in batch.items()}
            labels = batch.pop("label")
            optimizer.zero_grad(set_to_none=True)
            with torch.autocast(device_type="cuda", dtype=torch.bfloat16):
                output = model(**batch, labels=labels)
                loss = output.loss
            loss.backward()  # DDP gradient synchronization happens across the 3 PCs.
            optimizer.step()
            steps += 1
            recent_losses.append(float(loss.detach().item()))
            if len(recent_losses) > 50:
                recent_losses.pop(0)
            if rank == 0 and steps % 50 == 0:
                print(f"Steps/worker={steps} | elapsed={time.monotonic()-start:.0f}s | "
                      f"recent_loss={sum(recent_losses)/len(recent_losses):.4f}", flush=True)
        epoch += 1

    torch.cuda.synchronize()
    elapsed = time.monotonic() - start
    avg_loss = sum(recent_losses) / max(len(recent_losses), 1)
    # Three GPUs trained one DDP model. Collect global loss for a final descriptive metric.
    loss_tensor = torch.tensor([avg_loss], device=device)
    dist.all_reduce(loss_tensor, op=dist.ReduceOp.SUM)
    global_avg_loss = loss_tensor.item() / world_size

    # The complete fine-tuned model is saved by RANK ZERO on its local PC AFTER the timer.
    # Save and startup time are not part of the timed training interval.
    output_location = None
    if rank == 0:
        output_path = Path.home() / "greentokens_results" / "distilbert_finetuned_3pcs"
        output_path.mkdir(parents=True, exist_ok=True)
        base = model.module if hasattr(model, "module") else model
        base.save_pretrained(str(output_path), safe_serialization=True)
        tokenizer.save_pretrained(str(output_path))
        output_location = str(output_path)
        (output_path / "benchmark.json").write_text(json.dumps({
            "elapsed_training_seconds": elapsed,
            "duration_requested_seconds": config["duration_seconds"],
            "computers": REQUIRED_PCS,
            "steps_per_gpu": steps,
            "global_batch_size": config["batch_size"] * world_size,
            "training_examples_processed_approx": steps * config["batch_size"] * world_size,
            "avg_recent_loss": global_avg_loss,
            "rank_zero_machine": identity,
        }, indent=2) + "\n", encoding="utf-8")
        print(f"TRAINED MODEL SAVED on {socket.gethostname()}: {output_path}", flush=True)

    print(f"DONE rank={rank} host={identity['hostname']} steps={steps} elapsed={elapsed:.2f}s", flush=True)
    # All workers MUST call report the same number of times.
    train.report({
        "steps_per_worker": steps,
        "elapsed_training_seconds": round(elapsed, 2),
        "recent_mean_loss_across_workers": round(global_avg_loss, 5),
        "approx_training_examples": steps * config["batch_size"] * world_size,
        "rank_zero_saved_model": output_location if rank == 0 else "(saved on rank-zero PC)",
    })


def main():
    parser = argparse.ArgumentParser(description="Require exactly 3 distinct RTX 5070 Ti computers for a timed DDP experiment.")
    parser.add_argument("--minutes", type=float, default=30.0,
                        help="Training portion only. Default: 30 minutes. Try --minutes 0.5 for a smoke test.")
    parser.add_argument("--batch-size", type=int, default=16, help="Examples per GPU per step")
    parser.add_argument("--check-only", action="store_true", help="Check three-node cluster, then exit without training")
    args = parser.parse_args()
    if not (0 < args.minutes <= 240):
        parser.error("--minutes must be between 0 and 240")
    if not (1 <= args.batch_size <= 64):
        parser.error("--batch-size must be between 1 and 64")

    ray.init(address="auto")
    alive_nodes = [node for node in ray.nodes() if node.get("Alive")]
    gpu_nodes = [node for node in alive_nodes if node.get("Resources", {}).get("GPU", 0) >= 1]
    print(f"Ray cluster: {len(alive_nodes)} active PCs, {len(gpu_nodes)} with registered GPU(s)")
    for node in alive_nodes:
        print(f"  PC: {node.get('NodeManagerAddress')} | GPUs: {node.get('Resources', {}).get('GPU', 0)}")

    # STRONG, EXPLICIT CARDINALITY RULE: reject 1, 2, 4, ... machines.
    if len(alive_nodes) != REQUIRED_PCS or len(gpu_nodes) != REQUIRED_PCS:
        raise SystemExit(
            "TEST REFUSED: The Ray cluster must contain EXACTLY 3 active computers "
            "and EACH computer must register >=1 GPU. Stop disconnected/extra Ray nodes first."
        )
    if args.check_only:
        print("PASS: Exactly 3 separate registered GPU computers. The actual GPU model is checked at runtime.")
        return

    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    wall_start = time.monotonic()
    trainer = TorchTrainer(
        train_on_one_pc,
        train_loop_config={
            "duration_seconds": int(round(args.minutes * 60)),
            "batch_size": args.batch_size,
        },
        scaling_config=ScalingConfig(
            num_workers=REQUIRED_PCS,
            use_gpu=True,
            resources_per_worker={"CPU": 2, "GPU": 1},
            placement_strategy="STRICT_SPREAD",  # 1 GPU worker on EACH of 3 DISTINCT Ray nodes.
        ),
        run_config=RunConfig(name="greentokens_3pcs_" + datetime.now().strftime("%Y%m%d_%H%M%S")),
    )
    result = trainer.fit()
    wall_elapsed = round(time.monotonic() - wall_start, 2)
    summary = {
        "run_completed_at_utc": datetime.now(timezone.utc).isoformat(),
        "required_active_pcs": REQUIRED_PCS,
        "distinct_machine_placement": "STRICT_SPREAD",
        "target_training_seconds": int(round(args.minutes * 60)),
        "elapsed_wall_seconds_setup_train_save": wall_elapsed,
        "ray_train_metrics": result.metrics,
        "gpu_nodes": [n.get("NodeManagerAddress") for n in gpu_nodes],
    }
    filename = RESULTS_DIR / ("greentokens_summary_" + datetime.now().strftime("%Y%m%d_%H%M%S") + ".json")
    filename.write_text(json.dumps(summary, indent=2, default=str) + "\n", encoding="utf-8")
    print("\nGREEN TOKENS TEST COMPLETE")
    print(json.dumps(summary, indent=2, default=str))
    print(f"Summary saved on HEAD PC: {filename}")
    print("Fine-tuned model saved on the rank-zero GPU PC, path shown in worker logs.")


if __name__ == "__main__":
    main()
