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
from core.database.models import Artifact, Attempt, Base, Job, Organization, Usage, User, Worker, now
from core.jobs.dispatcher import Dispatcher
from scripts.local_stack import heartbeat, seed


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

    def keyed_client(self):
        digest = hashlib.sha256(b"gt_testkey").hexdigest()
        settings = SimpleNamespace(max_bytes=65536, api_keys={digest: "alice"})
        return TestClient(create_app(settings, self.sessions, self.storage))

    def test_api_key_auth_and_tunnel_rules(self):
        body = {"template_id": "sum_numbers_v1", "parameters": {"values": [1]}, "idempotency_key": "k1"}
        with self.keyed_client() as c:
            good = {"Authorization": "Bearer gt_testkey"}
            self.assertEqual(c.post("/v1/jobs", json=body, headers=good).status_code, 202)
            self.assertEqual(c.get("/v1/usage", headers={"Authorization": "Bearer wrong"}).status_code, 401)
            # Tunneled requests (proxy headers) cannot use the dev identity stub...
            tunneled = {"X-Dev-User": "alice", "Cf-Connecting-Ip": "203.0.113.5"}
            self.assertEqual(c.get("/v1/usage", headers=tunneled).status_code, 401)
            # ...but a valid key still works through the tunnel, and docs are hidden.
            self.assertEqual(c.get("/v1/usage", headers={**good, "Cf-Ray": "x"}).status_code, 200)
            self.assertEqual(c.get("/docs", headers={"Cf-Ray": "x"}).status_code, 404)
            self.assertEqual(c.get("/openapi.json", headers={"Cf-Ray": "x"}).status_code, 404)
            # A key acts as its own user: bob's job is invisible to alice's key.
            bob_job = self.client.post("/v1/jobs", json={**body, "idempotency_key": "b"}, headers=self.bob).json()["job_id"]
            self.assertEqual(c.get(f"/v1/jobs/{bob_job}", headers=good).status_code, 404)
            # Local dev stub still works without proxy headers.
            self.assertEqual(c.get("/v1/usage", headers=self.alice).status_code, 200)

    def test_provider_only_server(self):
        job_id, attempt = self.claimed()
        self.settings.provider_only = True
        self.settings.api_keys = {hashlib.sha256(b"test-customer").hexdigest(): "alice"}
        with TestClient(create_app(self.settings, self.sessions, self.storage)) as client:
            self.assertEqual(client.get("/health").json()["authentication"], "bearer")
            self.assertEqual(client.get("/v1/usage", headers=self.alice).status_code, 401)
            auth = {"Authorization": "Bearer test-customer"}
            self.assertEqual(client.get("/v1/usage", headers=auth).status_code, 200)
            body = {"template_id": "sum_numbers_v1", "parameters": {"values": [1]}, "idempotency_key": "new"}
            self.assertEqual(client.post("/v1/jobs", json=body, headers=auth).status_code, 422)
        Dispatcher(self.sessions, None, self.storage).tick()
        with self.sessions() as db:
            self.assertEqual(db.get(Attempt, attempt.id).status, "DISPATCHING")
            self.assertEqual(db.get(Job, job_id).status, "DISPATCHING")

    def test_heartbeat_registers_every_live_node(self):
        class Nodes:
            def nodes(self):
                return [{"Alive": True, "NodeID": "n1", "NodeManagerHostname": "leader", "Resources": {"CPU": 4.0, "memory": 4 * 1024**3}},
                        {"Alive": True, "NodeID": "n2", "NodeManagerHostname": "mac", "Resources": {"CPU": 8.0, "memory": 8 * 1024**3}},
                        {"Alive": False, "NodeID": "n3", "NodeManagerHostname": "gone", "Resources": {"CPU": 2.0}}]
        heartbeat(self.sessions, Nodes())
        with self.sessions() as db:
            rows = {w.id: w for w in db.scalars(select(Worker))}
        self.assertEqual((rows["n1"].hostname, rows["n1"].cpu_cores), ("leader", 4))
        self.assertEqual((rows["n2"].hostname, rows["n2"].cpu_cores, round(rows["n2"].ram_gb)), ("mac", 8, 8))
        self.assertNotIn("n3", rows)

    def test_ray_job_gets_settings_through_a_private_file_not_runtime_env(self):
        from core.ray_runtime import client as ray_client
        sent = {}
        class FakeJobs:
            def __init__(self, endpoint): pass
            def submit_job(self, **kwargs): sent.update(kwargs); return "id"
        import tempfile
        from pathlib import Path
        with tempfile.TemporaryDirectory() as tmp, patch.object(ray_client, "JobSubmissionClient", FakeJobs),              patch.object(ray_client, "JOB_ENV_DIR", Path(tmp)),              patch.dict(os.environ, {"GT_MODE": "development", "RAY_AUTH_TOKEN": "t", "UNRELATED_SECRET": "x"}):
            ray_client.RayJobs("http://127.0.0.1:8265").submit(SimpleNamespace(id="a", ray_submission_id="gt-a"))
            self.assertNotIn("runtime_env", sent)  # would be copied to every computer and break Mac workers
            self.assertIn("--env-file", sent["entrypoint"])
            saved = json.loads((Path(tmp) / "a.json").read_text())
        self.assertEqual(saved["GT_MODE"], "development")
        self.assertNotIn("UNRELATED_SECRET", saved)

    def test_run_job_reads_and_deletes_its_private_file(self):
        import tempfile
        from pathlib import Path
        from scripts.run_job import load_private_env
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "x.json"
            path.write_text(json.dumps({"GT_TEST_SETTING": "1"}))
            with patch.dict(os.environ, {}, clear=False):
                load_private_env(["run_job.py", "attempt", "--env-file", str(path)])
                self.assertEqual(os.environ["GT_TEST_SETTING"], "1")
                os.environ.pop("GT_TEST_SETTING")
            self.assertFalse(path.exists())

    def bert(self, **params):
        body = {"template_id": "bert_tiny_ddp_v1", "parameters": params,
                "requirements": {"cpu_cores": 2, "max_runtime_seconds": 1800}, "idempotency_key": "bert"}
        return self.client.post("/v1/jobs", json=body, headers=self.alice)

    def test_bert_job_needs_one_online_computer_per_worker(self):
        # setUp has a single worker row: 2 workers cannot run, 1 can.
        response = self.bert(workers=2)
        self.assertEqual(response.status_code, 422)
        self.assertIn("Not enough computers online", response.json()["detail"])
        self.assertEqual(self.bert(workers=1).status_code, 202)
        with self.sessions.begin() as db:
            db.add(Worker(id="mac", hostname="mac", cpu_cores=5, ram_gb=1))
        body = {"template_id": "bert_tiny_ddp_v1", "parameters": {"workers": 2},
                "requirements": {"max_runtime_seconds": 1800}, "idempotency_key": "bert2"}
        self.assertEqual(self.client.post("/v1/jobs", json=body, headers=self.alice).status_code, 202)

    def test_bert_dispatch_fails_when_a_computer_has_gone(self):
        with self.sessions.begin() as db:
            db.add(Worker(id="mac", hostname="mac", cpu_cores=5, ram_gb=1))
        body = {"template_id": "bert_tiny_ddp_v1", "parameters": {"workers": 2},
                "requirements": {"max_runtime_seconds": 1800}, "idempotency_key": "bert3"}
        job_id = self.client.post("/v1/jobs", json=body, headers=self.alice).json()["job_id"]
        with self.sessions.begin() as db:
            db.get(Worker, "mac").last_seen_at = now() - timedelta(minutes=5)  # the Mac went offline
        self.dispatcher.claim()
        with self.sessions() as db:
            job = db.get(Job, job_id)
        self.assertEqual((job.status, job.error_code), ("FAILED", "NO_ELIGIBLE_WORKER"))

    def test_bert_limits_and_other_templates_stay_short(self):
        self.assertEqual(self.bert(workers=9).status_code, 422)
        self.assertEqual(self.bert(workers=2, global_batch=1).status_code, 422)
        self.assertEqual(self.bert(values=[1]).status_code, 422)
        long_sum = self.submit(requirements={"max_runtime_seconds": 900})
        self.assertEqual(long_sum.status_code, 422)

    def test_model_artifacts_may_be_large_but_other_kinds_may_not(self):
        big = b"x" * (5 * 1024 * 1024)
        model = self.storage.put("org-a", "model", big, None, None)
        self.assertEqual(self.storage.read(model), big)
        with self.assertRaises(ArtifactError):
            self.storage.put("org-a", "output", big)
        from core.artifacts import storage as storage_module
        with patch.dict(storage_module.LARGE_KIND_LIMITS, {"model": 1024}), self.assertRaises(ArtifactError):
            self.storage.put("org-a", "model", b"x" * 1025)

    def test_model_download_is_binary_and_owner_only(self):
        job_id = self.submit().json()["job_id"]
        model = self.storage.put("org-a", "model", b"\x00\x01weights", job_id, None)
        with self.sessions.begin() as db:
            db.add(model)
        ok = self.client.get(f"/v1/artifacts/{model.id}", headers=self.alice)
        self.assertEqual((ok.status_code, ok.headers["content-type"], ok.content), (200, "application/octet-stream", b"\x00\x01weights"))
        self.assertEqual(self.client.get(f"/v1/artifacts/{model.id}", headers=self.bob).status_code, 404)

    # ---- independent providers (connect outward, ask for work; no Ray on the provider) ----
    def provider_setup(self):
        with self.sessions.begin() as db:
            db.add(Organization(id="org-p", name="Providers"))
            db.flush()
            db.add(User(id="prov1", organization_id="org-p", role="provider"))
            db.add(User(id="prov2", organization_id="org-p", role="provider"))
        keys = {hashlib.sha256(b"gt_provider_one").hexdigest(): "prov1", hashlib.sha256(b"gt_provider_two").hexdigest(): "prov2",
                hashlib.sha256(b"gt_customer").hexdigest(): "alice"}
        client = TestClient(create_app(SimpleNamespace(max_bytes=65536, api_keys=keys), self.sessions, self.storage))
        return client, {"Authorization": "Bearer gt_provider_one"}, {"Authorization": "Bearer gt_customer"}

    def beat(self, client, headers, device="device-0001", gpu=False):
        caps = {"os": "Windows", "arch": "AMD64", "cpus": 16, "ram_gb": 32,
                "gpus": [{"name": "NVIDIA GeForce RTX 5070", "vram_gb": 12}] if gpu else [], "torch_cuda": gpu}
        return client.post("/v1/provider/heartbeat", headers=headers,
                           json={"device_id": device, "name": "PC-" + device[-4:], "status": "online", "capabilities": caps})

    def finetune(self, client, headers, key="ft1", **params):
        return client.post("/v1/jobs", headers=headers, json={"template_id": "text_finetune_v1", "parameters": params,
                           "requirements": {"max_runtime_seconds": 1800}, "idempotency_key": key})

    def test_provider_connects_runs_a_job_and_returns_results(self):
        client, prov, cust = self.provider_setup()
        with client:
            self.assertEqual(self.finetune(client, cust).status_code, 422)  # no provider online yet
            self.assertEqual(self.beat(client, prov, gpu=True).status_code, 200)
            job_id = self.finetune(client, cust, require_gpu=True).json()["job_id"]
            work = client.post("/v1/provider/work", headers=prov, json={"device_id": "device-0001", "wait_seconds": 0}).json()
            self.assertEqual((work["job_id"], work["workload"]["name"]), (job_id, "text_finetune"))
            package = client.get(work["workload"]["url"], headers=prov)
            self.assertEqual(hashlib.sha256(package.content).hexdigest(), work["workload"]["sha256"])
            attempt, q = work["attempt_id"], {"device_id": "device-0001"}
            self.assertTrue(client.post(f"/v1/provider/work/{attempt}/lease", headers=prov, json=q).json()["continue"])
            output = json.dumps({"result": {"eval_after": {"accuracy": 0.8}}, "job_id": job_id, "attempt_id": attempt}).encode()
            self.assertEqual(client.put(f"/v1/provider/work/{attempt}/artifacts/output", params=q, headers=prov, content=output).status_code, 200)
            self.assertEqual(client.put(f"/v1/provider/work/{attempt}/artifacts/model", params=q, headers=prov, content=b"w" * 70000).status_code, 200)
            done = client.post(f"/v1/provider/work/{attempt}/complete", headers=prov, json={**q, "status": "SUCCEEDED"}).json()
            self.assertEqual(done["status"], "SUCCEEDED")
            status = client.get(f"/v1/jobs/{job_id}", headers=cust).json()
            self.assertEqual(status["attempts"][0]["worker_hostname"], "PC-0001")
            self.assertEqual({a["kind"] for a in status["artifacts"]}, {"output", "model"})
            self.assertEqual(client.get(f"/v1/jobs/{job_id}/result", headers=cust).json()["result"]["eval_after"]["accuracy"], 0.8)

    def test_lost_provider_job_is_requeued_and_a_reconnect_gets_work(self):
        client, prov, cust = self.provider_setup()
        with client:
            self.beat(client, prov)
            job_id = self.finetune(client, cust).json()["job_id"]
            first = client.post("/v1/provider/work", headers=prov, json={"device_id": "device-0001", "wait_seconds": 0}).json()
            again = client.post("/v1/provider/work", headers=prov, json={"device_id": "device-0001", "wait_seconds": 0}).json()
            self.assertEqual(first["attempt_id"], again["attempt_id"])  # reconnecting mid-job resumes the same work
            with self.sessions.begin() as db:
                db.get(Attempt, first["attempt_id"]).lease_expires_at = now() - timedelta(seconds=1)  # provider vanished
            self.dispatcher.tick()
            with self.sessions() as db:
                self.assertEqual(db.get(Job, job_id).status, "QUEUED")
                self.assertEqual(db.get(Attempt, first["attempt_id"]).error_code, "PROVIDER_LOST")
            self.assertEqual(self.ray.submissions, 0)  # provider jobs never go to the server's Ray
            self.beat(client, prov)  # reconnect
            retry = client.post("/v1/provider/work", headers=prov, json={"device_id": "device-0001", "wait_seconds": 0}).json()
            self.assertEqual((retry["job_id"], retry["attempt_id"] != first["attempt_id"]), (job_id, True))

    def test_provider_security_boundaries(self):
        client, prov, cust = self.provider_setup()
        with client:
            self.assertEqual(self.beat(client, cust).status_code, 403)  # customer key is not a provider key
            self.beat(client, prov)
            self.assertEqual(self.finetune(client, prov, key="p").status_code, 403)  # providers cannot submit jobs
            other = {"Authorization": "Bearer gt_provider_two"}
            self.assertEqual(self.beat(client, other, device="device-0001").status_code, 403)  # someone else's device
            self.assertEqual(client.post("/v1/provider/work", headers=other, json={"device_id": "device-0001", "wait_seconds": 0}).status_code, 404)
            self.finetune(client, cust, key="gpu", require_gpu=True)
            self.assertEqual(self.finetune(client, cust, key="gpu2", require_gpu=True).status_code, 422)  # no GPU provider online
            self.assertEqual(client.post("/v1/provider/work", headers=prov, json={"device_id": "device-0001", "wait_seconds": 0}).status_code, 204)
            self.assertEqual(client.get("/v1/provider/packages/../../etc", headers=prov).status_code, 404)

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

    def test_training_contract_and_validation(self):
        data = {"x": [0, 1, 2, 3], "y": [1, 3, 5, 7]}
        response = self.submit(template_id="linear_regression_v1", parameters=data)
        self.assertEqual(response.status_code, 202)
        detail = self.client.get(f"/v1/jobs/{response.json()['job_id']}", headers=self.alice).json()
        self.assertEqual(detail["input_source"], "inline")
        self.assertEqual(detail["requirements"]["gpus"], 0)
        for bad in ({"x": [1, 1], "y": [2, 3]}, {"x": [1, 2], "y": [3]},
                    {"x": [True, 2], "y": [3, 4]}, {"x": [1, 2e6], "y": [3, 4]},
                    {"values": [1, 2]}):
            self.assertEqual(self.submit(template_id="linear_regression_v1", parameters=bad).status_code, 422)
        self.assertEqual(self.submit(parameters=data).status_code, 422)

    def test_uploaded_training_data_pipeline_and_ownership(self):
        uploaded = self.client.post("/v1/artifacts", headers=self.alice,
                                    json={"x": [0, 1, 2], "y": [1, 3, 5]})
        self.assertEqual(uploaded.status_code, 201)
        artifact_id = uploaded.json()["artifact_id"]
        self.assertEqual(self.submit(template_id="linear_regression_v1", parameters=None,
                                     input_artifact_id=artifact_id).status_code, 202)
        self.assertEqual(self.submit(parameters=None, input_artifact_id=artifact_id,
                                     idempotency_key="wrong-template").status_code, 422)
        body = {"template_id": "linear_regression_v1", "input_artifact_id": artifact_id, "idempotency_key": "other"}
        self.assertEqual(self.client.post("/v1/jobs", headers=self.bob, json=body).status_code, 404)

    def test_real_training_math(self):
        from core.training import train_linear
        model = train_linear({"x": [0, 1, 2, 3], "y": [1, 3, 5, 7]})
        self.assertEqual(model["slope"], 2)
        self.assertEqual(model["intercept"], 1)
        self.assertEqual(model["training_mse"], 0)


if __name__ == "__main__":
    unittest.main()
