"""Single dispatcher and reconciler; no durable reliance on ObjectRefs."""
import time
from datetime import timedelta

from sqlalchemy import select, text

from core.api.schemas import BERT_CPUS_PER_WORKER, PROVIDER_TEMPLATES
from core.artifacts.storage import ArtifactError, Storage
from core.config import Settings
from core.database.models import Artifact, Attempt, Job, Usage, Worker, now, uid
from core.database.session import database

TERMINAL = {"SUCCEEDED", "FAILED", "CANCELLED"}
PROVIDER_MAX_ATTEMPTS = 3  # a job whose provider disappears is queued again, at most this many times


def finish_attempt(db, job, attempt, status, error=None):
    """Mark a job and its attempt finished (shared by the Ray path and the provider API)."""
    if job.status in TERMINAL:
        return
    job.status, job.error_code = status, error
    attempt.status, attempt.error_code = status, error
    attempt.finished_at = now()
    attempt.exit_code = 0 if status == "SUCCEEDED" else 1
    if not db.scalar(select(Usage).where(Usage.job_attempt_id == attempt.id)):
        elapsed = max(0, (attempt.finished_at - (attempt.started_at or attempt.created_at)).total_seconds())
        db.add(Usage(job_attempt_id=attempt.id, wall_seconds=elapsed, billable=False))


