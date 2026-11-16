"""Phase A spike: can independent provider computers train ONE model together through a
per-job Ray head owned by the GreenTokens server?  Nothing here is product code.
Gradients are exchanged through Ray's own transfer (Gloo's address choice failed between Windows and Mac).

    python scripts/spike_job_cluster.py head                 # start the job head on this server (0 CPUs)
    python scripts/spike_job_cluster.py join-local --python <provider runtime python> [--cpus 4]
    python scripts/spike_job_cluster.py run --workers 2 [--steps 10 --examples 96]
    python scripts/spike_job_cluster.py down [--member]      # stop only what this script started

The head listens on 6379 so an already-installed provider app can join with its existing
"Join a group" box (code GT1-<ip>-<token>). Other head ports avoid the provider's own node ports.
Shutdown is scoped by temp folder; `ray stop` (which kills every Ray process) is never used.
"""
import argparse
import importlib.util
import json
import os
import secrets
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CODE_FILE = Path.home() / ".greentokens" / "spike_code.txt"   # outside the repo; holds the job token
HEAD_TEMP = "/tmp/gt-server"
HEAD_PORTS = {"--port": 6379, "--node-manager-port": 6501, "--object-manager-port": 6502,
              "--runtime-env-agent-port": 6503, "--dashboard-agent-grpc-port": 6504,
              "--dashboard-agent-listen-port": 6505, "--metrics-export-port": 6506,
              "--ray-client-server-port": 6507}
HEAD_WORKER_PORTS = (10200, 10299)
PINS = ["torch==2.15.0", "transformers==4.57.6", "datasets==4.8.5", "safetensors==0.8.0"]
GLOO_PORT = 6386  # inside the provider firewall rule; unused by provider nodes


