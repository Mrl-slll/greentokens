"""Local development launcher. Secrets stay in memory/container configuration."""
import argparse
import json
import os
from pathlib import Path
import secrets
import socket
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))


def container_env(name):
    result = subprocess.run(["docker", "inspect", name], capture_output=True, text=True)
    if result.returncode:
        return {}
    info = json.loads(result.stdout)[0]
    if info["Config"].get("Labels", {}).get("com.docker.compose.project") != "greentokens-dev":
        raise RuntimeError("Container name belongs to a different project")
    return dict(value.split("=", 1) for value in info["Config"]["Env"] if "=" in value)


def configure():
    mysql = container_env("greentokens-dev-mysql")
    s3 = container_env("greentokens-dev-storage")
    os.environ.update({
        "GT_MODE": "development",
        "GT_MYSQL_PASSWORD": mysql.get("MYSQL_PASSWORD") or secrets.token_hex(24),
        "GT_MYSQL_ROOT_PASSWORD": mysql.get("MYSQL_ROOT_PASSWORD") or secrets.token_hex(24),
        "GT_S3_ACCESS_KEY": s3.get("AWS_ACCESS_KEY_ID") or secrets.token_hex(12),
        "GT_S3_SECRET_KEY": s3.get("AWS_SECRET_ACCESS_KEY") or secrets.token_hex(24),
        "GT_S3_ENDPOINT": "http://127.0.0.1:8333",
        "GT_RAY_ENDPOINT": "http://127.0.0.1:8265",
        "RAY_USAGE_STATS_ENABLED": "0", "RAY_ENABLE_WINDOWS_OR_OSX_CLUSTER": "0",
        "PYTHONUNBUFFERED": "1",
    })
    os.environ.pop("RAY_ADDRESS", None)
    os.environ["GT_DATABASE_URL"] = (
        "mysql+pymysql://greentokens:" + os.environ["GT_MYSQL_PASSWORD"] +
        "@127.0.0.1:3307/greentokens?charset=utf8mb4")


def services():
    print("Starting dedicated MySQL and SeaweedFS containers...", flush=True)
    result = subprocess.run(["docker", "compose", "-f", str(ROOT / "infrastructure/compose.yaml"),
                             "up", "-d"], capture_output=True, text=True)
    if result.returncode:
        # Compose errors can contain interpolated configuration: never echo them.
        raise RuntimeError("Compose startup failed; inspect container/image status without printing environment")
    from core.config import Settings
    from core.database.session import database
    from core.artifacts.storage import Storage
    from sqlalchemy import text
    settings = Settings.from_env()
    engine, sessions = database(settings)
    storage = Storage(settings)
    deadline = time.monotonic() + 180
    while True:
        try:
            with engine.connect() as conn:
                conn.execute(text("SELECT 1"))
            storage.ensure_bucket()
            break
        except Exception:
            if time.monotonic() > deadline:
                raise RuntimeError("Local database/object storage readiness timed out") from None
            time.sleep(2)
    print("MySQL and S3 are ready.", flush=True)
    return settings, engine, sessions, storage


def migrate(autogenerate=False):
    from alembic.config import Config
    from alembic import command
    config = Config(str(ROOT / "alembic.ini"))
    if autogenerate:
        (ROOT / "core/database/migrations/versions").mkdir(exist_ok=True)
        command.revision(config, message="initial durable job and artifact schema", autogenerate=True,
                         rev_id="0001")
    command.upgrade(config, "head")


def seed(sessions):
    from core.database.models import Organization, User
    with sessions.begin() as db:
        for org_id in ("org-a", "org-b"):
            if not db.get(Organization, org_id):
                db.add(Organization(id=org_id, name=f"Development {org_id}"))
        db.flush()
        for name, org, role in (("alice", "org-a", "customer"), ("bob", "org-b", "customer"),
                                ("admin", "org-a", "admin")):
            if not db.get(User, name):
                db.add(User(id=name, organization_id=org, role=role))


def heartbeat(sessions, ray):
    from core.database.models import Worker, now
    resources = ray.cluster_resources()
    node_id = ray.get_runtime_context().get_node_id()
    with sessions.begin() as db:
        worker = db.get(Worker, node_id)
        if worker is None:
            worker = Worker(id=node_id, hostname=socket.gethostname(), cpu_cores=0, ram_gb=0)
            db.add(worker)
        worker.cpu_cores = int(resources.get("CPU", 0))
        worker.ram_gb = resources.get("memory", 0) / 1024**3
        worker.last_seen_at = now()


def start_api():
    return subprocess.Popen([sys.executable, "-m", "uvicorn", "core.api.main:create_app", "--factory",
                             "--host", "127.0.0.1", "--port", "8000", "--no-access-log",
                             "--no-proxy-headers"], cwd=ROOT)


def stop(child):
    if child is not None and child.poll() is None:
        child.terminate()
        try:
            child.wait(timeout=10)
        except subprocess.TimeoutExpired:
            child.kill()
            child.wait(timeout=10)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--prepare", action="store_true")
    parser.add_argument("--generate-migration", action="store_true")
    parser.add_argument("--verify", action="store_true")
    args = parser.parse_args()
    os.chdir(ROOT)
    configure()
    settings, engine, sessions, storage = services()
    migrate(args.generate_migration)
    seed(sessions)
    if args.prepare:
        print("Schema migrated and development identities ready.", flush=True)
        engine.dispose()
        return
    import ray
    api = dispatcher = None
    try:
        for port in (8000, 8265):
            with socket.socket() as probe:
                if probe.connect_ex(("127.0.0.1", port)) == 0:
                    raise RuntimeError(f"Port {port} is in use; stop the previous local stack first")
        print("Starting private local Ray Jobs service...", flush=True)
        try:
            ray.init(address="local", num_cpus=min(4, os.cpu_count() or 1), num_gpus=0,
                     include_dashboard=True, dashboard_host="127.0.0.1", dashboard_port=8265,
                     _node_ip_address="127.0.0.1", logging_level="ERROR")
        except ValueError as exc:
            message = str(exc)
            for name, value in os.environ.items():
                if value and any(word in name.upper() for word in ("PASSWORD", "SECRET", "TOKEN", "KEY", "URL")):
                    message = message.replace(value, "[redacted]")
            print(f"Ray configuration rejected: {message}", flush=True)
            raise
        heartbeat(sessions, ray)
        api = start_api()
        dispatcher = subprocess.Popen([sys.executable, "-m", "core.jobs.dispatcher"], cwd=ROOT)
        print("Local API: http://127.0.0.1:8000/docs (development identities only)", flush=True)
        if args.verify:
            from scripts.verify_pipeline import verify
            def restart_api():
                nonlocal api
                stop(api)
                api = start_api()
            def restart_dispatcher():
                nonlocal dispatcher
                stop(dispatcher)
                dispatcher = subprocess.Popen([sys.executable, "-m", "core.jobs.dispatcher"], cwd=ROOT)
            verify(settings, sessions, storage, restart_api, lambda: heartbeat(sessions, ray), restart_dispatcher)
        else:
            while True:
                if api.poll() is not None or dispatcher.poll() is not None:
                    raise RuntimeError("A local control-plane process exited")
                heartbeat(sessions, ray)
                time.sleep(5)
    finally:
        stop(dispatcher)
        stop(api)
        ray.shutdown()
        engine.dispose()


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("Local API, dispatcher, and Ray stopped. Data volumes retained.")
    except Exception as exc:
        print(f"Local stack failed: {type(exc).__name__}", file=sys.stderr)
        # Avoid secret-bearing tracebacks from database or infrastructure libraries.
        sys.exit(1)
