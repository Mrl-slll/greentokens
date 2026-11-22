"""GreenTokens Provider agent: lead or join a private Ray group on the local network.

Called by the desktop app with fixed actions and validated arguments. Prints exactly one
JSON line and always exits 0; failures are {"ok": false, "error": "<friendly text>"}.

Security: the group is protected by Ray token authentication (the token is inside the join
code), only private LAN addresses are accepted, the dashboard stays on 127.0.0.1, and the
firewall rule covers a fixed port list on the Private network profile only.
"""
import argparse
import base64
import hashlib
import ipaddress
import json
import os
import re
import shutil
import socket
import subprocess
import sys
import time
from pathlib import Path

GCS_PORT = 6379
FIXED_PORTS = {
    "--node-manager-port": 6380,
    "--object-manager-port": 6381,
    "--runtime-env-agent-port": 6382,
    "--dashboard-agent-grpc-port": 6383,
    "--dashboard-agent-listen-port": 6384,
    "--metrics-export-port": 6385,
}
CLIENT_SERVER_PORT = 6386
# Ray copies the leader's temp folder to computers that join. A Windows path (C:/Users/...) is
# unusable on a Mac, so every computer uses this one: Windows reads it as C:/tmp/ray, macOS and
# Linux as /tmp/ray (short enough for Ray's socket paths).
TEMP_DIR = "/tmp/ray"
WORKER_PORTS = (10002, 10101)
FIREWALL_PORTS = ["6379-6386", f"{WORKER_PORTS[0]}-{WORKER_PORTS[1]}"]
FIREWALL_RULE = "GreenTokens Provider (Ray)"
CODE_RE = re.compile(r"^GT1-(\d{1,3}(?:\.\d{1,3}){3})-([0-9a-f]{32})$")
NO_WINDOW = 0x0800_0000 if os.name == "nt" else 0


class Friendly(Exception):
    """An error whose message is safe to show to a non-technical user."""


def parse_code(code):
    match = CODE_RE.match((code or "").strip())
    if not match:
        raise Friendly("That group code doesn't look right. Copy it again from the leader's computer.")
    ip, token = match.groups()
    try:
        address = ipaddress.ip_address(ip)
    except ValueError:
        raise Friendly("That group code doesn't look right. Copy it again from the leader's computer.")
    if not address.is_private or address.is_loopback:
        raise Friendly("Groups only work between computers on the same home or office network.")
    return ip, token


def lan_ip():
    # A UDP "connect" picks the outgoing interface without sending any packet.
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
            s.connect(("192.0.2.1", 9))
            ip = s.getsockname()[0]
    except OSError:
        ip = socket.gethostbyname(socket.gethostname())
    address = ipaddress.ip_address(ip)
    if not address.is_private or address.is_loopback:
        raise Friendly("This computer isn't on a home or office network right now.")
    return ip


def ray_executable():
    sibling = Path(sys.executable).with_name("ray.exe" if os.name == "nt" else "ray")
    found = sibling if sibling.is_file() else shutil.which("ray")
    if not found:
        raise Friendly("The computing runtime isn't installed correctly. Restart the app to repair it.")
    return str(found)


def ray_env(token=None):
    env = dict(os.environ)
    env.update({"RAY_ENABLE_WINDOWS_OR_OSX_CLUSTER": "1", "RAY_USAGE_STATS_ENABLED": "0",
                "RAY_AUTH_MODE": "token", "PYTHONUTF8": "1"})
    if token:
        env["RAY_AUTH_TOKEN"] = token
    return env


def run(args, env=None, timeout=180):
    return subprocess.run(args, env=env, capture_output=True, text=True, timeout=timeout,
                          stdin=subprocess.DEVNULL, creationflags=NO_WINDOW)


def node_args(cpus, ip):
    args = ["--node-ip-address", ip, "--num-cpus", str(cpus), "--num-gpus", "0",
            "--min-worker-port", str(WORKER_PORTS[0]), "--max-worker-port", str(WORKER_PORTS[1]),
            "--temp-dir", TEMP_DIR,
            "--disable-usage-stats", "--log-style", "record", "--log-color", "false"]
    for flag, port in FIXED_PORTS.items():
        args += [flag, str(port)]
    return args


