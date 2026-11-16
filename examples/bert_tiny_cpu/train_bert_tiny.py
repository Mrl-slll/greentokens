"""Single-computer CPU baseline for GreenTokens; not a multi-node test.

Run with Python 3.11+ in a fresh virtual environment. See README_zh.md.
"""
import argparse
import hashlib
import importlib.metadata
import json
import platform
import socket
import time
from pathlib import Path


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--examples", type=int, default=999)
    parser.add_argument("--epochs", type=int, default=3)
    parser.add_argument("--batch-size", type=int, default=24)
    parser.add_argument("--threads", type=int, default=2)
    parser.add_argument("--max-length", type=int, default=128)
    parser.add_argument("--learning-rate", type=float, default=5e-5)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--output", default="bert-tiny-sst2-cpu")
    parser.add_argument("--sentence", default="This movie was wonderful.")
    args = parser.parse_args()
    for key in ("examples", "epochs", "batch_size", "threads", "max_length", "learning_rate"):
        if getattr(args, key) <= 0:
            parser.error(f"--{key.replace('_', '-')} must be positive")
    if args.max_length > 512:
        parser.error("--max-length must be at most 512")
    output = Path(args.output).resolve()
    if output.exists():
        parser.error(f"Output already exists: {output}. Choose a new --output.")

    import torch
    from datasets import load_dataset
    from torch.utils.data import DataLoader
    from transformers import AutoModelForSequenceClassification, AutoTokenizer, set_seed

    total_start = time.perf_counter()
    torch.set_num_threads(args.threads)
    set_seed(args.seed)
    device = torch.device("cpu")  # Also avoids Apple's MPS accelerator.
    model_id = "prajjwal1/bert-tiny"
    print(f"Host={socket.gethostname()} device=cpu threads={args.threads}", flush=True)
    print("Loading model and SST-2; first run needs internet access...", flush=True)
    tokenizer = AutoTokenizer.from_pretrained(model_id)
    model = AutoModelForSequenceClassification.from_pretrained(
        model_id, num_labels=2,
        id2label={0: "NEGATIVE", 1: "POSITIVE"},
        label2id={"NEGATIVE": 0, "POSITIVE": 1},
    ).to(device)
    data = load_dataset("stanfordnlp/sst2")
    if args.examples > len(data["train"]):
        parser.error("--examples exceeds the training dataset size")
    raw_train = data["train"].shuffle(seed=args.seed).select(range(args.examples))
    subset_hash = hashlib.sha256(
        json.dumps(raw_train.to_dict(), sort_keys=True).encode("utf-8")
    ).hexdigest()

    def encode(dataset):
        encoded = dataset.map(
            lambda batch: tokenizer(batch["sentence"], truncation=True,
                                    padding="max_length", max_length=args.max_length),
            batched=True, remove_columns=["sentence", "idx"],
        ).rename_column("label", "labels")
        encoded.set_format("torch")
        return encoded

    train_data = encode(raw_train)
    validation_data = encode(data["validation"])
    train_loader = DataLoader(train_data, batch_size=args.batch_size, shuffle=True,
                              num_workers=0, generator=torch.Generator().manual_seed(args.seed))
    validation_loader = DataLoader(validation_data, batch_size=args.batch_size, num_workers=0)
    optimizer = torch.optim.AdamW(model.parameters(), lr=args.learning_rate, weight_decay=0.01)
    epoch_losses = []
    train_start = time.perf_counter()
    cpu_start = time.process_time()
    for epoch in range(args.epochs):
        model.train()
        loss_sum = 0.0
        count = 0
        for step, batch in enumerate(train_loader, start=1):
            batch = {key: value.to(device) for key, value in batch.items()}
            optimizer.zero_grad(set_to_none=True)
            loss = model(**batch).loss
            loss.backward()
            torch.nn.utils.clip_grad_norm_(model.parameters(), 1.0)
            optimizer.step()
            n = batch["labels"].shape[0]
            loss_sum += loss.item() * n
            count += n
            if step % 10 == 0 or step == len(train_loader):
                print(f"epoch={epoch + 1}/{args.epochs} step={step}/{len(train_loader)} "
                      f"loss={loss.item():.4f}", flush=True)
        epoch_losses.append(loss_sum / count)
    train_seconds = time.perf_counter() - train_start
    cpu_seconds = time.process_time() - cpu_start

    model.eval()
    correct = 0
    with torch.inference_mode():
        for batch in validation_loader:
            batch = {key: value.to(device) for key, value in batch.items()}
            prediction = model(**batch).logits.argmax(dim=-1)
            correct += (prediction == batch["labels"]).sum().item()
    accuracy = correct / len(validation_data)

    output.mkdir(parents=True, exist_ok=False)
    model.save_pretrained(output, safe_serialization=True)
    tokenizer.save_pretrained(output)
    # Verify the saved model, rather than using the in-memory model for the demo.
    restored = AutoModelForSequenceClassification.from_pretrained(output).to(device).eval()
    restored_tokenizer = AutoTokenizer.from_pretrained(output)
    inputs = restored_tokenizer(args.sentence, return_tensors="pt", truncation=True,
                                max_length=args.max_length)
    with torch.inference_mode():
        probabilities = restored(**inputs).logits.softmax(dim=-1)[0]
    label = int(probabilities.argmax())
    report = {
        "status": "completed", "mode": "single_computer_cpu", "hostname": socket.gethostname(),
        "platform": platform.platform(), "python": platform.python_version(),
        "versions": {name: importlib.metadata.version(name)
                     for name in ("torch", "transformers", "datasets")},
        "model": model_id, "model_revision": getattr(model.config, "_commit_hash", None),
        "dataset": "stanfordnlp/sst2", "training_subset_sha256": subset_hash,
        "settings": vars(args), "learning_rate": args.learning_rate, "weight_decay": 0.01,
        "epoch_train_losses": epoch_losses, "validation_accuracy": accuracy,
        "training_loop_seconds": train_seconds, "training_process_cpu_seconds": cpu_seconds,
        "average_training_cpu_percent_one_core_is_100": 100 * cpu_seconds / train_seconds,
        "checkpoint": str(output), "checkpoint_reload_verified": True,
        "prediction": {"sentence": args.sentence, "label": restored.config.id2label[label],
                       "probability": float(probabilities[label])},
        "total_seconds_including_download_preparation_evaluation_save_reload":
            time.perf_counter() - total_start,
    }
    (output / "metrics.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps(report, indent=2), flush=True)
    print(f"COMPLETE: checkpoint and metrics saved to {output}", flush=True)


if __name__ == "__main__":
    main()
