"""Separate operator-only four-provider experiment; HTTPS relays bytes, never trains on the server."""
import hashlib
import json
import os
import re
import threading
import time
from datetime import timedelta
from pathlib import Path
from uuid import uuid4

from fastapi import Depends, HTTPException, Request, Response
from fastapi.responses import FileResponse
from sqlalchemy import select

from core.database.models import Attempt, Job, Worker, now

ROOT = Path(__file__).resolve().parents[2] / "experiments/four_pc_cpu/runs"
HOSTS = ("INFO-COL-D0047", "INFO-COL-D0048", "INFO-COL-D0049", "INFO-COL-D0064")
CHUNK = 8 * 1024 * 1024
LOCK = threading.RLock()


def write_json(path, value):
    temp = path.with_suffix(".tmp")
    temp.write_text(json.dumps(value, indent=2), encoding="utf-8")
    os.replace(temp, path)


def add_shared_test_routes(app, sessions, identity):
    def admin(user=Depends(identity)):
        if user.role != "admin":
            raise HTTPException(403, "Operator only")
        return user

    def folder(run_id):
        if not re.fullmatch(r"[a-f0-9]{32}", run_id):
            raise HTTPException(404)
        path = ROOT / run_id
        if not (path / "run.json").is_file():
            raise HTTPException(404)
        return path

    def member(run_id, user):
        path = folder(run_id)
        cfg = json.loads((path / "run.json").read_text())
        device = getattr(user, "auth_device_id", None)
        if user.role != "provider" or device not in cfg["devices"]:
            raise HTTPException(403, "Not a participant")
        rank = cfg["devices"].index(device)
        with sessions() as db:
            worker = db.get(Worker, device)
            job = db.get(Job, cfg["jobs"][rank])
            attempts = db.scalars(select(Attempt).where(Attempt.job_id == job.id)).all()
            if worker.owner_user_id != user.id or job.cancel_requested or job.status != "RUNNING":
                raise HTTPException(409, "Participant is no longer running")
            if len(attempts) != 1 or attempts[0].worker_id != device:
                raise HTTPException(409, "Restart the experiment after a participant failure")
        return path, cfg, rank

    @app.post("/v1/shared-test", status_code=201)
    def create(user=Depends(admin)):
        with LOCK, sessions.begin() as db:
            workers = db.scalars(select(Worker).where(Worker.kind == "provider", Worker.paused.is_(False),
                                 Worker.last_seen_at > now() - timedelta(seconds=60))).all()
            chosen = []
            for host in HOSTS:
                matches = [w for w in workers if w.hostname == host and w.ram_gb >= 12]
                if len(matches) != 1:
                    raise HTTPException(409, f"Need exactly one online provider named {host} with >=12 GB RAM")
                chosen.append(matches[0])
            busy = db.scalar(select(Job.id).where(Job.template_id == "distilbert_four_pc_test_v1",
                             Job.status.not_in(["SUCCEEDED", "FAILED", "CANCELLED"])))
            if busy:
                raise HTTPException(409, "A shared test is already active")
            run_id = uuid4().hex
            cfg = {"run_id": run_id, "hosts": list(HOSTS), "devices": [w.id for w in chosen],
                   "created_at": now().isoformat(), "duration_seconds": 1800,
                   "model": "distilbert/distilbert-base-uncased", "dataset": "stanfordnlp/imdb",
                   "examples": 12000, "batch_size": 16, "max_length": 256, "threads": 0, "sync_seconds": 240, "stop_margin_seconds": 60,
                   "learning_rate": 2e-5, "seed": 42, "jobs": []}
            for rank, w in enumerate(chosen):
                p = {k: v for k, v in cfg.items() if k not in ("devices", "hosts", "jobs", "created_at")}
                p.update(rank=rank, workers=4, target_device_id=w.id, require_gpu=False)
                job = Job(organization_id=user.organization_id, template_id="distilbert_four_pc_test_v1",
                          parameters=p, requirements={"cpu_cores": 8, "ram_gb": 12.0, "gpus": 0,
                          "execution_class": "trusted_cpu", "max_runtime_seconds": 10800},
                          idempotency_key=f"four-pc-{run_id}-{rank}",
                          request_hash=hashlib.sha256(json.dumps(p, sort_keys=True).encode()).hexdigest())
                db.add(job)
                db.flush()
                cfg["jobs"].append(job.id)
            path = ROOT / run_id
            path.mkdir(parents=True)
            write_json(path / "run.json", cfg)
            write_json(path / "state.json", {"started": None, "barriers": {}})
        return cfg

    @app.get("/v1/shared-test/{run_id}")
    def status(run_id: str, user=Depends(admin)):
        path = folder(run_id)
        with LOCK:
            cfg = json.loads((path / "run.json").read_text())
            state = json.loads((path / "state.json").read_text())
        with sessions() as db:
            jobs = [{"job_id": j, "status": db.get(Job, j).status, "error": db.get(Job, j).error_code}
                    for j in cfg["jobs"]]
        return {"config": cfg, "state": state, "jobs": jobs}

    def blob_name(name, owner, chunk=None):
        if not re.fullmatch(r"init|final|grad-[0-9]{1,4}|mean-[0-9]{1,4}", name) or not 0 <= owner < 4:
            raise HTTPException(422)
        if chunk is not None and not 0 <= chunk < 64:
            raise HTTPException(422)
        return f"{name}-{owner}" + (f"-{chunk}.bin" if chunk is not None else ".json")

    def can_write(name, owner, rank):
        if owner != rank or (not name.startswith("grad-") and rank != 0):
            raise HTTPException(403)

    @app.put("/v1/shared-test/{run_id}/blob/{name}/{owner}/{chunk}")
    async def put_chunk(run_id: str, name: str, owner: int, chunk: int, request: Request, user=Depends(identity)):
        path, cfg, rank = member(run_id, user)
        target = path / blob_name(name, owner, chunk)
        can_write(name, owner, rank)
        data = bytearray()
        async for part in request.stream():
            data.extend(part)
            if len(data) > CHUNK:
                raise HTTPException(413)
        digest = hashlib.sha256(data).hexdigest()
        if request.headers.get("x-content-sha256") != digest:
            raise HTTPException(422, "Checksum mismatch")
        with LOCK:
            if target.exists() and hashlib.sha256(target.read_bytes()).hexdigest() != digest:
                raise HTTPException(409, "Immutable chunk differs")
            temp = target.with_suffix(".tmp")
            temp.write_bytes(data)
            os.replace(temp, target)
        return {"sha256": digest}

    @app.get("/v1/shared-test/{run_id}/blob/{name}/{owner}/{chunk}")
    def get_chunk(run_id: str, name: str, owner: int, chunk: int, user=Depends(identity)):
        path, _, _ = member(run_id, user)
        target = path / blob_name(name, owner, chunk)
        if not target.is_file():
            raise HTTPException(404)
        return FileResponse(target, media_type="application/octet-stream")

    @app.put("/v1/shared-test/{run_id}/manifest/{name}/{owner}")
    async def put_manifest(run_id: str, name: str, owner: int, request: Request, user=Depends(identity)):
        path, _, rank = member(run_id, user)
        target = path / blob_name(name, owner)
        can_write(name, owner, rank)
        raw = await request.body()
        if len(raw) > 8192:
            raise HTTPException(413)
        manifest = json.loads(raw)
        hashes = manifest.get("hashes", [])
        if not 1 <= len(hashes) <= 64 or any(not re.fullmatch("[a-f0-9]{64}", h) for h in hashes):
            raise HTTPException(422)
        full = hashlib.sha256()
        size = 0
        for i, expected in enumerate(hashes):
            part = path / blob_name(name, owner, i)
            if not part.exists():
                raise HTTPException(409, "Incomplete upload")
            data = part.read_bytes()
            if hashlib.sha256(data).hexdigest() != expected:
                raise HTTPException(409, "Checksum mismatch")
            full.update(data)
            size += len(data)
        if full.hexdigest() != manifest.get("sha256") or size != manifest.get("size"):
            raise HTTPException(422, "Invalid full checksum")
        with LOCK:
            write_json(target, manifest)
        return {"ok": True}

    @app.get("/v1/shared-test/{run_id}/manifest/{name}/{owner}")
    def get_manifest(run_id: str, name: str, owner: int, user=Depends(identity)):
        path, _, _ = member(run_id, user)
        target = path / blob_name(name, owner)
        if not target.exists():
            return Response(status_code=202)
        return json.loads(target.read_text())

    @app.post("/v1/shared-test/{run_id}/barrier/{step}")
    async def barrier(run_id: str, step: int, request: Request, user=Depends(identity)):
        path, cfg, rank = member(run_id, user)
        if not 0 <= step <= 1000:
            raise HTTPException(422)
        raw = await request.body()
        if len(raw) > 8192:
            raise HTTPException(413)
        report = json.loads(raw)
        with LOCK:
            state = json.loads((path / "state.json").read_text())
            slot = state["barriers"].setdefault(str(step), {"reports": {}})
            slot["reports"].setdefault(str(rank), report)
            if len(slot["reports"]) == 4 and "decision" not in slot:
                hashes = {r.get("weights_sha256") for r in slot["reports"].values()}
                if len(hashes) != 1 or None in hashes:
                    raise HTTPException(409, "Model replicas differ")
                if step == 0:
                    fingerprints = {r.get("dataset_fingerprint") for r in slot["reports"].values()}
                    if len(fingerprints) != 1:
                        raise HTTPException(409, "Dataset versions differ")
                    state["started"] = time.time()
                elif str(step - 1) not in state["barriers"] or "decision" not in state["barriers"][str(step - 1)]:
                    raise HTTPException(409, "Missing prior synchronization")
                elapsed = time.time() - state["started"]
                # Stop when a sync lands within stop_margin of the limit: an extra round would be
                # a few seconds of training paying for a full sync.
                limit = cfg["duration_seconds"] - cfg.get("stop_margin_seconds", 0)
                slot["decision"] = {"stop": step > 0 and elapsed >= limit,
                                    "elapsed_seconds": elapsed, "step": step}
                # All replicas consumed the old data; retain the newest two rounds only.
                if step > 2:
                    for prefix in (f"grad-{step - 3}-", f"mean-{step - 3}-"):
                        for old in path.glob(prefix + "*"):
                            if old.is_file():
                                old.unlink()
            write_json(path / "state.json", state)
            if "decision" not in slot:
                return Response(status_code=202)
            return slot["decision"]
