import hashlib
import json
import os
import unittest
from datetime import timedelta
from types import SimpleNamespace
from unittest.mock import patch

from fastapi.testclient import TestClient
from sqlalchemy import create_engine, select, func
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from core.api.main import create_app
from core.artifacts.storage import ArtifactError, Storage
from core.config import Settings
from core.database.models import Artifact, Attempt, Base, Job, Usage, Worker, now
from core.jobs.dispatcher import Dispatcher
from scripts.local_stack import seed


class MemoryStorage:
    def __init__(self):
        self.settings = SimpleNamespace(max_bytes=65536, artifact_ttl_seconds=86400, bucket="test")
        self.objects = {}
        self.client = self

    def put_object(self, Bucket, Key, Body, **kwargs):
        self.objects[Key] = Body

    def get_object(self, Bucket, Key):
        import io
        return {"Body": io.BytesIO(self.objects[Key])}

    put = Storage.put
    read = Storage.read


class FakeRay:
    def __init__(self):
        self.states = {}
        self.submissions = 0

    def status(self, identifier):
        return self.states.get(identifier)

    def submit(self, attempt):
        self.submissions += 1
        self.states[attempt.ray_submission_id] = "PENDING"

    def stop(self, identifier):
        self.states[identifier] = "STOPPED"

    def logs(self, identifier):
        return "approved execution log"