def stop():
    run([ray_executable(), "stop", "--grace-period", "10"], env=ray_env(), timeout=120)
    return {"ok": True, "connected": False}


def start(role, code, cpus):
    ip, token = parse_code(code)
    mine = lan_ip()
    if role == "host" and ip != mine:
        raise Friendly("This computer's network address changed. Create a new group code and share it again.")
    stop()  # Start clean: one GreenTokens node per computer.
    if role == "host":
        args = ["start", "--head", "--port", str(GCS_PORT), "--ray-client-server-port", str(CLIENT_SERVER_PORT),
                "--dashboard-host", "127.0.0.1", "--include-dashboard", "true"] + node_args(cpus, mine)
    else:
        args = ["start", "--address", f"{ip}:{GCS_PORT}"] + node_args(cpus, mine)
    result = run([ray_executable()] + args, env=ray_env(token))
    if result.returncode != 0:
        stop()
        detail = (result.stderr or result.stdout).strip().splitlines()[-1:] or [""]
        if role == "member":
            raise Friendly("Couldn't reach the group leader. Check that the leader is connected, both computers are on the "
                           f"same network, and the code is current. ({detail[0][:160]})")
        raise Friendly(f"Couldn't start the group on this computer. ({detail[0][:160]})")
    return {"ok": True, "connected": True, "role": role, "address": mine}


def raylet_running():
    if os.name != "nt":
        return run(["pgrep", "-f", "raylet"]).returncode == 0
    out = run(["tasklist", "/FI", "IMAGENAME eq raylet.exe", "/NH"]).stdout
    return "raylet.exe" in out.lower()


def parse_active_nodes(text):
    """Count live nodes in `ray status` output: entries under 'Active:' and 'Idle:'."""
    count, counting = 0, False
    for line in text.splitlines():
        stripped = line.strip()
        if stripped in ("Active:", "Idle:"):
            counting = True
        elif stripped.endswith(":"):
            counting = False  # Pending:, Recent failures:, Usage:, ...
        elif counting:
            match = re.match(r"^(\d+)\s+node_[0-9a-fA-F]+", stripped)
            if match:
                count += int(match.group(1))
    return count


def status(code):
    ip, token = parse_code(code)
    if not raylet_running():
        return {"ok": True, "connected": False, "nodes": 0}
    result = run([ray_executable(), "status", "--address", f"{ip}:{GCS_PORT}"], env=ray_env(token), timeout=60)
    if result.returncode != 0:
        return {"ok": True, "connected": False, "nodes": 0, "detail": "leader unreachable"}
    return {"ok": True, "connected": True, "nodes": parse_active_nodes(result.stdout)}


def powershell(script, timeout=120):
    encoded = base64.b64encode(script.encode("utf-16-le")).decode("ascii")
    return run(["powershell.exe", "-NoProfile", "-NonInteractive", "-EncodedCommand", encoded], timeout=timeout)


def check():
    ip = lan_ip()
    info = {"ok": True, "lan_ip": ip, "firewall": True, "network_private": True}
    if os.name == "nt":
        script = (
            f"$rule = @(Get-NetFirewallRule -DisplayName '{FIREWALL_RULE}' -ErrorAction SilentlyContinue).Count -gt 0;"
            f"$idx = (Get-NetIPAddress -IPAddress '{ip}' -ErrorAction SilentlyContinue | Select-Object -First 1).InterfaceIndex;"
            "$cat = if ($idx) { [string](Get-NetConnectionProfile -InterfaceIndex $idx -ErrorAction SilentlyContinue).NetworkCategory } else { '' };"
            "[pscustomobject]@{ rule = $rule; category = $cat } | ConvertTo-Json -Compress"
        )
        result = powershell(script)
        try:
            data = json.loads(result.stdout.strip() or "{}")
        except ValueError:
            data = {}
        info["firewall"] = bool(data.get("rule"))
        info["network_private"] = data.get("category") in ("Private", "DomainAuthenticated")
    return info


