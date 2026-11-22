"""Single dispatcher and reconciler; no durable reliance on ObjectRefs."""
import time
from datetime import timedelta

from sqlalchemy import select, text

from core.artifacts.storage import ArtifactError, Storage
from core.config import Settings
from core.database.models import Artifact, Attempt, Job, Usage, Worker, now, uid
from core.database.session import database
from core.ray_runtime.client import RayJobs

TERMINAL = {"SUCCEEDED", "FAILED", "CANCELLED"}


class Dispatcher:
    def __init__(self, sessions, ray_jobs, storage):
        self.sessions, self.ray, self.storage = sessions, ray_jobs, storage

    def claim(self):
        with self.sessions.begin() as db:
            # One in-flight job in this initial local runtime; resource admission remains simple.
            if db.scalar(select(Job.id).where(Job.status.in_(["DISPATCHING", "RUNNING"]))):
                return
            job = db.scalar(select(Job).where(Job.status == "QUEUED").order_by(Job.created_at)
                            .with_for_update(skip_locked=True).limit(1))
            if not job:
                return
            workers = db.scalars(select(Worker).where(Worker.trusted.is_(True), Worker.paused.is_(False),
                Worker.last_seen_at > now() - timedelta(seconds=60))).all()
            if not any(w.cpu_cores >= job.requirements["cpu_cores"] and
                       w.ram_gb >= job.requirements["ram_gb"] and
                       w.workload_class == job.requirements["execution_class"] for w in workers):
                job.status, job.error_code = "FAILED", "NO_ELIGIBLE_WORKER"
                return
            attempt_id = uid()
            db.add(Attempt(id=attempt_id, job_id=job.id, ray_submission_id=f"gt-{attempt_id}"))
            job.status = "DISPATCHING"

    def finish(self, db, job, attempt, status, error=None):
        if job.status in TERMINAL:
            return
        job.status, job.error_code = status, error
        attempt.status, attempt.error_code = status, error
        attempt.finished_at = now()
        attempt.exit_code = 0 if status == "SUCCEEDED" else 1
        if not db.scalar(select(Usage).where(Usage.job_attempt_id == attempt.id)):
            elapsed = max(0, (attempt.finished_at - (attempt.started_at or attempt.created_at)).total_seconds())
            db.add(Usage(job_attempt_id=attempt.id, wall_seconds=elapsed, billable=False))

    def reconcile(self, attempt_id):
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
            ids = list(db.scalars(select(Attempt.id).where(Attempt.status.not_in(TERMINAL))))
        for attempt_id in ids:
            self.reconcile(attempt_id)
        self.claim()


def main():
    settings = Settings.from_env()
    engine, sessions = database(settings)
    dispatcher = Dispatcher(sessions, RayJobs(settings.ray_endpoint), Storage(settings))
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
