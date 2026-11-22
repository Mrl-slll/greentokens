"""Check the running Next.js proxy against the real local backend and Ray worker.

Run the backend and frontend first, then: python -m scripts.verify_frontend
Creates two small jobs and an input artifact under development identity alice.
"""
import time
from uuid import uuid4

import httpx


def main():
    with httpx.Client(base_url="http://127.0.0.1:3000", timeout=30) as client:
        for page in ("/", "/jobs", "/jobs/new", "/settings"):
            assert client.get(page).status_code == 200, page
        assert client.get("/api/core/health").json()["status"] == "ok"
        assert client.get("/api/core/v1/workers").status_code == 404
        assert client.get("/api/core/v1/usage").status_code == 401
        assert client.post("/api/core/v1/jobs", headers={"Origin": "https://unrelated.example"}, json={}).status_code == 403
        alice = {"X-Dev-User": "alice", "Origin": "http://127.0.0.1:3000"}
        bob = {"X-Dev-User": "bob"}

        def complete(input_fields):
            body = {"template_id": "sum_numbers_v1", **input_fields,
                    "requirements": {"cpu_cores": 1, "ram_gb": 0.125, "gpus": 0,
                                     "execution_class": "trusted_cpu", "max_runtime_seconds": 60},
                    "idempotency_key": f"frontend-check-{uuid4()}"}
            response = client.post("/api/core/v1/jobs", headers=alice, json=body)
            assert response.status_code == 202, response.text
            job_id = response.json()["job_id"]
            replay = client.post("/api/core/v1/jobs", headers=alice, json=body)
            assert replay.status_code == 202 and replay.json()["job_id"] == job_id
            path = f"/api/core/v1/jobs/{job_id}"
            assert client.get(f"/jobs/{job_id}").status_code == 200
            for _ in range(150):
                response = client.get(path, headers=alice)
                response.raise_for_status()
                job = response.json()
                if job["status"] in {"SUCCEEDED", "FAILED", "CANCELLED"}:
                    break
                time.sleep(1)
            assert job["status"] == "SUCCEEDED", job
            result = client.get(f"{path}/result", headers=alice)
            assert result.status_code == 200 and result.json()["result"] == 10, result.text
            assert client.get(path, headers=bob).status_code == 404
            assert client.get(f"{path}/result", headers=bob).status_code == 404
            assert client.post(f"{path}/cancel", headers=bob).status_code == 404
            for artifact in job["artifacts"]:
                artifact_path = f"/api/core/v1/artifacts/{artifact['artifact_id']}"
                assert client.get(artifact_path, headers=alice).status_code == 200
                assert client.get(artifact_path, headers=bob).status_code == 404
            # Cancelling a completed job must preserve the successful result.
            assert client.post(f"{path}/cancel", headers=alice).json()["status"] == "SUCCEEDED"
            print(f"PASS {'upload' if 'input_artifact_id' in body else 'inline'} through Next.js -> FastAPI -> Ray: result=10, replay and tenant isolation", flush=True)

        complete({"parameters": {"values": [1, 2, 3, 4]}})
        upload = client.post("/api/core/v1/artifacts", headers=alice, json={"values": [1, 2, 3, 4]})
        assert upload.status_code == 201, upload.text
        complete({"input_artifact_id": upload.json()["artifact_id"]})
        assert client.get("/api/core/v1/usage", headers=alice).json()["billable"] is False
        print("PASS page routes, origin policy, restricted routes, artifacts, and usage", flush=True)


if __name__ == "__main__":
    main()