def allow_firewall():
    """One-time, elevated: allow Ray's fixed ports on the Private network profile only."""
    if os.name != "nt":
        return {"ok": True}
    ports = ",".join(f"'{p}'" for p in FIREWALL_PORTS)
    inner = (f"New-NetFirewallRule -DisplayName '{FIREWALL_RULE}' -Direction Inbound -Protocol TCP "
             f"-LocalPort {ports} -Profile Private -Action Allow | Out-Null")
    inner_encoded = base64.b64encode(inner.encode("utf-16-le")).decode("ascii")
    outer = ("Start-Process powershell.exe -Verb RunAs -Wait -WindowStyle Hidden "
             f"-ArgumentList '-NoProfile','-EncodedCommand','{inner_encoded}'")
    powershell(outer, timeout=300)
    if not check()["firewall"]:
        raise Friendly("Windows Firewall wasn't updated. Choose Yes when Windows asks for permission.")
    return {"ok": True}


# ---------------------------------------------------------------------------------------------
# Provider worker: connects OUTWARD to the GreenTokens server, asks for approved work, runs it,
# returns results. No Ray on this computer and no `ray stop`. Settings come from environment
# variables so the provider key never appears in the process list:
#   GT_SERVER (https URL), GT_PROVIDER_KEY, GT_DEVICE_ID, GT_DEVICE_NAME, GT_HOME (app data folder)
# The app stops the worker by creating GT_HOME/worker.stop. State for the app: GT_HOME/worker-state.json
# ---------------------------------------------------------------------------------------------
AGENT_VERSION = "0.3.1"
LOG_TAIL_BYTES = 60_000


def _http(server, key, method, path, body=None, data=None, params=None, timeout=60):
    import urllib.error
    import urllib.parse
    import urllib.request
    url = server.rstrip("/") + path + ("?" + urllib.parse.urlencode(params) if params else "")
    headers = {"Authorization": "Bearer " + key, "User-Agent": "GreenTokens-Provider/" + AGENT_VERSION}
    if body is not None:
        data = json.dumps(body).encode()
        headers["Content-Type"] = "application/json"
    elif data is not None:
        headers["Content-Type"] = "application/octet-stream"
    request = urllib.request.Request(url, data=data, method=method, headers=headers)
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            return response.status, response.read(), dict(response.headers)
    except urllib.error.HTTPError as exc:
        return exc.code, exc.read()[:2000], dict(exc.headers or {})


def _total_ram_gb():
    """Total memory without extra packages (psutil is not in the runtime)."""
    try:
        if os.name == "nt":
            import ctypes

            class MemoryStatus(ctypes.Structure):
                _fields_ = [("length", ctypes.c_ulong), ("load", ctypes.c_ulong), ("total", ctypes.c_ulonglong),
                            ("avail", ctypes.c_ulonglong), ("total_page", ctypes.c_ulonglong), ("avail_page", ctypes.c_ulonglong),
                            ("total_virtual", ctypes.c_ulonglong), ("avail_virtual", ctypes.c_ulonglong),
                            ("avail_extended", ctypes.c_ulonglong)]
            status = MemoryStatus()
            status.length = ctypes.sizeof(MemoryStatus)
            ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(status))
            return round(status.total / 1024 ** 3, 1)
        if sys.platform == "darwin":
            return round(int(run(["sysctl", "-n", "hw.memsize"], timeout=10).stdout.strip()) / 1024 ** 3, 1)
        with open("/proc/meminfo") as f:
            return round(int(f.readline().split()[1]) / 1024 ** 2, 1)
    except Exception:
        return 0.0


def capabilities():
    """What this computer can do: reported to the server with every heartbeat."""
    import platform
    caps = {"os": platform.system(), "arch": platform.machine(), "cpus": os.cpu_count() or 0, "ram_gb": 0.0,
            "gpus": [], "cuda_driver": None, "torch": None, "torch_cuda": False,
            "python": platform.python_version(), "agent": AGENT_VERSION}
    caps["ram_gb"] = _total_ram_gb()
    smi = shutil.which("nvidia-smi")
    if smi:
        try:
            out = run([smi, "--query-gpu=name,memory.total", "--format=csv,noheader,nounits"], timeout=20).stdout
            for line in out.strip().splitlines():
                name, _, mem = line.partition(",")
                caps["gpus"].append({"name": name.strip()[:255], "vram_gb": round(float(mem.strip()) / 1024, 1) if mem.strip() else None})
            match = re.search(r"CUDA Version:\s*([0-9.]+)", run([smi], timeout=20).stdout)
            caps["cuda_driver"] = match.group(1) if match else None
        except Exception:
            pass
    try:
        probe = run([sys.executable, "-c", "import json,torch;print(json.dumps([torch.__version__, torch.cuda.is_available()]))"], timeout=120)
        version, cuda = json.loads(probe.stdout.strip().splitlines()[-1])
        caps["torch"], caps["torch_cuda"] = version, bool(cuda)
    except Exception:
        pass
    return caps


