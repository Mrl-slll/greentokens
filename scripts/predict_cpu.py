"""Local inference from the newest verified CPU checkpoint.

One-shot (default): read one JSON request {"text": ...} on stdin, print one JSON result.
--serve: keep the model loaded; read one JSON request per line, write one JSON line each.
The newest examples/bert_tiny_cpu/bert-tiny-run-* directory whose metrics.json records a
verified reload is used, and the server reloads automatically when a newer run appears.
"""
import json
from pathlib import Path
import sys

RUNS = Path(__file__).resolve().parents[1] / "examples/bert_tiny_cpu"


def latest_checkpoint():
    # Timestamped names (bert-tiny-run-YYYYMMDD-HHMMSS) sort chronologically.
    for run in sorted(RUNS.glob("bert-tiny-run-*"), reverse=True):
        try:
            metrics = json.loads((run / "metrics.json").read_text(encoding="utf-8"))
        except (OSError, ValueError):
            continue  # Missing metrics means the run is unfinished or failed.
        if metrics.get("checkpoint_reload_verified") is True and (run / "model.safetensors").is_file():
            return run
    raise FileNotFoundError("No verified checkpoint")


class Predictor:
    def __init__(self):
        import torch
        torch.set_num_threads(2)
        self.torch = torch
        self.checkpoint = None

    def _ensure_loaded(self):
        checkpoint = latest_checkpoint()
        if checkpoint != self.checkpoint:
            from transformers import AutoModelForSequenceClassification, AutoTokenizer
            self.tokenizer = AutoTokenizer.from_pretrained(checkpoint, local_files_only=True)
            self.model = AutoModelForSequenceClassification.from_pretrained(
                checkpoint, local_files_only=True).to("cpu").eval()
            self.checkpoint = checkpoint

    def predict(self, request):
        text = request.get("text") if isinstance(request, dict) else None
        if not isinstance(text, str) or not text.strip() or len(text) > 1000:
            raise ValueError("Invalid sentence")
        self._ensure_loaded()
        inputs = self.tokenizer(text, return_tensors="pt", truncation=True, max_length=128)
        with self.torch.inference_mode():
            probabilities = self.model(**inputs).logits.softmax(dim=-1)[0]
        label = int(probabilities.argmax())
        return {"label": self.model.config.id2label[label], "probability": float(probabilities[label]),
                "device": "cpu", "source": "saved-trained-checkpoint", "checkpoint": self.checkpoint.name}


def serve():
    predictor = Predictor()
    for line in sys.stdin:
        if not line.strip():
            continue
        try:
            reply = predictor.predict(json.loads(line))
        except Exception:
            reply = {"error": "Local prediction failed"}
        print(json.dumps(reply), flush=True)


def main():
    print(json.dumps(Predictor().predict(json.load(sys.stdin))))


if __name__ == "__main__":
    if "--serve" in sys.argv[1:]:
        serve()
    else:
        try:
            main()
        except Exception:
            print("Local prediction failed", file=sys.stderr)
            sys.exit(1)
