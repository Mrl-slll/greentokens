"""Four providers train one DistilBERT. Each trains locally for a few minutes, then all four average
their weight changes (local SGD / DiLoCo-style) over authenticated HTTPS. Uses CUDA when present."""
import argparse
from concurrent.futures import ThreadPoolExecutor
import hashlib
import io
import json
import os
from pathlib import Path
import platform
import socket
import time
import urllib.error
import urllib.request
import zipfile

CHUNK = 8 * 1024 * 1024


class Relay:
    def __init__(self, run_id):
        self.url = os.environ["GT_SERVER"].rstrip("/") + "/v1/shared-test/" + run_id
        self.key = os.environ["GT_PROVIDER_KEY"]

    def call(self, method, path, data=None, checksum=None):
        headers = {"Authorization": "Bearer " + self.key, "Content-Type": "application/octet-stream"}
        if checksum:
            headers["X-Content-SHA256"] = checksum
        deadline, wait = time.monotonic() + 120, 1
        while True:
            req = urllib.request.Request(self.url + path, data=data, headers=headers, method=method)
            try:
                with urllib.request.urlopen(req, timeout=120) as response:
                    return response.status, response.read()
            except urllib.error.HTTPError as exc:
                if exc.code < 500 and exc.code != 429:
                    raise RuntimeError(f"Coordinator rejected {method} {path}: HTTP {exc.code}") from None
            except OSError:
                pass
            if time.monotonic() > deadline:
                raise RuntimeError("Coordinator unreachable for 2 minutes")
            time.sleep(wait)
            wait = min(wait * 2, 15)

    def upload(self, name, rank, data):
        parts = [data[i:i + CHUNK] for i in range(0, len(data), CHUNK)]
        hashes = [hashlib.sha256(part).hexdigest() for part in parts]
        def send(i):
            self.call("PUT", f"/blob/{name}/{rank}/{i}", parts[i], hashes[i])
        with ThreadPoolExecutor(max_workers=4) as pool:
            list(pool.map(send, range(len(parts))))
        manifest = {"size": len(data), "sha256": hashlib.sha256(data).hexdigest(), "hashes": hashes}
        self.call("PUT", f"/manifest/{name}/{rank}", json.dumps(manifest).encode())
        return manifest["sha256"]

    def download(self, name, rank):
        deadline = time.monotonic() + 5400
        while time.monotonic() < deadline:
            status, data = self.call("GET", f"/manifest/{name}/{rank}")
            if status == 200:
                break
            time.sleep(2)
        else:
            raise RuntimeError("Timed out waiting for another training PC")
        manifest = json.loads(data)
        def receive(i):
            _, part = self.call("GET", f"/blob/{name}/{rank}/{i}")
            if hashlib.sha256(part).hexdigest() != manifest["hashes"][i]:
                raise RuntimeError("Transfer checksum mismatch")
            return part
        with ThreadPoolExecutor(max_workers=4) as pool:
            result = b"".join(pool.map(receive, range(len(manifest["hashes"]))))
        if len(result) != manifest["size"] or hashlib.sha256(result).hexdigest() != manifest["sha256"]:
            raise RuntimeError("Model transfer checksum mismatch")
        return result

    def barrier(self, step, report):
        deadline = time.monotonic() + 5400
        while time.monotonic() < deadline:
            status, result = self.call("POST", f"/barrier/{step}", json.dumps(report).encode())
            if status == 200:
                return json.loads(result)
            time.sleep(2)
        raise RuntimeError("Four-PC synchronization timed out")