def agent():
    path = ROOT / "apps/provider_app/src-tauri/agent/gt_agent.py"
    spec = importlib.util.spec_from_file_location("gt_agent", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def ray_env(token):
    env = dict(os.environ)
    env.update({"RAY_AUTH_MODE": "token", "RAY_AUTH_TOKEN": token, "RAY_USAGE_STATS_ENABLED": "0",
                "RAY_ENABLE_WINDOWS_OR_OSX_CLUSTER": "1", "PYTHONUTF8": "1"})
    return env


def ray_exe(python):
    return str(Path(python).with_name("ray.exe" if os.name == "nt" else "ray"))


def read_code():
    return agent().parse_code(CODE_FILE.read_text().strip())


def start_head(dashboard=False):
    """Start the job head with THIS Python's Ray (0 CPUs, fresh token). Returns (ip, token).

    dashboard=True also serves the Ray Jobs API on 127.0.0.1:8265, which the backend dispatcher uses.
    """
    token, ip = secrets.token_hex(16), agent().lan_ip()
    args = [ray_exe(sys.executable), "start", "--head", "--num-cpus", "0", "--num-gpus", "0",
            "--node-ip-address", ip, "--temp-dir", HEAD_TEMP,
            "--include-dashboard", "true" if dashboard else "false",
            "--min-worker-port", str(HEAD_WORKER_PORTS[0]), "--max-worker-port", str(HEAD_WORKER_PORTS[1]),
            "--disable-usage-stats", "--log-style", "record", "--log-color", "false"]
    if dashboard:
        args += ["--dashboard-host", "127.0.0.1", "--dashboard-port", "8265"]
    for flag, port in HEAD_PORTS.items():
        args += [flag, str(port)]
    result = subprocess.run(args, env=ray_env(token), capture_output=True, text=True)
    if result.returncode:
        raise RuntimeError("Head failed: " + (result.stderr or result.stdout).strip().splitlines()[-1][:300])
    CODE_FILE.parent.mkdir(exist_ok=True)
    CODE_FILE.write_text(f"GT1-{ip}-{token}")
    return ip, token


def head(_args):
    try:
        ip, _ = start_head()
    except RuntimeError as exc:
        sys.exit(str(exc))
    print(f"Job head running on {ip} (0 CPUs). Join code written to {CODE_FILE}")


def join_local(args):
    ip, token = read_code()
    a = agent()
    cmd = [ray_exe(args.python), "start", "--address", f"{ip}:6379"] + a.node_args(args.cpus, a.lan_ip())
    result = subprocess.run(cmd, env=ray_env(token), capture_output=True, text=True)
    if result.returncode:
        sys.exit("Join failed: " + (result.stderr or result.stdout).strip().splitlines()[-1][:300])
    print("This computer joined the job head as a provider node.")


def down(args):
    markers = [HEAD_TEMP] + (["/tmp/ray"] if args.member else [])
    stopped = 0
    for marker in markers:
        # Windows shows /tmp/ray as C:\tmp\ray in command lines, so match both spellings.
        for spelling in ([marker, marker.replace("/", "\\")] if os.name == "nt" else [marker]):
            stopped += _kill_matching(spelling)
    print(f"Stopped {stopped} processes scoped to {markers}.")


def _kill_matching(marker):
    """Kill only processes whose command line contains this folder; never `ray stop`."""
    if os.name == "nt":
        script = ("$m = @(Get-CimInstance Win32_Process | Where-Object { $_.CommandLine -and "
                  f"$_.CommandLine.Contains('{marker}') -and $_.ProcessId -ne {os.getpid()} }}); "
                  "$m | ForEach-Object { Stop-Process -Id $_.ProcessId -Force -ErrorAction SilentlyContinue }; $m.Count")
        out = subprocess.run(["powershell.exe", "-NoProfile", "-Command", script], capture_output=True, text=True).stdout
        return int(out.strip().splitlines()[-1] or 0) if out.strip() else 0
    return int(subprocess.run(["pkill", "-f", marker]).returncode == 0)


class Reducer:
    """Meeting point for the gradient exchange. Workers hand over a reference to their gradients; the data
    itself moves computer-to-computer through Ray's own transfer, so no PyTorch/Gloo address selection is needed."""

    def __init__(self, world):
        import asyncio
        self.world, self.data, self.events, self.asyncio = world, {}, {}, asyncio

    async def exchange(self, step, rank, refs):
        slot = self.data.setdefault(step, {})
        event = self.events.setdefault(step, self.asyncio.Event())
        slot[rank] = refs[0]
        if len(slot) == self.world:
            event.set()
        await event.wait()
        result = [slot[r] for r in sorted(slot)]
        for old in [s for s in self.data if s < step - 2]:  # keep memory bounded
            self.data.pop(old, None)
            self.events.pop(old, None)
        return result


class DDPWorker:
    """Runs on a provider node: synchronous data-parallel training. Self-contained so Ray ships it by value."""

    def info(self):
        import platform, socket, ray
        return {"host": socket.gethostname(), "os": f"{platform.system()} {platform.machine()}",
                "python": platform.python_version(), "ip": ray.util.get_node_ip_address()}

    def train(self, reducer, rank, world, steps, examples, global_batch, max_length, sync_every=1):
        import socket, time
        import numpy as np
        import ray, torch
        from datasets import load_dataset
        from transformers import AutoModelForSequenceClassification, AutoTokenizer, set_seed
        torch.set_num_threads(2)
        set_seed(42)
        tok = AutoTokenizer.from_pretrained("prajjwal1/bert-tiny")
        model = AutoModelForSequenceClassification.from_pretrained("prajjwal1/bert-tiny", num_labels=2)
        params = [p for p in model.parameters() if p.requires_grad]

        def flat(tensors):
            return torch.cat([t.reshape(-1) for t in tensors]).detach().numpy()

        def exchange(step, vector):
            ref = ray.put(vector)
            refs = ray.get(reducer.exchange.remote(step, rank, [ref]))
            return [ray.get(r) for r in refs]

        # Every worker starts from rank 0's exact weights (what DDP does at start-up), whatever the OS.
        start_sync = time.perf_counter()
        initial = exchange(-1, flat(params))[0]
        offset = 0
        with torch.no_grad():
            for p in params:
                p.copy_(torch.from_numpy(initial[offset:offset + p.numel()].copy()).view_as(p))
                offset += p.numel()
        raw = load_dataset("stanfordnlp/sst2")["train"].shuffle(seed=42).select(range(examples))
        sentences, labels = list(raw["sentence"]), list(raw["label"])  # datasets 4.x returns column objects
        enc = tok(sentences, truncation=True, padding="max_length", max_length=max_length, return_tensors="pt")
        ids_all, mask_all, labels_all = enc["input_ids"], enc["attention_mask"], torch.tensor(labels)
        shard = list(range(rank, examples, world))  # disjoint slice of the data for this computer
        per_worker = max(1, global_batch // world)
        opt = torch.optim.AdamW(params, lr=5e-5)
        losses, sync_seconds, cursor = [], 0.0, 0
        start = time.perf_counter()
        for step in range(steps):
            idx = [shard[(cursor + i) % len(shard)] for i in range(per_worker)]
            cursor += per_worker
            loss = model(input_ids=ids_all[idx], attention_mask=mask_all[idx], labels=labels_all[idx]).loss
            opt.zero_grad()
            loss.backward()
            if sync_every == 1:
                # Standard synchronous data-parallel: average the gradients every step.
                t = time.perf_counter()
                grads = exchange(step, flat([p.grad for p in params]))
                sync_seconds += time.perf_counter() - t
                average = np.mean(grads, axis=0)
                offset = 0
                for p in params:
                    p.grad.copy_(torch.from_numpy(average[offset:offset + p.numel()].copy()).view_as(p))
                    offset += p.numel()
                opt.step()
            else:
                # Periodic averaging ("local SGD"): train alone, then average the MODEL every sync_every steps
                # (and at the last step, so every computer ends with identical weights).
                opt.step()
                if (step + 1) % sync_every == 0 or step == steps - 1:
                    t = time.perf_counter()
                    weights = np.mean(exchange(step, flat(params)), axis=0)
                    sync_seconds += time.perf_counter() - t
                    offset = 0
                    with torch.no_grad():
                        for p in params:
                            p.copy_(torch.from_numpy(weights[offset:offset + p.numel()].copy()).view_as(p))
                            offset += p.numel()
            losses.append(round(loss.item(), 4))
        elapsed = time.perf_counter() - start
        checksum = sum(p.detach().double().sum().item() for p in params)
        return {"rank": rank, "host": socket.gethostname(), "steps": steps, "first_loss": losses[0],
                "last_loss": losses[-1], "seconds": round(elapsed, 2), "sync_seconds": round(sync_seconds, 2),
                "seconds_per_step": round(elapsed / steps, 3), "samples_per_second": round(per_worker * world * steps / elapsed, 1),
                "weights_checksum": round(checksum, 6)}


def run(args):
    ip, token = read_code()
    os.environ.update(ray_env(token))
    import ray
    from ray.util.placement_group import placement_group
    from ray.util.scheduling_strategies import PlacementGroupSchedulingStrategy
    ray.init(address=f"{ip}:6379", logging_level="ERROR")
    providers = [n for n in ray.nodes() if n["Alive"] and n["Resources"].get("CPU", 0) > 0]
    print("Provider nodes:", [(n["NodeManagerHostname"], n["Resources"].get("CPU")) for n in providers], flush=True)
    if len(providers) < args.workers:
        sys.exit(f"Need {args.workers} provider computers, only {len(providers)} joined.")
    Worker = ray.remote(num_cpus=2)(DDPWorker)
    # --preinstalled: the packages are already in each provider's runtime (how the product will work).
    options = {} if args.preinstalled else {"runtime_env": {"pip": PINS}}
    if args.host:  # run on one named computer (for comparing the computers one by one)
        from ray.util.scheduling_strategies import NodeAffinitySchedulingStrategy
        target = next((n for n in providers if n["NodeManagerHostname"].lower().startswith(args.host.lower())), None)
        if target is None:
            sys.exit(f"No joined computer named {args.host}.")
        strategies = [NodeAffinitySchedulingStrategy(target["NodeID"], soft=False)] * args.workers
    else:
        pg = placement_group([{"CPU": 2}] * args.workers, strategy="STRICT_SPREAD")
        ray.get(pg.ready(), timeout=120)
        strategies = [PlacementGroupSchedulingStrategy(pg, i) for i in range(args.workers)]
    actors = [Worker.options(scheduling_strategy=strategies[i], **options).remote() for i in range(args.workers)]
    infos = ray.get([a.info.remote() for a in actors], timeout=1800)
    print("Workers:", json.dumps(infos), flush=True)
    reducer = ray.remote(num_cpus=0, max_concurrency=32)(Reducer).remote(args.workers)
    results = ray.get([a.train.remote(reducer, r, args.workers, args.steps, args.examples, args.global_batch, args.max_length, args.sync_every)
                       for r, a in enumerate(actors)], timeout=3600)
    for r in results:
        busy = r["seconds"] - r["sync_seconds"]
        print(f"  {r['host']}: total {r['seconds']} s = {busy:.1f} s training ({busy / r['steps']:.3f} s/step) "
              f"+ {r['sync_seconds']} s waiting/exchanging; final loss {r['last_loss']}")
    same = len({r["weights_checksum"] for r in results}) == 1
    hosts = len({r["host"] for r in results})
    print("RESULT:", f"PASS - one model trained across {hosts} computer(s), weights identical on all" if same
          else "FAIL - replicas diverged")
    print(f"Speed: {results[0]['seconds_per_step']} s/step, {results[0]['samples_per_second']} samples/s "
          f"({args.workers} worker(s), global batch {args.global_batch}, sequence length {args.max_length}); "
          f"time spent exchanging gradients: {results[0]['sync_seconds']} s of {results[0]['seconds']} s")


def main():
    p = argparse.ArgumentParser()
    sub = p.add_subparsers(dest="cmd", required=True)
    sub.add_parser("head")
    j = sub.add_parser("join-local"); j.add_argument("--python", required=True); j.add_argument("--cpus", type=int, default=4)
    r = sub.add_parser("run"); r.add_argument("--workers", type=int, default=2)
    r.add_argument("--steps", type=int, default=10); r.add_argument("--examples", type=int, default=96)
    r.add_argument("--global-batch", type=int, default=24); r.add_argument("--max-length", type=int, default=64)
    r.add_argument("--host", help="run on the joined computer whose name starts with this")
    r.add_argument("--sync-every", type=int, default=1, help="1 = average gradients every step; N = average the model every N steps")
    r.add_argument("--preinstalled", action="store_true", help="packages already installed in each provider runtime")
    d = sub.add_parser("down"); d.add_argument("--member", action="store_true")
    args = p.parse_args()
    {"head": head, "join-local": join_local, "run": run, "down": down}[args.cmd](args)


if __name__ == "__main__":
    main()
