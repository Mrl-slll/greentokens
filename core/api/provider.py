"""Provider API: independent provider computers connect OUTWARD to these endpoints (no Ray on providers).

Flow: heartbeat (register + capabilities) -> ask for work (long poll) -> download the workload package ->
renew the lease while running -> upload artifacts -> complete. A provider that stops renewing its lease is
treated as lost by the dispatcher and the job is queued again. Only users with role "provider" can call these.
"""
import hashlib
import io
import time
import zipfile
from datetime import timedelta
from pathlib import Path
from typing import Literal

from fastapi import Depends, HTTPException, Request, Response
from pydantic import Field
from sqlalchemy import func, select

from core.api.schemas import PROVIDER_TEMPLATES, StrictModel
from core.artifacts.storage import LARGE_KIND_LIMITS, ArtifactError
from core.database.models import Artifact, Attempt, Job, Worker, now, uid
from core.jobs.dispatcher import finish_attempt

LEASE = timedelta(seconds=90)
PACKAGE_ROOT = Path(__file__).resolve().parents[1] / "workloads" / "packages"
WORKLOAD_PACKAGES = {"text_finetune_v1": "text_finetune", "distilbert_four_pc_test_v1": "distilbert_four_pc"}
UPLOAD_KINDS = {"output", "model", "log"}
DEVICE = Field(pattern=r"^[A-Za-z0-9-]{8,64}$")


class Gpu(StrictModel):
    name: str = Field(max_length=255)
    vram_gb: float | None = None


class Capabilities(StrictModel):
    os: str = Field(default="", max_length=64)
    arch: str = Field(default="", max_length=32)
    cpus: int = Field(default=0, ge=0, le=4096)
    ram_gb: float = Field(default=0, ge=0)
    gpus: list[Gpu] = Field(default_factory=list, max_length=16)
    cuda_driver: str | None = Field(default=None, max_length=32)
    torch: str | None = Field(default=None, max_length=64)
    torch_cuda: bool = False
    python: str | None = Field(default=None, max_length=32)
    agent: str | None = Field(default=None, max_length=32)


class Heartbeat(StrictModel):
    device_id: str = DEVICE
    name: str = Field(min_length=1, max_length=255)
    status: Literal["online", "paused"]
    capabilities: Capabilities


class WorkRequest(StrictModel):
    device_id: str = DEVICE
    wait_seconds: int = Field(default=20, ge=0, le=25)


class LeaseRenewal(StrictModel):
    device_id: str = DEVICE
    progress: dict | None = None


class Completion(StrictModel):
    device_id: str = DEVICE
    status: Literal["SUCCEEDED", "FAILED", "CANCELLED"]
    error_code: str | None = Field(default=None, max_length=64, pattern=r"^[A-Z0-9_]+$")


_package_cache = {}


def build_package(name):
    """Deterministic zip of an approved workload package folder, plus its sha256."""
    if name not in _package_cache:
        folder = PACKAGE_ROOT / name
        buffer = io.BytesIO()
        with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as zf:
            for path in sorted(p for p in folder.rglob("*") if p.is_file() and "__pycache__" not in p.parts):
                info = zipfile.ZipInfo(path.relative_to(folder).as_posix(), date_time=(2020, 1, 1, 0, 0, 0))
                zf.writestr(info, path.read_bytes())
        data = buffer.getvalue()
        _package_cache[name] = (data, hashlib.sha256(data).hexdigest())
    return _package_cache[name]


