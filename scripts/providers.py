"""Read-only: which provider computers are connected right now, and what they can do.

    python -m scripts.providers
Uses the local admin view of the backend on this computer (http://127.0.0.1:8000).
"""
import json
import urllib.request
from datetime import datetime, timezone


def main():
    request = urllib.request.Request("http://127.0.0.1:8000/v1/workers", headers={"X-Dev-User": "admin"})
    try:
        with urllib.request.urlopen(request, timeout=10) as response:
            workers = json.loads(response.read())
    except OSError:
        raise SystemExit("The backend isn't running on this computer. Start it with scripts\\start_server.ps1")
    providers = [w for w in workers if w.get("kind") == "provider"]
    if not providers:
        print("No provider computers have connected yet.")
        return
    now = datetime.now(timezone.utc).replace(tzinfo=None)
    print(f"{'computer':28} {'status':10} {'last seen':>10}  {'CPUs':>4} {'RAM GB':>6}  GPU")
    for w in sorted(providers, key=lambda w: w["last_seen_at"], reverse=True):
        seen = (now - datetime.fromisoformat(w["last_seen_at"].replace("Z", ""))).total_seconds()
        status = "offline" if seen > 60 else "paused" if w["paused"] else "online"
        gpu = w.get("gpu_name") or "-"
        if w.get("gpu_name") and not w.get("gpu_count"):
            gpu += " (not usable yet: driver/setup)"
        print(f"{w['hostname'][:28]:28} {status:10} {int(seen):>8}s  {w['cpu_cores']:>4} {w['ram_gb']:>6.1f}  {gpu}")


if __name__ == "__main__":
    main()
