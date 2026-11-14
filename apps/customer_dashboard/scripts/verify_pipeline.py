"""Acceptance checks against actual MySQL, S3, Ray Jobs, and a separate API process."""
import time
from concurrent.futures import ThreadPoolExecutor
from datetime import timedelta
from uuid import uuid4

import httpx
from sqlalchemy import select, func

from core.database.models import Artifact, Attempt, Job, Usage, now


def wait_api(client):
    for _ in range(60):
        try:
            if client.get("/health").status_code == 200:
                return
        except httpx.TransportError:
            pass
        time.sleep(1)
    raise AssertionError("API readiness timeout")


def verify(settings, sessions, storage, restart_api, heartbeat, restart_dispatcher):
    alice = {"X-Dev-User": "alice"}
    bob = {"X-Dev-User": "bob"}
    with httpx.Client(base_url="http://127.0.0.1:8000", timeout=20) as api:
        wait_api(api)
        assert api.get("/v1/usage").status_code == 401
        assert api.get("/v1/workers", headers=alice).status_code == 403
        assert api.get("/v1/workers", headers={"X-Dev-User": "admin"}).status_code == 200

        def complete(body):
            response = api.post("/v1/jobs", json=body, headers=alice)
            assert response.status_code == 202, response.text
            job_id = response.json()["job_id"]
            duplicate = api.post("/v1/jobs", json=body, headers=alice)
            assert duplicate.json()["job_id"] == job_id
            with ThreadPoolExecutor(max_workers=4) as pool:
                duplicates = list(pool.map(lambda _: api.post("/v1/jobs", json=body, headers=alice), range(4)))
            assert all(r.status_code == 202 and r.json()["job_id"] == job_id for r in duplicates)
            # Restart the API with a live/queued job; the dispatcher must continue independently.
            restart_api()
            wait_api(api)
            restart_dispatcher()
            for _ in range(150):
                heartbeat()
                job = api.get(f"/v1/jobs/{job_id}", headers=alice).json()
                if job["status"] in {"SUCCEEDED", "FAILED", "CANCELLED"}:
                    break
                time.sleep(1)
            assert job["status"] == "SUCCEEDED", job
            result = api.get(f"/v1/jobs/{job_id}/result", headers=alice)
            assert result.status_code == 200 and result.json()["result"] == 10, result.text
            assert api.get(f"/v1/jobs/{job_id}", headers=bob).status_code == 404
            assert api.get(f"/v1/jobs/{job_id}/result", headers=bob).status_code == 404
            assert api.post(f"/v1/jobs/{job_id}/cancel", headers=bob).status_code == 404
            assert job["attempt_count"] == 1
            assert {a["kind"] for a in job["artifacts"]} == {"output", "log"}
            for artifact in job["artifacts"]:
                path = f"/v1/artifacts/{artifact['artifact_id']}"
                assert api.get(path, headers=alice).status_code == 200
                assert api.get(path, headers=bob).status_code == 404
            with sessions() as db:
                count = db.scalar(select(func.count()).select_from(Usage).join(Attempt)
                                  .where(Attempt.job_id == job_id))
                assert count == 1
            print(f"PASS durable {('file' if body.get('input_artifact_id') else 'inline')} job: "
                  f"{job_id}; result=10; one attempt/usage record; tenant isolation", flush=True)
            return job_id

        first = complete({"template_id": "sum_numbers_v1", "parameters": {"values": [1, 2, 3, 4]},
                          "idempotency_key": str(uuid4())})
        upload = api.post("/v1/artifacts", json={"values": [1, 2, 3, 4]}, headers=alice)
        assert upload.status_code == 201, upload.text
        artifact_id = upload.json()["artifact_id"]
        foreign = {"template_id": "sum_numbers_v1", "input_artifact_id": artifact_id,
                   "idempotency_key": str(uuid4())}
        assert api.post("/v1/jobs", json=foreign, headers=bob).status_code == 404
        complete(foreign)
        restart_api()
        wait_api(api)
        assert api.get(f"/v1/jobs/{first}/result", headers=alice).json()["result"] == 10
        print("PASS API restart retains MySQL records and verified S3 outputs", flush=True)
        corrupt = api.post("/v1/artifacts", json={"values": [9]}, headers=alice).json()["artifact_id"]
        with sessions() as db:
            key = db.get(Artifact, corrupt).object_key
        storage.client.put_object(Bucket=settings.bucket, Key=key, Body=b"corrupt-test-input")
        assert api.get(f"/v1/artifacts/{corrupt}", headers=alice).status_code == 502
        with sessions.begin() as db:
            db.get(Artifact, corrupt).expires_at = now() - timedelta(seconds=1)
        assert api.get(f"/v1/artifacts/{corrupt}", headers=alice).status_code == 410
        print("PASS actual S3 integrity rejection and artifact expiry", flush=True)
    print("MILESTONES 2-3 ACCEPTANCE PASSED (local development identity stub)", flush=True)
