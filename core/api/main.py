import hashlib
import json
from datetime import timedelta

from fastapi import Depends, FastAPI, HTTPException, Request, Response
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from pydantic import ValidationError
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError

from core.api.schemas import BERT_CPUS_PER_WORKER, Numbers, TrainingData, Submission, input_model
from core.artifacts.storage import ArtifactError, Storage
from core.config import Settings
from core.database.models import Artifact, Attempt, Job, Organization, Usage, User, Worker, now
from core.database.session import database

TERMINAL = {"SUCCEEDED", "FAILED", "CANCELLED"}


PROXY_HEADERS = ("cf-connecting-ip", "cf-ray", "x-forwarded-for", "forwarded")


def proxied(request):
    """True when the request came through a tunnel/proxy (which reaches us from loopback)."""
    return any(h in request.headers for h in PROXY_HEADERS)


def create_app(settings=None, sessions=None, storage=None):
    settings = settings or Settings.from_env()
    if sessions is None:
        _, sessions = database(settings)
    storage = storage or Storage(settings)
    app = FastAPI(title="GreenTokens local development API", version="0.2.0")

    @app.middleware("http")
    async def local_only(request, call_next):
        if not request.client or request.client.host not in {"127.0.0.1", "::1", "testclient"}:
            return JSONResponse({"detail": "Local development access only"}, status_code=403)
        if proxied(request) and not (request.url.path == "/health" or request.url.path.startswith("/v1/")):
            return JSONResponse({"detail": "Not found"}, status_code=404)
        return await call_next(request)

    @app.exception_handler(RequestValidationError)
    async def invalid_request(request, exc):
        # Avoid reflecting input or accidental secrets in validation responses/logs.
        return JSONResponse({"detail": "Invalid approved job request"}, status_code=422)

    @app.exception_handler(ArtifactError)
    async def artifact_error(request, exc):
        code = str(exc)
        status = 410 if code == "ARTIFACT_EXPIRED" else 502
        return JSONResponse({"detail": code}, status_code=status)

    def identity(request: Request):
        auth = request.headers.get("Authorization", "")
        with sessions() as db:
            if auth.startswith("Bearer "):
                digest = hashlib.sha256(auth[7:].encode()).hexdigest()
                user = db.get(User, settings.api_keys.get(digest, ""))
                if user is None:
                    raise HTTPException(401, "Invalid API key")
                return user
            if proxied(request):
                # Tunneled requests arrive from loopback; never let them use the dev stub.
                raise HTTPException(401, "API key required")
            # Deliberate development stub, NOT authentication. Configuration blocks production.
            name = request.headers.get("X-Dev-User", "")
            user = db.get(User, name)
            if user is None:
                raise HTTPException(401, "Use a configured local X-Dev-User identity")
            return user

    def owned(db, model, identifier, user):
        item = db.get(model, identifier)
        if item is None or item.organization_id != user.organization_id:
            raise HTTPException(404, "Not found")
        return item

    @app.get("/health")
    def health():
        with sessions() as db:
            db.execute(select(1))
        return {"status": "ok", "authentication": "development-stub"}

    @app.post("/v1/artifacts", status_code=201)
    async def upload(request: Request, user=Depends(identity)):
        data = bytearray()
        async for chunk in request.stream():
            data.extend(chunk)
            if len(data) > settings.max_bytes:
                raise HTTPException(413, "Input exceeds size limit")
        try:
            try:
                values = Numbers.model_validate_json(bytes(data))
            except ValidationError:
                values = TrainingData.model_validate_json(bytes(data))
        except ValidationError:
            raise HTTPException(422, "Expected bounded sum values or paired training x/y arrays") from None
        payload = values.model_dump_json().encode()
        artifact = storage.put(user.organization_id, "input", payload)
        with sessions.begin() as db:
            db.add(artifact)
        return {"artifact_id": artifact.id, "sha256": artifact.sha256,
                "size_bytes": artifact.size_bytes, "expires_at": artifact.expires_at}

    @app.get("/v1/artifacts/{artifact_id}")
    def download(artifact_id: str, user=Depends(identity)):
        with sessions() as db:
            artifact = owned(db, Artifact, artifact_id, user)
            data = storage.read(artifact)
        return Response(data, media_type={"log": "text/plain", "model": "application/octet-stream"}.get(artifact.kind, "application/json"))

    @app.post("/v1/jobs", status_code=202)
    def submit(body: Submission, user=Depends(identity)):
        digest = hashlib.sha256(json.dumps(body.model_dump(), sort_keys=True).encode()).hexdigest()
        with sessions.begin() as db:
            # Serialize the organization's submission/quota check across API processes.
            db.execute(select(Organization).where(Organization.id == user.organization_id).with_for_update()).scalar_one()
            old = db.scalar(select(Job).where(Job.organization_id == user.organization_id,
                                             Job.idempotency_key == body.idempotency_key))
            if old:
                if old.request_hash != digest:
                    raise HTTPException(409, "Idempotency key already used with different content")
                return {"job_id": old.id, "status": old.status}
            if body.input_artifact_id:
                artifact = owned(db, Artifact, body.input_artifact_id, user)
                if artifact.kind != "input":
                    raise HTTPException(422, "Expected an input artifact")
                try:
                    input_model(body.template_id).model_validate_json(storage.read(artifact))
                except ValidationError:
                    raise HTTPException(422, "Input does not match selected pipeline") from None
            workers = db.scalars(select(Worker).where(Worker.trusted.is_(True),
                Worker.paused.is_(False), Worker.last_seen_at > now() - timedelta(seconds=60),
                Worker.workload_class == body.requirements.execution_class)).all()
            if body.template_id == "bert_tiny_ddp_v1":
                # One worker per computer: each needs enough CPUs, and enough computers must be online.
                needed = body.parameters.workers
                ready = [w for w in workers if w.cpu_cores >= BERT_CPUS_PER_WORKER]
                if len(ready) < needed:
                    raise HTTPException(422, f"Not enough computers online: {needed} needed, {len(ready)} available")
            elif not any(w.cpu_cores >= body.requirements.cpu_cores and
                         w.ram_gb >= body.requirements.ram_gb for w in workers):
                raise HTTPException(422, "No eligible trusted worker for requested resources")
            active = db.scalar(select(func.count()).select_from(Job).where(
                Job.organization_id == user.organization_id, Job.status.not_in(TERMINAL)))
            if active >= 20:
                raise HTTPException(429, "Local organization queue limit reached")
            job = Job(organization_id=user.organization_id, template_id=body.template_id,
                      parameters=body.parameters.model_dump() if body.parameters else {},
                      input_artifact_id=body.input_artifact_id,
                      requirements=body.requirements.model_dump(), idempotency_key=body.idempotency_key,
                      request_hash=digest)
            db.add(job)
            db.flush()
            return {"job_id": job.id, "status": job.status}

    @app.get("/v1/jobs/{job_id}")
    def status(job_id: str, user=Depends(identity)):
        with sessions() as db:
            job = owned(db, Job, job_id, user)
            attempts = db.scalars(select(Attempt).where(Attempt.job_id == job.id).order_by(Attempt.attempt_number)).all()
            artifacts = db.scalars(select(Artifact).where(Artifact.job_id == job.id)).all()
            return {"job_id": job.id, "status": job.status, "template_id": job.template_id,
                    "requirements": job.requirements, "input_artifact_id": job.input_artifact_id,
                    "input_source": "artifact" if job.input_artifact_id else "inline",
                    "created_at": job.created_at, "updated_at": job.updated_at,
                    "cancel_requested": job.cancel_requested, "error_code": job.error_code,
                    "attempt_count": len(attempts),
                    "attempts": [{k: getattr(a, k) for k in ("id", "attempt_number", "status",
                        "ray_submission_id", "started_at", "finished_at", "worker_hostname",
                        "worker_pid", "exit_code", "error_code")} for a in attempts],
                    "artifacts": [{"artifact_id": a.id, "kind": a.kind, "sha256": a.sha256,
                                   "size_bytes": a.size_bytes, "expires_at": a.expires_at} for a in artifacts]}

    @app.get("/v1/jobs/{job_id}/result")
    def result(job_id: str, user=Depends(identity)):
        with sessions() as db:
            job = owned(db, Job, job_id, user)
            if job.status != "SUCCEEDED":
                raise HTTPException(409, "Job has no successful result")
            artifact = db.scalar(select(Artifact).where(Artifact.job_id == job.id, Artifact.kind == "output"))
            if not artifact:
                raise HTTPException(502, "Result metadata missing")
            return json.loads(storage.read(artifact))

    @app.post("/v1/jobs/{job_id}/cancel")
    def cancel(job_id: str, user=Depends(identity)):
        with sessions.begin() as db:
            job = db.scalar(select(Job).where(Job.id == job_id).with_for_update())
            if not job or job.organization_id != user.organization_id:
                raise HTTPException(404, "Not found")
            if job.status not in TERMINAL:
                job.cancel_requested = True
                if job.status == "QUEUED":
                    job.status = "CANCELLED"
            return {"job_id": job.id, "status": job.status, "cancel_requested": job.cancel_requested}

    @app.get("/v1/workers")
    def workers(user=Depends(identity)):
        if user.role != "admin":
            raise HTTPException(403, "Admin only")
        with sessions() as db:
            return [{"id": w.id, "cpu_cores": w.cpu_cores, "ram_gb": w.ram_gb,
                     "trusted": w.trusted, "paused": w.paused, "last_seen_at": w.last_seen_at}
                    for w in db.scalars(select(Worker))]

    @app.get("/v1/usage")
    def usage(user=Depends(identity)):
        with sessions() as db:
            rows = db.scalars(select(Usage).join(Attempt, Attempt.id == Usage.job_attempt_id)
                             .join(Job, Job.id == Attempt.job_id)
                             .where(Job.organization_id == user.organization_id)).all()
            return {"attempts": len(rows), "wall_seconds": sum(r.wall_seconds for r in rows),
                    "billable": False, "measurement": "attempt elapsed time; not billing-grade"}

    return app