def add_provider_routes(app, sessions, storage, identity):
    def provider_user(user=Depends(identity)):
        if user.role != "provider":
            raise HTTPException(403, "A provider key is required")
        return user

    def own_device(db, user, device_id):
        if getattr(user, "auth_device_id", device_id) != device_id:
            raise HTTPException(403, "Sign in on this device first")
        worker = db.get(Worker, device_id)
        if worker is None or worker.kind != "provider" or worker.owner_user_id != user.id:
            raise HTTPException(404, "Unknown device; send a heartbeat first")
        return worker

    def own_attempt(db, user, attempt_id, device_id):
        attempt = db.get(Attempt, attempt_id)
        if attempt is None or attempt.worker_id != device_id:
            raise HTTPException(404, "Not found")
        own_device(db, user, device_id)
        return attempt

    def payload(job, attempt):
        name = WORKLOAD_PACKAGES[job.template_id]
        _, digest = build_package(name)
        return {"attempt_id": attempt.id, "job_id": job.id, "template_id": job.template_id,
                "workload": {"name": name, "sha256": digest, "url": f"/v1/provider/packages/{name}"},
                "parameters": job.parameters, "timeout_seconds": job.requirements["max_runtime_seconds"],
                "lease_seconds": int(LEASE.total_seconds())}

    @app.post("/v1/provider/heartbeat")
    def heartbeat(body: Heartbeat, user=Depends(provider_user)):
        if getattr(user, "auth_device_id", body.device_id) != body.device_id:
            raise HTTPException(403, "Sign in on this device first")
        caps = body.capabilities
        with sessions.begin() as db:
            worker = db.get(Worker, body.device_id)
            if worker is None:
                worker = Worker(id=body.device_id, hostname=body.name, cpu_cores=0, ram_gb=0, kind="provider",
                                owner_user_id=user.id, trusted=True, workload_class="trusted_cpu")
                db.add(worker)
            elif worker.kind != "provider" or worker.owner_user_id != user.id:
                raise HTTPException(403, "This device belongs to another account")
            worker.hostname, worker.paused, worker.last_seen_at = body.name, body.status != "online", now()
            worker.cpu_cores, worker.ram_gb = caps.cpus, caps.ram_gb
            worker.gpu_count = len(caps.gpus) if caps.torch_cuda else 0  # a GPU only counts if training can use it
            worker.gpu_name = caps.gpus[0].name if caps.gpus else None
            worker.capabilities = caps.model_dump()
        return {"ok": True, "server_time": now().isoformat()}

    def try_assign(user, device_id):
        with sessions.begin() as db:
            worker = own_device(db, user, device_id)
            worker.last_seen_at, worker.paused = now(), False
            active = db.scalar(select(Attempt).where(Attempt.worker_id == device_id, Attempt.status == "RUNNING"))
            if active is not None:  # reconnected while working: hand the same job back
                return payload(db.get(Job, active.job_id), active)
            jobs = db.scalars(select(Job).where(Job.status == "QUEUED", Job.template_id.in_(PROVIDER_TEMPLATES))
                              .order_by(Job.created_at).with_for_update(skip_locked=True).limit(20)).all()
            for job in jobs:
                if job.parameters.get("target_device_id") and job.parameters["target_device_id"] != device_id:
                    continue
                if job.cancel_requested or (job.parameters.get("require_gpu") and worker.gpu_count < 1):
                    continue
                count = db.scalar(select(func.count()).select_from(Attempt).where(Attempt.job_id == job.id)) or 0
                attempt_id = uid()
                attempt = Attempt(id=attempt_id, job_id=job.id, attempt_number=count + 1,
                                  ray_submission_id=f"prov-{attempt_id}", status="RUNNING", started_at=now(),
                                  worker_id=worker.id, worker_hostname=worker.hostname, lease_expires_at=now() + LEASE)
                db.add(attempt)
                job.status, job.error_code = "RUNNING", None
                db.flush()
                return payload(job, attempt)
        return None

    @app.post("/v1/provider/work")
    def work(body: WorkRequest, user=Depends(provider_user)):
        deadline = time.monotonic() + body.wait_seconds
        while True:
            assignment = try_assign(user, body.device_id)
            if assignment is not None:
                return assignment
            if time.monotonic() >= deadline:
                return Response(status_code=204)
            time.sleep(2)

    @app.get("/v1/provider/packages/{name}")
    def package(name: str, user=Depends(provider_user)):
        if name not in WORKLOAD_PACKAGES.values():
            raise HTTPException(404, "Unknown workload package")
        data, digest = build_package(name)
        return Response(data, media_type="application/zip", headers={"X-GT-SHA256": digest})

    @app.post("/v1/provider/work/{attempt_id}/lease")
    def renew(attempt_id: str, body: LeaseRenewal, user=Depends(provider_user)):
        with sessions.begin() as db:
            attempt = own_attempt(db, user, attempt_id, body.device_id)
            job = db.get(Job, attempt.job_id)
            if attempt.status != "RUNNING":
                return {"continue": False}
            attempt.lease_expires_at = now() + LEASE
            db.get(Worker, body.device_id).last_seen_at = now()
            return {"continue": not job.cancel_requested}

    @app.put("/v1/provider/work/{attempt_id}/artifacts/{kind}")
    async def upload_artifact(attempt_id: str, kind: str, request: Request, device_id: str, user=Depends(provider_user)):
        if kind not in UPLOAD_KINDS:
            raise HTTPException(404, "Unknown artifact kind")
        limit = LARGE_KIND_LIMITS.get(kind, storage.settings.max_bytes)
        declared = int(request.headers.get("content-length") or 0)
        if declared > limit:
            raise HTTPException(413, "Artifact exceeds size limit")
        data = bytearray()
        async for chunk in request.stream():
            data.extend(chunk)
            if len(data) > limit:
                raise HTTPException(413, "Artifact exceeds size limit")
        with sessions.begin() as db:
            attempt = own_attempt(db, user, attempt_id, device_id)
            if attempt.status != "RUNNING":
                raise HTTPException(409, "Attempt is no longer running")
            job = db.get(Job, attempt.job_id)
            try:
                artifact = storage.put(job.organization_id, kind, bytes(data), job.id, attempt.id)
            except ArtifactError as exc:
                raise HTTPException(413, str(exc)) from None
            old = db.scalar(select(Artifact).where(Artifact.attempt_id == attempt.id, Artifact.kind == kind))
            if old is not None:
                db.delete(old)
                db.flush()
            db.add(artifact)
        return {"artifact_id": artifact.id, "sha256": artifact.sha256, "size_bytes": artifact.size_bytes}

    @app.post("/v1/provider/work/{attempt_id}/complete")
    def complete(attempt_id: str, body: Completion, user=Depends(provider_user)):
        with sessions.begin() as db:
            attempt = own_attempt(db, user, attempt_id, body.device_id)
            job = db.scalar(select(Job).where(Job.id == attempt.job_id).with_for_update())
            if attempt.status != "RUNNING":
                return {"job_id": job.id, "status": job.status}
            status, error = body.status, body.error_code
            if status == "SUCCEEDED" and not db.scalar(select(Artifact).where(
                    Artifact.attempt_id == attempt.id, Artifact.kind == "output")):
                status, error = "FAILED", "OUTPUT_MISSING"
            if job.cancel_requested and status != "SUCCEEDED":
                status, error = "CANCELLED", None
            attempt.lease_expires_at = None
            finish_attempt(db, job, attempt, status, error if status == "FAILED" else None)
            return {"job_id": job.id, "status": job.status}