class CoreTests(unittest.TestCase):
    def setUp(self):
        self.engine = create_engine("sqlite://", poolclass=StaticPool,
                                    connect_args={"check_same_thread": False})
        Base.metadata.create_all(self.engine)
        self.sessions = sessionmaker(self.engine, expire_on_commit=False)
        seed(self.sessions)
        with self.sessions.begin() as db:
            db.add(Worker(id="node", hostname="local", cpu_cores=4, ram_gb=4))
        self.storage = MemoryStorage()
        self.settings = SimpleNamespace(max_bytes=65536)
        self.client = TestClient(create_app(self.settings, self.sessions, self.storage))
        self.alice = {"X-Dev-User": "alice"}
        self.bob = {"X-Dev-User": "bob"}
        self.ray = FakeRay()
        self.dispatcher = Dispatcher(self.sessions, self.ray, self.storage)

    def tearDown(self):
        self.client.close()
        self.engine.dispose()

    def submit(self, **changes):
        body = {"template_id": "sum_numbers_v1", "parameters": {"values": [1, 2, 3, 4]},
                "idempotency_key": "test"}
        body.update(changes)
        return self.client.post("/v1/jobs", json=body, headers=self.alice)

    def claimed(self):
        job_id = self.submit().json()["job_id"]
        self.dispatcher.claim()
        with self.sessions() as db:
            attempt = db.scalar(select(Attempt).where(Attempt.job_id == job_id))
        return job_id, attempt

    def test_idempotency_and_body_ownership(self):
        first = self.submit()
        self.assertEqual(first.status_code, 202)
        self.assertEqual(first.json()["job_id"], self.submit().json()["job_id"])
        self.assertEqual(self.submit(parameters={"values": [9]}).status_code, 409)
        self.assertEqual(self.submit(organization_id="org-b").status_code, 422)
        with self.sessions() as db:
            self.assertEqual(db.scalar(select(func.count()).select_from(Job)), 1)

    def test_validation_and_resource_policy(self):
        for change in ({"template_id": "python"}, {"parameters": {"values": [True]}},
                       {"parameters": {"values": []}}, {"requirements": {"gpus": 1}},
                       {"entrypoint": "anything"}, {"requirements": {"max_runtime_seconds": 0}}):
            self.assertEqual(self.submit(**change).status_code, 422)
        with self.sessions.begin() as db:
            db.get(Worker, "node").paused = True
        self.assertEqual(self.submit().status_code, 422)

    def test_identity_and_tenant_isolation(self):
        self.assertEqual(self.client.get("/v1/usage").status_code, 401)
        self.assertEqual(self.client.get("/v1/workers", headers=self.alice).status_code, 403)
        job_id = self.submit().json()["job_id"]
        for path in (f"/v1/jobs/{job_id}", f"/v1/jobs/{job_id}/result"):
            self.assertEqual(self.client.get(path, headers=self.bob).status_code, 404)
        self.assertEqual(self.client.post(f"/v1/jobs/{job_id}/cancel", headers=self.bob).status_code, 404)

    def test_artifact_owner_expiry_integrity_and_size(self):
        response = self.client.post("/v1/artifacts", json={"values": [1, 2]}, headers=self.alice)
        self.assertEqual(response.status_code, 201)
        artifact_id = response.json()["artifact_id"]
        path = f"/v1/artifacts/{artifact_id}"
        self.assertEqual(self.client.get(path, headers=self.bob).status_code, 404)
        with self.sessions.begin() as db:
            artifact = db.get(Artifact, artifact_id)
            key = artifact.object_key
        self.storage.objects[key] = b"corrupt"
        self.assertEqual(self.client.get(path, headers=self.alice).status_code, 502)
        with self.sessions.begin() as db:
            db.get(Artifact, artifact_id).expires_at = now() - timedelta(seconds=1)
        self.assertEqual(self.client.get(path, headers=self.alice).status_code, 410)
        self.assertEqual(self.client.post("/v1/artifacts", content=b"x" * 65537,
                                         headers=self.alice).status_code, 413)

    def test_queued_cancel_creates_no_attempt(self):
        job_id = self.submit().json()["job_id"]
        self.assertEqual(self.client.post(f"/v1/jobs/{job_id}/cancel", headers=self.alice).json()["status"], "CANCELLED")
        self.dispatcher.tick()
        with self.sessions() as db:
            self.assertEqual(db.scalar(select(func.count()).select_from(Attempt)), 0)

    def test_completion_is_idempotent(self):
        job_id, attempt = self.claimed()
        with self.sessions.begin() as db:
            db.add(self.storage.put("org-a", "output", b'{"result":10}', job_id, attempt.id))
        self.ray.states[attempt.ray_submission_id] = "SUCCEEDED"
        self.dispatcher.reconcile(attempt.id)
        self.dispatcher.reconcile(attempt.id)
        self.assertEqual(self.client.get(f"/v1/jobs/{job_id}/result", headers=self.alice).json()["result"], 10)
        with self.sessions() as db:
            self.assertEqual(db.scalar(select(func.count()).select_from(Usage)), 1)
            self.assertFalse(db.scalar(select(Usage)).billable)

    def test_missing_output_fails(self):
        job_id, attempt = self.claimed()
        self.ray.states[attempt.ray_submission_id] = "SUCCEEDED"
        self.dispatcher.reconcile(attempt.id)
        job = self.client.get(f"/v1/jobs/{job_id}", headers=self.alice).json()
        self.assertEqual(job["error_code"], "OUTPUT_MISSING")

    def test_corrupt_output_cannot_become_success(self):
        job_id, attempt = self.claimed()
        with self.sessions.begin() as db:
            artifact = self.storage.put("org-a", "output", b'{"result":10}', job_id, attempt.id)
            db.add(artifact)
            self.storage.objects[artifact.object_key] = b'{"result":99}'
        self.ray.states[attempt.ray_submission_id] = "SUCCEEDED"
        self.dispatcher.reconcile(attempt.id)
        job = self.client.get(f"/v1/jobs/{job_id}", headers=self.alice).json()
        self.assertEqual(job["status"], "FAILED")
        self.assertEqual(job["error_code"], "OUTPUT_INTEGRITY_FAILED")

    def test_dispatch_rechecks_worker_freshness(self):
        job_id = self.submit().json()["job_id"]
        with self.sessions.begin() as db:
            db.get(Worker, "node").last_seen_at = now() - timedelta(seconds=61)
        self.dispatcher.claim()
        self.assertEqual(self.client.get(f"/v1/jobs/{job_id}", headers=self.alice).json()["error_code"], "NO_ELIGIBLE_WORKER")

    def test_foreign_input_cannot_be_submitted(self):
        upload = self.client.post("/v1/artifacts", json={"values": [1]}, headers=self.alice)
        response = self.client.post("/v1/jobs", headers=self.bob, json={
            "template_id": "sum_numbers_v1", "input_artifact_id": upload.json()["artifact_id"],
            "idempotency_key": "foreign"})
        self.assertEqual(response.status_code, 404)

    def test_failed_execution(self):
        job_id, attempt = self.claimed()
        self.ray.states[attempt.ray_submission_id] = "FAILED"
        self.dispatcher.reconcile(attempt.id)
        self.assertEqual(self.client.get(f"/v1/jobs/{job_id}", headers=self.alice).json()["status"], "FAILED")

    def test_uncertain_submission_is_not_reexecuted(self):
        job_id, attempt = self.claimed()
        self.dispatcher.reconcile(attempt.id)
        self.ray.states.clear()  # Cluster lost its job records after submission.
        self.dispatcher.reconcile(attempt.id)
        self.assertEqual(self.ray.submissions, 1)
        with self.sessions.begin() as db:
            db.get(Attempt, attempt.id).created_at = now() - timedelta(seconds=61)
        self.dispatcher.reconcile(attempt.id)
        self.assertEqual(self.client.get(f"/v1/jobs/{job_id}", headers=self.alice).json()["error_code"], "EXECUTION_LOST")

    def test_running_cancel_waits_for_stop_confirmation(self):
        job_id, attempt = self.claimed()
        self.ray.states[attempt.ray_submission_id] = "RUNNING"
        self.client.post(f"/v1/jobs/{job_id}/cancel", headers=self.alice)
        self.dispatcher.reconcile(attempt.id)
        self.dispatcher.reconcile(attempt.id)
        self.assertEqual(self.client.get(f"/v1/jobs/{job_id}", headers=self.alice).json()["status"], "CANCELLED")

    def test_runtime_limit(self):
        job_id, attempt = self.claimed()
        with self.sessions.begin() as db:
            db.get(Attempt, attempt.id).created_at = now() - timedelta(seconds=121)
        self.ray.states[attempt.ray_submission_id] = "RUNNING"
        self.dispatcher.reconcile(attempt.id)
        self.dispatcher.reconcile(attempt.id)
        self.assertEqual(self.client.get(f"/v1/jobs/{job_id}", headers=self.alice).json()["error_code"], "RUNTIME_EXCEEDED")

    def test_production_startup_is_blocked(self):
        with patch.dict(os.environ, {"GT_MODE": "production"}):
            with self.assertRaises(RuntimeError):
                Settings.from_env()


if __name__ == "__main__":
    unittest.main()