class Worker:
    def __init__(self, server, key, device_id, name, home):
        self.server, self.key, self.device, self.name = server, key, device_id, name
        self.home = Path(home)
        self.stop_file, self.state_file = self.home / "worker.stop", self.home / "worker-state.json"
        self.caps = None

    def state(self, **fields):
        fields.update({"updated": time.time(), "device_id": self.device, "server": self.server})
        tmp = self.state_file.with_suffix(".tmp")
        tmp.write_text(json.dumps(fields), encoding="utf-8")
        os.replace(tmp, self.state_file)

    def stopping(self):
        return self.stop_file.exists()

    def call(self, method, path, **kwargs):
        status, body, headers = _http(self.server, self.key, method, path, **kwargs)
        if status in (401, 403):
            raise Friendly("Your GreenTokens session expired or was revoked. Sign out and sign in again.")
        if status >= 500:
            raise OSError(f"server error {status}")
        return status, body, headers

    def heartbeat(self, status="online"):
        self.call("POST", "/v1/provider/heartbeat", body={"device_id": self.device, "name": self.name,
                                                          "status": status, "capabilities": self.caps})

    def package(self, workload):
        """Download (once) and verify an approved workload package; reuse it for later jobs."""
        cache = self.home / "packages" / workload["sha256"]
        if (cache / ".verified").exists():
            return cache
        status, data, headers = self.call("GET", workload["url"], timeout=120)
        digest = hashlib.sha256(data).hexdigest()
        if status != 200 or digest != workload["sha256"] or headers.get("X-GT-SHA256", digest) != digest:
            raise Friendly("A workload package failed its checksum and was not run.")
        import io
        import zipfile
        cache.mkdir(parents=True, exist_ok=True)
        with zipfile.ZipFile(io.BytesIO(data)) as zf:
            for member in zf.namelist():
                target = (cache / member).resolve()
                if cache.resolve() not in target.parents:
                    raise Friendly("A workload package contained an unsafe path and was not run.")
            zf.extractall(cache)
        (cache / ".verified").write_text(digest)
        return cache

    def run_job(self, job):
        import collections
        import subprocess
        import threading
        attempt, q = job["attempt_id"], {"device_id": self.device}
        package = self.package(job["workload"])
        folder = self.home / "jobs" / attempt
        shutil.rmtree(folder, ignore_errors=True)
        (folder / "out").mkdir(parents=True)
        (folder / "params.json").write_text(json.dumps(job["parameters"]), encoding="utf-8")
        tail, progress = collections.deque(maxlen=400), {}
        proc = subprocess.Popen([sys.executable, str(package / "workload.py"), "--params", str(folder / "params.json"),
                                 "--out", str(folder / "out")], cwd=str(folder), stdout=subprocess.PIPE,
                                stderr=subprocess.STDOUT, text=True, encoding="utf-8", errors="replace",
                                stdin=subprocess.DEVNULL, creationflags=NO_WINDOW)

        def read():
            for line in proc.stdout:
                tail.append(line.rstrip())
                if line.startswith("GT_PROGRESS "):
                    try:
                        progress.update(json.loads(line[12:]))
                    except ValueError:
                        pass
        threading.Thread(target=read, daemon=True).start()
        started, renewed, outcome = time.time(), 0.0, None
        while proc.poll() is None:
            self.state(state="working", job={"id": job["job_id"], "workload": job["workload"]["name"],
                                             "started": started, "progress": dict(progress)})
            if self.stopping():
                proc.kill()  # the server's lease expires and another provider takes the job
                outcome = "stopped"
                break
            if time.time() - started > job["timeout_seconds"]:
                proc.kill()
                outcome = "timeout"
                break
            if time.time() - renewed > 15:
                status, body, _ = self.call("POST", f"/v1/provider/work/{attempt}/lease", body={**q, "progress": dict(progress)})
                renewed = time.time()
                if status == 200 and not json.loads(body).get("continue", True):
                    proc.kill()
                    outcome = "cancelled"
                    break
            time.sleep(1)
        proc.wait()
        log = "\n".join(tail).encode("utf-8", "replace")[-LOG_TAIL_BYTES:]
        try:
            if outcome == "stopped":
                return
            self.call("PUT", f"/v1/provider/work/{attempt}/artifacts/log", data=log, params=q)
            metrics_file, model_file = folder / "out" / "metrics.json", folder / "out" / "model.safetensors"
            if outcome is None and proc.returncode == 0 and metrics_file.exists():
                output = {"result": json.loads(metrics_file.read_text(encoding="utf-8")), "job_id": job["job_id"], "attempt_id": attempt}
                self.call("PUT", f"/v1/provider/work/{attempt}/artifacts/output", data=json.dumps(output).encode(), params=q)
                if model_file.exists():
                    self.call("PUT", f"/v1/provider/work/{attempt}/artifacts/model", data=model_file.read_bytes(), params=q, timeout=600)
                done = {"status": "SUCCEEDED"}
            elif outcome == "cancelled":
                done = {"status": "CANCELLED"}
            else:
                code = "RUNTIME_EXCEEDED" if outcome == "timeout" else "NO_GPU" if proc.returncode == 3 else "WORKLOAD_FAILED"
                done = {"status": "FAILED", "error_code": code}
            self.call("POST", f"/v1/provider/work/{attempt}/complete", body={**q, **done})
        finally:
            shutil.rmtree(folder, ignore_errors=True)  # keep the package cache, drop the job's files

    def loop(self):
        self.stop_file.unlink(missing_ok=True)
        self.state(state="starting")
        self.caps = capabilities()
        backoff = 2
        while not self.stopping():
            try:
                self.heartbeat("online")
                self.state(state="online", capabilities=self.caps)
                status, body, _ = self.call("POST", "/v1/provider/work", body={"device_id": self.device, "wait_seconds": 20}, timeout=60)
                if status == 200:
                    self.run_job(json.loads(body))
                backoff = 2
            except Friendly as exc:
                self.state(state="error", error=str(exc))
                return {"ok": False, "error": str(exc)}
            except Exception as exc:  # network loss, server restart: keep trying, never give up silently
                self.state(state="reconnecting", error=type(exc).__name__)
                for _ in range(backoff):
                    if self.stopping():
                        break
                    time.sleep(1)
                backoff = min(backoff * 2, 60)
        try:
            self.heartbeat("paused")
        except Exception:
            pass
        self.state(state="stopped")
        return {"ok": True, "stopped": True}


