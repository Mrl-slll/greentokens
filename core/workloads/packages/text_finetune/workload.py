"""GreenTokens workload package: text_finetune (approved). Runs on ONE provider computer.

The provider agent downloads this package (checksum-verified), runs:
    python workload.py --params params.json --out OUTPUT_DIR
and uploads OUTPUT_DIR/metrics.json and OUTPUT_DIR/model.safetensors. Progress lines start with
"GT_PROGRESS " (JSON). Uses the GPU when one is available; fails clearly when a GPU was required but missing.
Only the approved models listed by the server can be requested (validated before the job is queued).
"""
import argparse
import json
import os
import platform
import socket
import sys
import time
from pathlib import Path


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--params", required=True)
    parser.add_argument("--out", required=True)
    args = parser.parse_args()
    p = json.loads(Path(args.params).read_text(encoding="utf-8"))
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)

    import torch
    from datasets import load_dataset
    from transformers import AutoModelForSequenceClassification, AutoTokenizer, set_seed

    set_seed(42)
    cuda = torch.cuda.is_available()
    if p.get("require_gpu") and not cuda:
        print("GT_ERROR NO_GPU: this job needs a GPU, but CUDA is not available on this computer", flush=True)
        sys.exit(3)
    device = torch.device("cuda" if cuda else "cpu")
    gpu_name = torch.cuda.get_device_name(0) if cuda else None
    if not cuda:
        torch.set_num_threads(max(1, (os.cpu_count() or 2) // 2))
    print(f"GT_INFO device={device} gpu={gpu_name} model={p['model']}", flush=True)

    tokenizer = AutoTokenizer.from_pretrained(p["model"])
    model = AutoModelForSequenceClassification.from_pretrained(
        p["model"], num_labels=2, id2label={0: "NEGATIVE", 1: "POSITIVE"}, label2id={"NEGATIVE": 0, "POSITIVE": 1}
    ).to(device)
    data = load_dataset("stanfordnlp/sst2")
    n = min(p["examples"], len(data["train"]))
    train = data["train"].shuffle(seed=42).select(range(n))
    held_out = data["validation"].shuffle(seed=42).select(range(min(p["eval_examples"], len(data["validation"]))))

    def encode(ds):
        e = tokenizer(list(ds["sentence"]), truncation=True, padding="max_length", max_length=p["max_length"], return_tensors="pt")
        return e["input_ids"], e["attention_mask"], torch.tensor(list(ds["label"]))

    ids, mask, labels = encode(train)
    eval_ids, eval_mask, eval_labels = encode(held_out)

    def evaluate():
        model.eval()
        correct = 0
        with torch.no_grad():
            for i in range(0, len(eval_labels), 128):
                logits = model(input_ids=eval_ids[i:i + 128].to(device), attention_mask=eval_mask[i:i + 128].to(device)).logits
                correct += int((logits.argmax(-1).cpu() == eval_labels[i:i + 128]).sum())
        model.train()
        return round(correct / len(eval_labels), 4)

    before = evaluate()
    optimizer = torch.optim.AdamW(model.parameters(), lr=p["learning_rate"])
    batch = p["batch_size"]
    total = ((n + batch - 1) // batch) * p["epochs"]
    generator = torch.Generator().manual_seed(42)
    losses, step = [], 0
    started = time.perf_counter()
    for _ in range(p["epochs"]):
        order = torch.randperm(n, generator=generator)
        for i in range(0, n, batch):
            idx = order[i:i + batch]
            loss = model(input_ids=ids[idx].to(device), attention_mask=mask[idx].to(device), labels=labels[idx].to(device)).loss
            optimizer.zero_grad()
            loss.backward()
            optimizer.step()
            step += 1
            losses.append(float(loss.item()))
            if step % 10 == 0 or step == total:
                print("GT_PROGRESS " + json.dumps({"step": step, "total": total, "loss": round(losses[-1], 4)}), flush=True)
    if cuda:
        torch.cuda.synchronize()
    train_seconds = time.perf_counter() - started
    after = evaluate()

    from safetensors.torch import save_file
    # 16-bit weights: half the size (bert-small ~58 MB instead of ~115 MB), which keeps uploads under the
    # ~100 MB request limit of the tunnel; fine for downloading and inference.
    save_file({k: (v.detach().cpu().half() if v.is_floating_point() else v.detach().cpu()).contiguous()
               for k, v in model.state_dict().items()}, str(out / "model.safetensors"))
    tail = losses[-10:]
    computer = {"host": socket.gethostname(), "os": f"{platform.system()} {platform.machine()}", "python": platform.python_version(),
                "ray": None, "rank": 0, "gpu": gpu_name, "device": str(device), "train_seconds": round(train_seconds, 2),
                "sync_seconds": 0.0, "seconds": round(train_seconds, 2), "last_loss": round(sum(tail) / len(tail), 4)}
    metrics = {"workload": "text_finetune", "model": p["model"], "examples": n, "epochs": p["epochs"], "steps": step,
               "device": str(device), "gpu": gpu_name, "eval_before": {"accuracy": before, "examples": len(eval_labels)},
               "eval_after": {"accuracy": after, "examples": len(eval_labels)}, "first_loss": round(losses[0], 4),
               "last_loss": computer["last_loss"], "wall_seconds": round(train_seconds, 2),
               "samples_per_second": round(n * p["epochs"] / train_seconds, 1), "workers": 1, "computers": [computer]}
    (out / "metrics.json").write_text(json.dumps(metrics), encoding="utf-8")
    print("GT_DONE " + json.dumps({"accuracy_before": before, "accuracy_after": after, "seconds": round(train_seconds, 1)}), flush=True)


if __name__ == "__main__":
    main()
