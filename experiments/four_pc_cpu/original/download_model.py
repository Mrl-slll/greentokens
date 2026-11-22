"""Run once on EACH PC to download the real training model and IMDB training data."""
from pathlib import Path
import sys

import torch
from datasets import load_dataset
from transformers import AutoModelForSequenceClassification, AutoTokenizer

MODEL_ID = "distilbert/distilbert-base-uncased"
MODEL_DIR = Path.home() / "greentokens_models" / "distilbert_imdb_initial"


def main():
    if not torch.cuda.is_available():
        sys.exit("ERROR: PyTorch cannot access an NVIDIA GPU. Check your driver and CUDA 12.8 PyTorch installation.")
    name = torch.cuda.get_device_name(0)
    print(f"Detected GPU: {name}")
    print(f"CUDA via PyTorch: {torch.version.cuda}")
    print(f"GPU memory: {torch.cuda.get_device_properties(0).total_memory / (1024 ** 3):.1f} GiB")
    if "5070ti" not in name.lower().replace(" ", ""):
        sys.exit("ERROR: This test requires an RTX 5070 Ti on each of the three PCs.")
    if torch.cuda.get_device_capability(0)[0] < 12:
        sys.exit("ERROR: Your PyTorch CUDA build does not support the RTX 5070 Ti (Blackwell / sm_120). Install the cu128 wheel.")

    print(f"Downloading pretrained DistilBERT from: https://huggingface.co/{MODEL_ID}")
    torch.manual_seed(42)
    tokenizer = AutoTokenizer.from_pretrained(MODEL_ID)
    model = AutoModelForSequenceClassification.from_pretrained(MODEL_ID, num_labels=2)
    MODEL_DIR.mkdir(parents=True, exist_ok=True)
    tokenizer.save_pretrained(MODEL_DIR)
    model.save_pretrained(MODEL_DIR, safe_serialization=True)
    print(f"Model files stored at: {MODEL_DIR}")

    print("Downloading the publicly available IMDB sentiment-classification training dataset...")
    imdb = load_dataset("stanfordnlp/imdb", split="train")
    print(f"Dataset cached. Training examples: {len(imdb):,}")
    print("SUCCESS: This PC has the required GPU, pretrained model, and training data.")


if __name__ == "__main__":
    main()