def progress(**kwargs):
    print("GT_PROGRESS " + json.dumps(kwargs), flush=True)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--params", required=True)
    parser.add_argument("--out", required=True)
    args = parser.parse_args()
    p = json.loads(Path(args.params).read_text())
    rank = p["rank"]
    if socket.gethostname().upper() == "CODY":
        raise RuntimeError("The coordinator must never train")
    import numpy as np
    import torch
    import transformers
    import datasets
    from transformers import AutoModelForSequenceClassification, AutoTokenizer, set_seed
    from datasets import load_dataset
    set_seed(p["seed"])
    if p.get("threads"):
        torch.set_num_threads(p["threads"])  # 0/absent: PyTorch default = all physical cores
    torch.set_num_interop_threads(1)
    device = torch.device("cuda", 0) if torch.cuda.is_available() else torch.device("cpu")
    relay = Relay(p["run_id"])
    progress(phase="loading_model", rank=rank, host=socket.gethostname())
    tokenizer = AutoTokenizer.from_pretrained(p["model"])
    model = AutoModelForSequenceClassification.from_pretrained(p["model"], num_labels=2,
                    id2label={0: "NEGATIVE", 1: "POSITIVE"}, label2id={"NEGATIVE": 0, "POSITIVE": 1}).to(device)
    params = list(model.parameters())
    def flatten(tensors):
        return torch.cat([x.detach().reshape(-1).float().cpu() for x in tensors]).numpy().astype("<f4", copy=False)
    def load_flat(vector, tensors):
        offset = 0
        with torch.no_grad():
            for tensor in tensors:
                size = tensor.numel()
                tensor.copy_(torch.from_numpy(vector[offset:offset + size].copy()).view_as(tensor))
                offset += size
        if offset != len(vector):
            raise RuntimeError("Model dimensions differ between providers")
    def weight_hash():
        return hashlib.sha256(flatten(params).tobytes()).hexdigest()
    progress(phase="initial_weights", rank=rank)
    if rank == 0:
        relay.upload("init", 0, flatten(params).tobytes())
    else:
        load_flat(np.frombuffer(relay.download("init", 0), dtype="<f4"), params)
    initial_hash = weight_hash()
    progress(phase="loading_imdb", rank=rank)
    data = load_dataset(p["dataset"])
    full = data["train"].shuffle(seed=p["seed"]).select(range(p["examples"]))
    indices = list(range(rank, p["examples"], 4))
    shard = full.select(indices)
    encoded = tokenizer(list(shard["text"]), truncation=True, padding="max_length",
                        max_length=p["max_length"], return_tensors="pt")
    labels = torch.tensor(list(shard["label"]))
    eval_indices = data["test"].shuffle(seed=42).select(range(256)) if rank == 0 else None
    def evaluate():
        model.eval()
        correct = 0
        with torch.no_grad():
            for i in range(0, 256, 8):
                batch = eval_indices[i:i + 8]
                enc = tokenizer(batch["text"], truncation=True, padding="max_length",
                                max_length=p["max_length"], return_tensors="pt")
                pred = model(**{k: v.to(device) for k, v in enc.items()}).logits.argmax(-1).cpu()
                correct += int((pred == torch.tensor(batch["label"])).sum())
        model.train()
        return {"accuracy": correct / 256, "examples": 256, "split": "test"}
    before = evaluate() if rank == 0 else None
    info = {"host": socket.gethostname(), "rank": rank, "device": torch.cuda.get_device_name(0) if device.type == "cuda" else "cpu",
            "threads": torch.get_num_threads(),
            "torch": torch.__version__, "transformers": transformers.__version__, "datasets": datasets.__version__,
            "python": platform.python_version(), "parameter_count": sum(x.numel() for x in params),
            "dataset_fingerprint": full._fingerprint, "shard_examples": len(indices),
            "shard_index_sha256": hashlib.sha256(json.dumps(indices).encode()).hexdigest(),
            "weights_sha256": initial_hash, "eval_before": before}
    progress(phase="ready", rank=rank)
    relay.barrier(0, info)
    optimizer = torch.optim.AdamW(params, lr=p["learning_rate"])
    model.train()
    generator = torch.Generator().manual_seed(p["seed"] + rank)
    order, position = torch.randperm(len(labels), generator=generator), 0
    # The shared model every replica agrees on. Only weight *changes* travel, as bfloat16 (half of FP32).
    shared = flatten(params).copy()

    def pack(vector):
        return torch.from_numpy(vector).to(torch.bfloat16).view(torch.int16).numpy().tobytes()

    def unpack(raw):
        return torch.from_numpy(np.frombuffer(raw, dtype="<i2").copy()).view(torch.bfloat16).float().numpy()

    step, rounds, losses, compute_seconds, communication_seconds = 0, 0, [], 0.0, 0.0
    elapsed, last_sync = 0.0, 0.0
    started = time.monotonic()
    use_amp = device.type == "cuda"
    while True:
        # Train alone for sync_seconds (shorter at the end so the run finishes near the time limit).
        budget = min(p["sync_seconds"], max(20.0, p["duration_seconds"] - elapsed - last_sync))
        tick = time.monotonic()
        round_steps = 0
        while time.monotonic() - tick < budget:
            if position + p["batch_size"] > len(labels):
                order, position = torch.randperm(len(labels), generator=generator), 0
            idx = order[position:position + p["batch_size"]]
            position += p["batch_size"]
            optimizer.zero_grad(set_to_none=True)
            batch = {k: v[idx].to(device) for k, v in encoded.items()}
            with torch.autocast("cuda", dtype=torch.bfloat16, enabled=use_amp):
                loss = model(**batch, labels=labels[idx].to(device)).loss
            loss.backward()
            optimizer.step()
            losses.append(float(loss.detach()))
            step += 1
            round_steps += 1
            if round_steps % 10 == 0:
                progress(phase="training", round=rounds + 1, step=step, rank=rank, loss=losses[-1])
        compute_seconds += time.monotonic() - tick
        progress(phase="weight_sync", round=rounds + 1, step=step, loss=losses[-1], rank=rank)
        tick = time.monotonic()
        mine = pack(flatten(params) - shared)
        relay.upload(f"grad-{rounds}", rank, mine)
        if rank == 0:
            total = unpack(mine)
            with ThreadPoolExecutor(max_workers=3) as pool:
                peers = list(pool.map(lambda peer: unpack(relay.download(f"grad-{rounds}", peer)), range(1, 4)))
            for delta in peers:
                if len(delta) != len(total) or not np.isfinite(delta).all():
                    raise RuntimeError("Invalid weight change from another PC")
                total += delta
            mean_raw = pack(total / 4)
            relay.upload(f"mean-{rounds}", 0, mean_raw)
        else:
            mean_raw = relay.download(f"mean-{rounds}", 0)
        mean = unpack(mean_raw)
        if len(mean) != len(shared) or not np.isfinite(mean).all():
            raise RuntimeError("Invalid averaged weight change")
        shared += mean
        load_flat(shared, params)
        rounds += 1
        digest = hashlib.sha256(shared.tobytes()).hexdigest()
        report = {"weights_sha256": digest, "loss": losses[-1], "host": socket.gethostname(), "round": rounds,
                  "steps": step, "rounds": rounds, "examples_processed": step * p["batch_size"], "compute_seconds": compute_seconds,
                  "communication_seconds": communication_seconds}
        decision = relay.barrier(rounds, report)
        last_sync = time.monotonic() - tick
        communication_seconds += last_sync
        elapsed = decision["elapsed_seconds"]
        progress(phase="synchronized", round=rounds, step=step, rank=rank, elapsed_seconds=elapsed, loss=losses[-1])
        if decision["stop"]:
            break
    after, checkpoint_sha = None, None
    if rank == 0:
        progress(phase="evaluating_and_saving", rank=rank, step=step)
        after = evaluate()
        checkpoint = Path(args.out) / "checkpoint"
        model.save_pretrained(checkpoint, safe_serialization=True)
        tokenizer.save_pretrained(checkpoint)
        buffer = io.BytesIO()
        with zipfile.ZipFile(buffer, "w", zipfile.ZIP_STORED) as archive:
            for file in checkpoint.iterdir():
                archive.write(file, file.name)
        checkpoint_sha = relay.upload("final", 0, buffer.getvalue())
    metrics = {**info, "weights_sha256": digest, "initial_weights_sha256": initial_hash,
               "steps": step, "rounds": rounds, "examples_processed": step * p["batch_size"], "first_loss": losses[0],
               "last_loss": losses[-1], "training_elapsed_seconds": decision["elapsed_seconds"],
               "local_elapsed_including_save": time.monotonic() - started,
               "compute_seconds": compute_seconds, "communication_seconds": communication_seconds,
               "eval_after": after, "checkpoint_sha256": checkpoint_sha,
               "algorithm": f"local AdamW for up to {p['sync_seconds']} s per round, then average of "
                                "bf16 weight changes (local SGD / DiLoCo-style)"}
    Path(args.out).mkdir(parents=True, exist_ok=True)
    (Path(args.out) / "metrics.json").write_text(json.dumps(metrics), encoding="utf-8")
    progress(phase="complete", rank=rank, step=step)


if __name__ == "__main__":
    main()
