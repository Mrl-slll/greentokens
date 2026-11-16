"""Bring up / tear down / check the GreenTokens demo cluster on this (server) computer.

    python -m scripts.demo_cluster up [--cpus 4]   # job head + this PC as a provider + backend
    python -m scripts.demo_cluster check [--json]  # read-only: which computers joined, and are they ready?
    python -m scripts.demo_cluster down            # stops only what `up` started; never `ray stop`

The Provider app must stay closed on this computer: its power button restarts Ray and would
replace the group. Other computers join with the code written to ~/.greentokens/spike_code.txt
(open that file yourself; the code is never printed here).
"""
import argparse
import json
import os
import socket
import subprocess
import sys
import time
import urllib.request
from pathlib import Path
from types import SimpleNamespace

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import spike_job_cluster as spike  # noqa: E402  (head, join, scoped shutdown)

HOME = Path.home() / ".greentokens"
LOG = HOME / "logs" / "backend.log"
BACKEND_MARKERS = ["scripts.local_stack", "core.jobs.dispatcher", "core.api.main"]


def runtime_python():
    """The Provider app's private Python. Every provider computer runs this same build."""
    if os.name == "nt":
        path = Path(os.environ["LOCALAPPDATA"]) / "ai.greentokens.provider/runtime/Scripts/python.exe"
    else:
        base = Path.home() / "Library/Application Support" if sys.platform == "darwin" else Path.home() / ".local/share"
        path = base / "ai.greentokens.provider/runtime/bin/python"
    if not path.is_file():
        sys.exit(f"Provider runtime not found at {path}. Open the Provider app once so it can prepare itself, then close it.")
    return str(path)


def port_in_use(port):
    with socket.socket() as probe:
        return probe.connect_ex(("127.0.0.1", port)) == 0


def app_running():
    if os.name != "nt":
        return subprocess.run(["pgrep", "-f", "greentokens-provider"], capture_output=True).returncode == 0
    out = subprocess.run(["tasklist", "/FI", "IMAGENAME eq greentokens-provider.exe", "/NH"], capture_output=True, text=True).stdout
    return "greentokens-provider.exe" in out.lower()


def wait_health(seconds=180):
    deadline = time.monotonic() + seconds
    while time.monotonic() < deadline:
        try:
            with urllib.request.urlopen("http://127.0.0.1:8000/health", timeout=2):
                return True
        except OSError:
            time.sleep(3)
    return False


def up(args):
    if app_running():
        sys.exit("The Provider app is running. Close it first (its power button would replace this group).")
    busy = [p for p in (6379, 8000, 8265) if port_in_use(p)]
    if busy:
        sys.exit(f"Ports {busy} are already in use. Run `python -m scripts.demo_cluster down` first.")
    if not (HOME / "api_keys.json").is_file() and not os.environ.get("GT_API_KEYS"):
        print("Note: no API keys configured (~/.greentokens/api_keys.json). Only the local dev identity will work.")
    py = runtime_python()
    print("1/3 Starting the job head (no training work of its own)...", flush=True)
    code = ("import sys; sys.path.insert(0, r'%s'); import spike_job_cluster as s; "
            "ip, _ = s.start_head(dashboard=True); print(ip)" % (ROOT / "scripts"))
    result = subprocess.run([py, "-I", "-c", code], capture_output=True, text=True)
    if result.returncode:
        sys.exit("Head failed to start: " + (result.stderr or result.stdout).strip().splitlines()[-1][:300])
    print(f"2/3 Joining this computer as a provider ({args.cpus} CPUs)...", flush=True)
    joined = subprocess.run([py, "-I", str(ROOT / "scripts/spike_job_cluster.py"), "join-local", "--python", py,
                             "--cpus", str(args.cpus)], capture_output=True, text=True)
    if joined.returncode:
        sys.exit("Join failed: " + (joined.stderr or joined.stdout).strip().splitlines()[-1][:300])
    print("3/3 Starting the GreenTokens backend...", flush=True)
    start_backend()
    print("\nReady. Backend: http://127.0.0.1:8000 (private). Group code file:", spike.CODE_FILE)
    print("Next: have the other computer join with that code, then run: python -m scripts.demo_cluster check")


def start_backend():
    """Start only the backend (API + dispatcher) attached to the running job head."""
    if port_in_use(8000):
        sys.exit("Something already listens on port 8000. Run `down` first, or the backend is already up.")
    if not port_in_use(6379):
        sys.exit("The job head is not running. Run `python -m scripts.demo_cluster up` instead.")
    LOG.parent.mkdir(parents=True, exist_ok=True)
    env = dict(os.environ, GT_GROUP_CODE=spike.CODE_FILE.read_text().strip())
    command = [sys.executable, "-m", "scripts.local_stack", "--attach"]
    # Windows: DETACHED_PROCESS | NEW_PROCESS_GROUP, and try to break away from the launcher's job object so the
    # backend keeps running after the terminal or tool that started it closes.
    base = 0x00000008 | 0x00000200 if os.name == "nt" else 0
    for flags in ((base | 0x01000000, base) if os.name == "nt" else (0,)):
        try:
            with open(LOG, "ab") as log:
                subprocess.Popen(command, cwd=ROOT, env=env, stdout=log, stderr=log, stdin=subprocess.DEVNULL,
                                 creationflags=flags, start_new_session=(os.name != "nt"))
            break
        except OSError:
            continue  # breakaway not permitted here; fall back to plain detach
    if not wait_health():
        sys.exit(f"The backend did not become healthy. See {LOG} (it never contains the group code).")


