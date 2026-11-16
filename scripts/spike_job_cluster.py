"""Phase A spike: can independent provider computers train ONE model together through a
per-job Ray head owned by the GreenTokens server?  Nothing here is product code.

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


def head(_args):
    token, ip = secrets.token_hex(16), agent().lan_ip()
    args = [ray_exe(sys.executable), "start", "--head", "--num-cpus", "0", "--num-gpus", "0",
            "--node-ip-address", ip, "--temp-dir", HEAD_TEMP, "--include-dashboard", "false",
            "--min-worker-port", str(HEAD_WORKER_PORTS[0]), "--max-worker-port", str(HEAD_WORKER_PORTS[1]),
            "--disable-usage-stats", "--log-style", "record", "--log-color", "false"]
    for flag, port in HEAD_PORTS.items():
        args += [flag, str(port)]
    result = subprocess.run(args, env=ray_env(token), capture_output=True, text=True)
    if result.returncode:
        sys.exit("Head failed: " + (result.stderr or result.stdout).strip().splitlines()[-1][:300])
    CODE_FILE.parent.mkdir(exist_ok=True)
    CODE_FILE.write_text(f"GT1-{ip}-{token}")
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
        script = ("$n=0; Get-CimInstance Win32_Process | Where-Object { $_.CommandLine -and "
                  f"$_.CommandLine.Contains('{marker}') -and $_.ProcessId -ne {os.getpid()} }} | "
                  "ForEach-Object { Stop-Process -Id $_.ProcessId -Force -ErrorAction SilentlyContinue; $n++ }; $n")
        out = subprocess.run(["powershell.exe", "-NoProfile", "-Command", script], capture_output=True, text=True).stdout
        return int(out.strip() or 0)
    return int(subprocess.run(["pkill", "-f", marker]).returncode == 0)


class DDPWorker:
    """Runs on a provider node. Self-contained so Ray ships it by value."""

    def info(self):
        import platform, socket, ray
        return {"host": socket.gethostname(), "os": f"{platform.system()} {platform.machine()}",
                "python": platform.python_version(), "ip": ray.util.get_node_ip_address()}

    def free_port(self):
        import socket
        with socket.socket() as s:
            s.bind(("", 0))
            return s.getsockname()[1]

    def setup(self, master, port, rank, world):
        from datetime import timedelta
        import torch, torch.distributed as dist
        torch.set_num_threads(2)
        dist.init_process_group("gloo", init_method=f"tcp://{master}:{port}", rank=rank,
                                world_size=world, timeout=timedelta(seconds=120))
        self.rank, self.world = rank, world
        return rank

    def allreduce(self):
        import torch, torch.distributed as dist
        t = torch.tensor([float(self.rank + 1)])
        dist.all_reduce(t)
        return t.item()

    def train(self, steps, examples):
        import socket, time
        import torch, torch.distributed as dist
        from datasets import load_dataset
        from torch.nn.parallel import DistributedDataParallel
        from torch.utils.data import DataLoader, DistributedSampler
        from transformers import AutoModelForSequenceClassification, AutoTokenizer, set_seed
        set_seed(42)
        tok = AutoTokenizer.from_pretrained("prajjwal1/bert-tiny")
        model = DistributedDataParallel(AutoModelForSequenceClassification.from_pretrained("prajjwal1/bert-tiny", num_labels=2))
        raw = load_dataset("stanfordnlp/sst2")["train"].shuffle(seed=42).select(range(examples))
        sentences, labels = list(raw["sentence"]), list(raw["label"])  # datasets 4.x returns column objects
        enc = tok(sentences, truncation=True, padding="max_length", max_length=64, return_tensors="pt")
        data = list(zip(enc["input_ids"], enc["attention_mask"], torch.tensor(labels)))
        loader = DataLoader(data, batch_size=max(1, 24 // self.world), sampler=DistributedSampler(data, self.world, self.rank, seed=42))
        opt = torch.optim.AdamW(model.parameters(), lr=5e-5)
        done, losses, start = 0, [], time.perf_counter()
        while done < steps:
            for ids, mask, labels in loader:
                loss = model(input_ids=ids, attention_mask=mask, labels=labels).loss
                opt.zero_grad(); loss.backward(); opt.step()
                losses.append(round(loss.item(), 4)); done += 1
                if done >= steps:
                    break
        # Proof the replicas stayed identical: checksum of all weights must match on every rank.
        checksum = sum(p.detach().double().sum().item() for p in model.parameters())
        dist.destroy_process_group()
        return {"rank": self.rank, "host": socket.gethostname(), "steps": done, "first_loss": losses[0],
                "last_loss": losses[-1], "seconds": round(time.perf_counter() - start, 1), "weights_checksum": round(checksum, 6)}


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
    pg = placement_group([{"CPU": 2}] * args.workers, strategy="STRICT_SPREAD")
    ray.get(pg.ready(), timeout=120)
    Worker = ray.remote(num_cpus=2)(DDPWorker)
    # --preinstalled: the packages are already in each provider's runtime (how the product will work).
    options = {} if args.preinstalled else {"runtime_env": {"pip": PINS}}
    actors = [Worker.options(scheduling_strategy=PlacementGroupSchedulingStrategy(pg, i), **options).remote()
              for i in range(args.workers)]
    t0 = time.perf_counter()
    print("Preparing each computer (first time installs torch etc.; can take several minutes)...", flush=True)
    infos = ray.get([a.info.remote() for a in actors], timeout=1800)
    print("Workers:", json.dumps(infos), f"(ready after {time.perf_counter() - t0:.0f}s)", flush=True)
    port = ray.get(actors[0].free_port.remote())  # chosen by rank 0, so it never collides with Ray's own ports
    print(f"Rank 0 is {infos[0]['host']} ({infos[0]['os']}), Gloo port {port}", flush=True)
    ray.get([a.setup.remote(infos[0]["ip"], port, r, args.workers) for r, a in enumerate(actors)], timeout=300)
    print("Gloo all-reduce (expect", sum(range(1, args.workers + 1)), "):", ray.get([a.allreduce.remote() for a in actors]), flush=True)
    results = ray.get([a.train.remote(args.steps, args.examples) for a in actors], timeout=1800)
    print(json.dumps(results, indent=1))
    same = len({r["weights_checksum"] for r in results}) == 1
    print("RESULT:", "PASS - one model trained across", len({r['host'] for r in results}), "computer(s), weights identical" if same
          else "FAIL - replicas diverged")


def main():
    p = argparse.ArgumentParser()
    sub = p.add_subparsers(dest="cmd", required=True)
    sub.add_parser("head")
    j = sub.add_parser("join-local"); j.add_argument("--python", required=True); j.add_argument("--cpus", type=int, default=4)
    r = sub.add_parser("run"); r.add_argument("--workers", type=int, default=2)
    r.add_argument("--steps", type=int, default=10); r.add_argument("--examples", type=int, default=96)
    r.add_argument("--preinstalled", action="store_true", help="packages already installed in each provider runtime")
    d = sub.add_parser("down"); d.add_argument("--member", action="store_true")
    args = p.parse_args()
    {"head": head, "join-local": join_local, "run": run, "down": down}[args.cmd](args)


if __name__ == "__main__":
    main()
