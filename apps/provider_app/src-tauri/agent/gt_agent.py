"""GreenTokens Provider agent: lead or join a private Ray group on the local network.

Called by the desktop app with fixed actions and validated arguments. Prints exactly one
JSON line and always exits 0; failures are {"ok": false, "error": "<friendly text>"}.

Security: the group is protected by Ray token authentication (the token is inside the join
code), only private LAN addresses are accepted, the dashboard stays on 127.0.0.1, and the
firewall rule covers a fixed port list on the Private network profile only.
"""
import argparse
import base64
import ipaddress
import json
import os
import re
import shutil
import socket
import subprocess
import sys
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


def main(argv=None):
    parser = argparse.ArgumentParser()
    parser.add_argument("action", choices=["check", "firewall", "host", "join", "stop", "status"])
    parser.add_argument("--code")
    parser.add_argument("--cpus", type=int, default=1)
    args = parser.parse_args(argv)
    if not 1 <= args.cpus <= 256:
        raise Friendly("Invalid processor limit.")
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