def backend(_args):
    start_backend()
    print("Backend is up: http://127.0.0.1:8000 (private).")


def down(_args):
    stopped = sum(spike._kill_matching(m) for m in BACKEND_MARKERS)
    for marker in (spike.HEAD_TEMP, "/tmp/ray"):
        for spelling in ([marker, marker.replace("/", "\\")] if os.name == "nt" else [marker]):
            stopped += spike._kill_matching(spelling)
    print(f"Stopped {stopped} processes (backend + only the Ray processes in GreenTokens' own folders).")


def probe_node(peers):
    """Runs ON a provider computer."""
    import platform
    import socket as sock
    import ray
    info = {"host": sock.gethostname(), "os": f"{platform.system()} {platform.machine()}",
            "python": platform.python_version(), "ray": ray.__version__}
    for name in ("torch", "transformers", "datasets"):
        try:
            info[name] = str(__import__(name).__version__)  # plain str: torch's own type can't be unpickled here
        except Exception:
            info[name] = None
    reach = {}
    for ip, port in peers:
        try:
            sock.create_connection((ip, port), 3).close()
            reach[f"{ip}:{port}"] = True
        except OSError:
            reach[f"{ip}:{port}"] = False
    info["reach"] = reach
    return info


def check(args):
    ip, token = spike.read_code()
    os.environ.update(spike.ray_env(token))
    os.environ["RAY_DEFAULT_PYTHON_VERSION_MATCH_LEVEL"] = "minor"  # patch differences only warn
    import ray
    from ray.util.scheduling_strategies import NodeAffinitySchedulingStrategy
    ray.init(address=f"{ip}:6379", logging_level="ERROR")
    nodes = [n for n in ray.nodes() if n["Alive"] and n["Resources"].get("CPU", 0) > 0]
    rows = []
    probe = ray.remote(num_cpus=0, max_retries=0)(probe_node)
    for n in nodes:
        peers = [(m["NodeManagerAddress"], m["NodeManagerPort"]) for m in nodes if m is not n] + [(ip, 6379)]
        ref = probe.options(scheduling_strategy=NodeAffinitySchedulingStrategy(n["NodeID"], soft=False)).remote(peers)
        try:
            info = ray.get(ref, timeout=60)
            info["cpus"] = int(n["Resources"].get("CPU", 0))
        except Exception as exc:
            info = {"host": n["NodeManagerHostname"], "error": type(exc).__name__}
        rows.append(info)
    versions = {(r.get("python"), r.get("ray")) for r in rows if "python" in r}
    for r in rows:
        problems = []
        if "error" in r:
            problems.append("could not be reached (" + r["error"] + ")")
        else:
            if not r.get("torch") or not r.get("transformers") or not r.get("datasets"):
                problems.append("training packages not installed on this computer")
            if len(versions) > 1:
                problems.append("Python/Ray version differs from the other computer")
            blocked = [k for k, ok in r["reach"].items() if not ok]
            if blocked:
                problems.append("cannot reach " + ", ".join(blocked) + " (firewall or network blocks computer-to-computer traffic)")
        r["problems"] = problems
    if len(rows) < 2:
        note = "Only %d computer has joined. Distributed training needs at least 2." % len(rows)
    else:
        note = ""
    if args.json:
        print(json.dumps({"computers": rows, "note": note}, indent=1))
    else:
        for r in rows:
            mark = "OK  " if not r["problems"] else "FAIL"
            detail = (f"{r.get('os')} | Python {r.get('python')} | Ray {r.get('ray')} | torch {r.get('torch') or '-'} | {r.get('cpus')} CPUs"
                      if "python" in r else "")
            print(f"{mark} {r['host']}  {detail}")
            for p in r["problems"]:
                print("       -", p)
        print(note or f"{len(rows)} computers joined.")
    ray.shutdown()
    return 0 if rows and len(rows) >= 2 and not any(r["problems"] for r in rows) else 1


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = parser.add_subparsers(dest="cmd", required=True)
    u = sub.add_parser("up")
    u.add_argument("--cpus", type=int, default=4)
    sub.add_parser("down")
    sub.add_parser("backend", help="restart only the backend (the job head must already be running)")
    c = sub.add_parser("check")
    c.add_argument("--json", action="store_true")
    args = parser.parse_args()
    code = {"up": up, "down": down, "check": check, "backend": backend}[args.cmd](args)
    sys.exit(code or 0)


if __name__ == "__main__":
    main()