def worker_from_env():
    server, key = os.environ.get("GT_SERVER", ""), os.environ.get("GT_PROVIDER_KEY", "")
    device, name, home = os.environ.get("GT_DEVICE_ID", ""), os.environ.get("GT_DEVICE_NAME", ""), os.environ.get("GT_HOME", "")
    if not server.startswith("https://") and not server.startswith("http://127.0.0.1"):
        raise Friendly("The GreenTokens server address is invalid. Contact the operator for an updated installer.")
    if not key or not re.fullmatch(r"[A-Za-z0-9_-]{8,64}", device) or not home:
        raise Friendly("This computer is not signed in. Sign in before connecting.")
    return Worker(server, key, device, (name or socket.gethostname())[:255], home)


# ---------------------------------------------------------------------------------------------
# One-click setup: training packages for this computer, chosen automatically. The app runs this
# once after the owner agrees; the bundled uv installs into the app's private runtime only.
# ---------------------------------------------------------------------------------------------
TRAIN_PACKAGES = ["transformers==4.57.6", "datasets==4.8.5", "safetensors==0.8.0"]
# Newest PyTorch build each NVIDIA driver can run. RTX 50-series GPUs need CUDA 12.8 or newer.
TORCH_BUILDS = [((13, 2), "2.15.0", "cu132"), ((13, 0), "2.14.1", "cu130"), ((12, 8), "2.11.0", "cu128")]
CPU_TORCH = "2.15.0"


