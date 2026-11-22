"""Recipe: fine-tune prajjwal1/bert-tiny for SST-2 sentiment. Approved pipeline; no customer code runs.

Heavy libraries are imported inside methods only, so the backend (which has no torch) can import this
module, and Ray ships it to providers by value.
"""
MODEL_ID = "prajjwal1/bert-tiny"
DATASET_ID = "stanfordnlp/sst2"


class BertTinyRecipe:
    def __init__(self, params):
        self.p = params  # validated BertTinyParams as a dict

    def build(self):
        from transformers import AutoModelForSequenceClassification, set_seed
        set_seed(42)
        model = AutoModelForSequenceClassification.from_pretrained(
            MODEL_ID, num_labels=2, id2label={0: "NEGATIVE", 1: "POSITIVE"}, label2id={"NEGATIVE": 0, "POSITIVE": 1})
        return model

    def batches(self, rank, world):
        """Returns a function step -> (inputs, labels) over this computer's disjoint slice of the data."""
        import torch
        from datasets import load_dataset
        from transformers import AutoTokenizer
        p = self.p
        raw = load_dataset(DATASET_ID)["train"].shuffle(seed=42).select(range(p["examples"]))
        sentences, labels = list(raw["sentence"]), list(raw["label"])  # datasets 4.x returns column objects
        enc = AutoTokenizer.from_pretrained(MODEL_ID)(sentences, truncation=True, padding="max_length",
                                                      max_length=p["max_length"], return_tensors="pt")
        labels = torch.tensor(labels)
        shard = list(range(rank, p["examples"], world))
        per_worker = max(1, p["global_batch"] // world)

        def batch(step):
            idx = [shard[(step * per_worker + i) % len(shard)] for i in range(per_worker)]
            return {"input_ids": enc["input_ids"][idx], "attention_mask": enc["attention_mask"][idx], "labels": labels[idx]}
        batch.per_worker = per_worker
        return batch

    def loss(self, model, batch):
        return model(**batch).loss

    def evaluate(self, model):
        """Accuracy on held-out validation sentences (never used for training)."""
        import torch
        from datasets import load_dataset
        from transformers import AutoTokenizer
        p = self.p
        raw = load_dataset(DATASET_ID)["validation"].shuffle(seed=42).select(range(p["eval_examples"]))
        enc = AutoTokenizer.from_pretrained(MODEL_ID)(list(raw["sentence"]), truncation=True, padding="max_length",
                                                      max_length=p["max_length"], return_tensors="pt")
        labels = torch.tensor(list(raw["label"]))
        model.eval()
        correct = 0
        with torch.no_grad():
            for i in range(0, len(labels), 64):
                logits = model(input_ids=enc["input_ids"][i:i + 64], attention_mask=enc["attention_mask"][i:i + 64]).logits
                correct += int((logits.argmax(-1) == labels[i:i + 64]).sum())
        model.train()
        return {"accuracy": round(correct / len(labels), 4), "examples": len(labels)}

    def save(self, model):
        from safetensors.torch import save
        return save({k: v.contiguous() for k, v in model.state_dict().items()})
