"""Operator CLI for the separate four-remote-PC test. No credentials needed on loopback."""
import argparse
import hashlib
import json
from pathlib import Path
import time
import urllib.request
import zipfile

ROOT = Path(__file__).resolve().parent


def api(path, method="GET"):
    req = urllib.request.Request("http://127.0.0.1:8000" + path, method=method,
                                 headers={"X-Dev-User": "admin"})
    with urllib.request.urlopen(req, timeout=30) as response:
        return json.loads(response.read())


def collect(run_id):
    status = api("/v1/shared-test/" + run_id)
    if not all(j["status"] == "SUCCEEDED" for j in status["jobs"]):
        raise RuntimeError("All four provider jobs must succeed before collecting")
    results = [api("/v1/jobs/" + j["job_id"] + "/result")["result"] for j in status["jobs"]]
    if len({r["weights_sha256"] for r in results}) != 1 or len({r["host"] for r in results}) != 4:
        raise RuntimeError("Training replicas differ or four unique computers were not observed")
    if any(r["weights_sha256"] == r["initial_weights_sha256"] or r["steps"] < 1 for r in results):
        raise RuntimeError("No model update was proved")
    if len({r.get("rounds", r["steps"]) for r in results}) != 1:
        raise RuntimeError("Synchronization round counts differ")
    cfg = status["config"]
    if [r["host"] for r in results] != cfg["hosts"]:
        raise RuntimeError("Unexpected provider assignment")
    path = ROOT / "runs" / run_id
    manifest = json.loads((path / "final-0.json").read_text())
    archive = path / "trained-model.zip"
    digest = hashlib.sha256()
    with archive.open("wb") as output:
        for i, expected in enumerate(manifest["hashes"]):
            data = (path / f"final-0-{i}.bin").read_bytes()
            if hashlib.sha256(data).hexdigest() != expected:
                raise RuntimeError("Checkpoint chunk mismatch")
            output.write(data)
            digest.update(data)
    if digest.hexdigest() != manifest["sha256"] or digest.hexdigest() != results[0]["checkpoint_sha256"]:
        raise RuntimeError("Checkpoint checksum mismatch")
    model = path / "model"
    model.mkdir(exist_ok=True)
    with zipfile.ZipFile(archive) as z:
        for entry in z.infolist():
            target = (model / entry.filename).resolve()
            if target.parent != model.resolve() or entry.is_dir():
                raise RuntimeError("Unexpected checkpoint path")
            target.write_bytes(z.read(entry))
    summary = {"config": cfg, "results": results, "checkpoint_sha256": digest.hexdigest(),
               "shared_final_weights_sha256": results[0]["weights_sha256"]}
    (path / "results.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    lead = results[0]
    rows = "\n".join(f"| {r['host']} | {r['rank']} | {r['steps']} | {r['examples_processed']} | "
                     f"{r['compute_seconds']:.1f} | {r['communication_seconds']:.1f} | {r['last_loss']:.5f} |"
                     for r in results)
    report = f"""# Completed four-PC DistilBERT/IMDB test

Run: `{run_id}`. All four pinned remote provider jobs succeeded.

The complete design and explanation are in [the experiment README](../../README.md).
CODY hosted the API, relayed bytes, tracked jobs and saved results. It did not train or average gradients.
INFO-COL-D0047 was rank zero: it trained its own shard, averaged the four weight changes each round,
evaluated the shared model, and saved the checkpoint. D0048, D0049 and D0064 trained their own shards.

## Measured participation

| Computer | Rank | Local training steps | Reviews processed | Compute seconds | Communication/wait seconds | Final batch loss |
|---|---:|---:|---:|---:|---:|---:|
{rows}

Each provider had 3,000 distinct reviews from the same shuffled 12,000-review IMDB training subset.
Each PC trained on batches of 16 of its own reviews for up to {cfg.get('sync_seconds', 0)} seconds per round;
the four then averaged their weight changes ({lead.get('rounds', lead['steps'])} synchronization rounds).
Step counts differ slightly because PCs run at slightly different speeds. Counts above include repeated
examples when cycling through shards. Total review presentations: **{sum(r['examples_processed'] for r in results)}**.
Synchronized training elapsed: **{lead['training_elapsed_seconds']:.1f} seconds**.
Requested interval: **1,800 seconds**, excluding setup and final evaluation/save.
Compute and communication totals exclude some hashing and logging overhead.

## Model result

- Held-out test reviews: {lead['eval_after']['examples']}.
- Accuracy before training: {lead['eval_before']['accuracy']:.2%}.
- Accuracy after training: {lead['eval_after']['accuracy']:.2%}.
- Parameters trained: {lead['parameter_count']:,}; full FP32 DistilBERT fine-tuning with AdamW.
- Final weights were identical across all four providers and differed from initialization.
- Shared final weight SHA-256: `{lead['weights_sha256']}`.
- Downloadable/local model archive: `trained-model.zip`; unpacked model/tokenizer: `model/`.
- Archive SHA-256: `{digest.hexdigest()}`.

Method: {lead.get('algorithm', 'see results.json')}, over authenticated HTTPS, not Ray DDP.
The current provider connections do not form a Ray cluster. Weight changes were transferred as chunks,
averaged on remote rank zero, then applied by all four replicas to a shared FP32 copy before a
hash-checked barrier.
This demonstrates four trusted provider computers contributing to one model; it does not establish
speedup, lower cost, or production model quality. Full runtime versions and shard hashes are in
`results.json`; per-step records are in `state.json`.
"""
    (path / "README.md").write_text(report, encoding="utf-8")
    overview = ROOT / "README.md"
    text = overview.read_text(encoding="utf-8")
    start = text.index("Status:")
    end = text.index("\n## What", start)
    text = text[:start] + f"Status: completed. See [the measured run report](runs/{run_id}/README.md).\n" + text[end:]
    overview.write_text(text, encoding="utf-8")
    print(str(path / "README.md"))


def monitor(run_id):
    previous = None
    deadline = time.monotonic() + 11000
    while time.monotonic() < deadline:
        try:
            status = api("/v1/shared-test/" + run_id)
        except OSError:
            time.sleep(30)
            continue
        jobs = status["jobs"]
        state = status["state"]
        complete = [int(k) for k, v in state["barriers"].items() if "decision" in v]
        snapshot = ([j["status"] for j in jobs], max(complete, default=-1))
        if snapshot != previous:
            print(json.dumps({"job_statuses": snapshot[0], "completed_step": snapshot[1]}), flush=True)
            previous = snapshot
        if any(j["status"] in ("FAILED", "CANCELLED") for j in jobs):
            for job in jobs:
                if job["status"] not in ("SUCCEEDED", "FAILED", "CANCELLED"):
                    api("/v1/jobs/" + job["job_id"] + "/cancel", "POST")
            (ROOT / "runs" / run_id / "failure.json").write_text(json.dumps(status, indent=2))
            raise RuntimeError("A participant failed; remaining training jobs were cancelled. See failure.json")
        if all(j["status"] == "SUCCEEDED" for j in jobs):
            collect(run_id)
            return
        time.sleep(30)
    raise RuntimeError("Monitor deadline exceeded")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("action", choices=["start", "status", "collect", "monitor"])
    parser.add_argument("run_id", nargs="?")
    args = parser.parse_args()
    if args.action == "start":
        print(json.dumps(api("/v1/shared-test", "POST"), indent=2))
    elif args.action == "collect":
        collect(args.run_id)
    elif args.action == "monitor":
        monitor(args.run_id)
    else:
        status = api("/v1/shared-test/" + args.run_id)
        state = status["state"]
        completed = [int(k) for k, v in state["barriers"].items() if "decision" in v]
        print(json.dumps({"jobs": status["jobs"], "started": state["started"],
                          "completed_barrier": max(completed, default=None),
                          "ready_ranks": list(state["barriers"].get("0", {}).get("reports", {}))}, indent=2))


if __name__ == "__main__":
    main()