def pick_torch(has_nvidia_gpu, cuda_driver):
    """Return (torch version, cuda tag or None, note for the owner)."""
    if not has_nvidia_gpu:
        return CPU_TORCH, None, "No NVIDIA GPU found: jobs will use the processor."
    try:
        driver = tuple(int(x) for x in (cuda_driver or "").split(".")[:2])
    except ValueError:
        driver = ()
    for minimum, version, tag in TORCH_BUILDS:
        if driver >= minimum:
            return version, tag, f"GPU support installed (PyTorch {version}, CUDA {tag[2:4]}.{tag[4:]})."
    return CPU_TORCH, None, ("Your NVIDIA driver is too old for GPU jobs (needs CUDA 12.8 or newer). "
                             "Update it from nvidia.com, then choose Repair setup. Until then jobs use the processor.")


def setup():
    uv = os.environ.get("GT_UV", "")
    if not uv or not Path(uv).is_file():
        raise Friendly("The setup tool is missing. Please reinstall GreenTokens Provider.")
    caps = {"gpus": [], "cuda_driver": None}
    smi = shutil.which("nvidia-smi")
    if smi:
        try:
            names = run([smi, "--query-gpu=name", "--format=csv,noheader"], timeout=20).stdout.strip().splitlines()
            caps["gpus"] = [n.strip() for n in names if n.strip()]
            match = re.search(r"CUDA Version:\s*([0-9.]+)", run([smi], timeout=20).stdout)
            caps["cuda_driver"] = match.group(1) if match else None
        except Exception:
            pass
    version, tag, note = pick_torch(bool(caps["gpus"]), caps["cuda_driver"])
    marker = Path(sys.prefix) / f"greentokens-train-{version}-{tag or 'cpu'}"
    if not marker.is_file():
        base = [uv, "pip", "install", "--quiet", "--python", sys.executable]
        torch_cmd = base + [f"torch=={version}"]
        if tag:
            torch_cmd += ["--index-url", f"https://download.pytorch.org/whl/{tag}", "--extra-index-url", "https://pypi.org/simple"]
        for command, what in ((torch_cmd, "PyTorch"), (base + TRAIN_PACKAGES, "training packages")):
            result = run(command, timeout=3600)
            if result.returncode != 0:
                detail = (result.stderr or result.stdout).strip().splitlines()[-1:] or [""]
                raise Friendly(f"Installing {what} failed. Check the internet connection and choose Repair setup. ({detail[0][:160]})")
        marker.write_text("ok")
    probe = run([sys.executable, "-c", "import json,torch;print(json.dumps([torch.__version__, torch.cuda.is_available()]))"], timeout=300)
    try:
        torch_version, cuda_ok = json.loads(probe.stdout.strip().splitlines()[-1])
    except Exception:
        raise Friendly("PyTorch was installed but doesn't start. Choose Repair setup.")
    if tag and not cuda_ok:
        note = "PyTorch is installed, but it can't use the GPU yet. Restart the computer, then choose Repair setup."
    return {"ok": True, "torch": torch_version, "gpu": caps["gpus"][0] if caps["gpus"] else None,
            "gpu_ready": bool(cuda_ok), "note": note}


def main(argv=None):
    parser = argparse.ArgumentParser()
    parser.add_argument("action", choices=["check", "firewall", "host", "join", "stop", "status", "capabilities", "worker", "setup"])
    parser.add_argument("--code")
    parser.add_argument("--cpus", type=int, default=1)
    args = parser.parse_args(argv)
    if not 1 <= args.cpus <= 256:
        raise Friendly("Invalid processor limit.")
    if args.action == "setup":
        return setup()
    if args.action == "capabilities":
        return {"ok": True, **capabilities()}
    if args.action == "worker":
        return worker_from_env().loop()
    if args.action == "check":
        return check()
    if args.action == "firewall":
        return allow_firewall()
    if args.action == "stop":
        return stop()
    if args.action == "status":
        return status(args.code)
    return start("host" if args.action == "host" else "member", args.code, args.cpus)


if __name__ == "__main__":
    try:
        reply = main()
    except Friendly as exc:
        reply = {"ok": False, "error": str(exc)}
    except subprocess.TimeoutExpired:
        reply = {"ok": False, "error": "That took too long. Please try again."}
    except Exception:  # Never show a traceback to the user.
        reply = {"ok": False, "error": "Something went wrong on this computer. Please try again."}
    print(json.dumps(reply), flush=True)