class Dispatcher:
    def __init__(self, sessions, ray_jobs, storage):
        self.sessions, self.ray, self.storage = sessions, ray_jobs, storage

    def claim(self):
        with self.sessions.begin() as db:
            # One in-flight job in this initial local runtime; resource admission remains simple.
            # Provider jobs are picked up by the providers themselves (core/api/provider.py), not dispatched here.
            ray_jobs = Job.template_id.not_in(PROVIDER_TEMPLATES)
            if db.scalar(select(Job.id).where(Job.status.in_(["DISPATCHING", "RUNNING"]), ray_jobs)):
                return
            job = db.scalar(select(Job).where(Job.status == "QUEUED", ray_jobs).order_by(Job.created_at)
                            .with_for_update(skip_locked=True).limit(1))
            if not job:
                return
            workers = db.scalars(select(Worker).where(Worker.trusted.is_(True), Worker.paused.is_(False),
                Worker.kind == "ray", Worker.last_seen_at > now() - timedelta(seconds=60))).all()
            if job.template_id == "bert_tiny_ddp_v1":
                ready = [w for w in workers if w.cpu_cores >= BERT_CPUS_PER_WORKER and
                         w.workload_class == job.requirements["execution_class"]]
                eligible = len(ready) >= job.parameters["workers"]
            else:
                eligible = any(w.cpu_cores >= job.requirements["cpu_cores"] and
                               w.ram_gb >= job.requirements["ram_gb"] and
                               w.workload_class == job.requirements["execution_class"] for w in workers)
            if not eligible:
                job.status, job.error_code = "FAILED", "NO_ELIGIBLE_WORKER"
                return
            attempt_id = uid()
            db.add(Attempt(id=attempt_id, job_id=job.id, ray_submission_id=f"gt-{attempt_id}"))
            job.status = "DISPATCHING"

    def finish(self, db, job, attempt, status, error=None):
        finish_attempt(db, job, attempt, status, error)

    def reconcile_provider(self, attempt_id):
        """A provider attempt whose lease lapsed: the provider is lost. Queue the job again (or fail it)."""
        with self.sessions.begin() as db:
            attempt = db.get(Attempt, attempt_id)
            job = db.scalar(select(Job).where(Job.id == attempt.job_id).with_for_update())
            if attempt.status != "RUNNING" or attempt.lease_expires_at is None or attempt.lease_expires_at > now():
                return
            if job.cancel_requested:
                finish_attempt(db, job, attempt, "CANCELLED")
                return
            if attempt.attempt_number >= PROVIDER_MAX_ATTEMPTS:
                finish_attempt(db, job, attempt, "FAILED", "PROVIDER_LOST")
                return
            attempt.status, attempt.error_code, attempt.finished_at, attempt.exit_code = "FAILED", "PROVIDER_LOST", now(), 1
            job.status, job.error_code = "QUEUED", None  # another provider can take it

    def reconcile(self, attempt_id):
        with self.sessions() as db:
            attempt = db.get(Attempt, attempt_id)
            if attempt.ray_submission_id.startswith("prov-"):
                provider_attempt = True
            else:
                provider_attempt = False
        if provider_attempt:
            self.reconcile_provider(attempt_id)
            return
        with self.sessions() as db:
            attempt = db.get(Attempt, attempt_id)
            job = db.get(Job, attempt.job_id)
            if job.status in TERMINAL:
                return
            submission_id = attempt.ray_submission_id
            state = self.ray.status(submission_id)
            age = (now() - attempt.created_at).total_seconds()
            # A stable ID makes an ambiguous submission recoverable without a new attempt.
            if state is None and job.status == "DISPATCHING" and age < 60:
                if job.cancel_requested:
                    with self.sessions.begin() as write:
                        locked = write.scalar(select(Job).where(Job.id == job.id).with_for_update())
                        self.finish(write, locked, write.get(Attempt, attempt.id), "CANCELLED")
                    return
                if attempt.status == "DISPATCHING":
                    # Commit intent before the network call. An uncertain submission is
                    # reconciled or failed, never executed again after cluster state loss.
                    with self.sessions.begin() as write:
                        write.get(Attempt, attempt.id).status = "SUBMITTING"
                    self.ray.submit(attempt)
                return
            timed_out = age > job.requirements["max_runtime_seconds"] + 60
            if state in {"PENDING", "RUNNING"} and (job.cancel_requested or timed_out):
                self.ray.stop(submission_id)
                # Wait for a confirmed terminal state; never report cancellation while still running.
                if timed_out:
                    with self.sessions.begin() as write:
                        write.get(Attempt, attempt.id).error_code = "RUNTIME_EXCEEDED"
                return
            logs = None
            if state in {"SUCCEEDED", "FAILED", "STOPPED"}:
                # Logs for approved templates contain only operational metadata.
                logs = self.ray.logs(submission_id).encode()[:self.storage.settings.max_bytes]
        with self.sessions.begin() as db:
            job = db.scalar(select(Job).where(Job.id == job.id).with_for_update())
            attempt = db.get(Attempt, attempt_id)
            if job.status in TERMINAL:
                return
            if state in {"PENDING", "RUNNING"}:
                if state == "RUNNING":
                    job.status = attempt.status = "RUNNING"
                    attempt.started_at = attempt.started_at or now()
                return
            if state is None:
                self.finish(db, job, attempt, "FAILED", "EXECUTION_LOST")
                return
            if logs is not None and not db.scalar(select(Artifact).where(
                    Artifact.attempt_id == attempt_id, Artifact.kind == "log")):
                db.add(self.storage.put(job.organization_id, "log", logs, job.id, attempt_id))
            if attempt.error_code == "RUNTIME_EXCEEDED":
                self.finish(db, job, attempt, "FAILED", "RUNTIME_EXCEEDED")
            elif job.cancel_requested or state == "STOPPED":
                self.finish(db, job, attempt, "CANCELLED")
            elif state == "SUCCEEDED":
                output = db.scalar(select(Artifact).where(Artifact.attempt_id == attempt_id,
                                                          Artifact.kind == "output"))
                if not output:
                    self.finish(db, job, attempt, "FAILED", "OUTPUT_MISSING")
                else:
                    try:
                        self.storage.read(output)
                    except ArtifactError:
                        self.finish(db, job, attempt, "FAILED", "OUTPUT_INTEGRITY_FAILED")
                    else:
                        self.finish(db, job, attempt, "SUCCEEDED")
            else:
                self.finish(db, job, attempt, "FAILED", "EXECUTION_FAILED")

    def tick(self):
        with self.sessions() as db:
            active = select(Attempt.id).where(Attempt.status.not_in(TERMINAL))
            if self.ray is None:
                active = active.where(Attempt.ray_submission_id.startswith("prov-"))
            ids = list(db.scalars(active))
        for attempt_id in ids:
            self.reconcile(attempt_id)
        if self.ray is not None:
            self.claim()


def main():
    settings = Settings.from_env()
    engine, sessions = database(settings)
    ray_jobs = None
    if not settings.provider_only:
        from core.ray_runtime.client import RayJobs
        ray_jobs = RayJobs(settings.ray_endpoint)
    dispatcher = Dispatcher(sessions, ray_jobs, Storage(settings))
    # This connection owns the MySQL advisory lock for the whole process lifetime.
    with engine.connect() as lock:
        if lock.execute(text("SELECT GET_LOCK('greentokens-dispatcher', 0)")).scalar() != 1:
            raise RuntimeError("A dispatcher is already active")
        try:
            while True:
                # Detect loss of the advisory-lock connection before performing work.
                if lock.execute(text("SELECT IS_USED_LOCK('greentokens-dispatcher') = CONNECTION_ID()")).scalar() != 1:
                    raise RuntimeError("Dispatcher lock lost")
                try:
                    dispatcher.tick()
                except Exception as exc:
                    print(f"Dispatcher tick deferred: {type(exc).__name__}", flush=True)
                time.sleep(1)
        finally:
            lock.execute(text("SELECT RELEASE_LOCK('greentokens-dispatcher')"))


if __name__ == "__main__":
    main()
