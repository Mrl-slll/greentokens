import hashlib
import json
from pathlib import Path
import tempfile
from unittest.mock import patch

from tests.test_provider_auth import ProviderAuthTests
from core.api.shared_test import HOSTS


class SharedTrainingTests(ProviderAuthTests):
    def test_targeting_integrity_and_four_party_barrier(self):
        with tempfile.TemporaryDirectory() as tmp, patch("core.api.shared_test.ROOT", Path(tmp)):
            participants = []
            for rank, host in enumerate((*HOSTS, "CODY")):
                device = f"device-{rank:04}"
                headers = self.bearer(self.signup(username=f"test-{rank}", device_id=device))
                response = self.client.post("/v1/provider/heartbeat", headers=headers,
                            json={"device_id": device, "name": host, "status": "online",
                                  "capabilities": {"cpus": 20, "ram_gb": 31.7}})
                self.assertEqual(response.status_code, 200)
                participants.append((device, headers))
            cfg = self.client.post("/v1/shared-test", headers={"X-Dev-User": "admin"})
            self.assertEqual(cfg.status_code, 201, cfg.text)
            cfg = cfg.json()
            base = "/v1/shared-test/" + cfg["run_id"]
            for rank, (device, headers) in enumerate(participants):
                assignment = self.client.post("/v1/provider/work", headers=headers,
                                              json={"device_id": device, "wait_seconds": 0})
                if rank == 4:
                    self.assertEqual(assignment.status_code, 204)
                else:
                    self.assertEqual(assignment.status_code, 200)
                    self.assertEqual(assignment.json()["parameters"]["rank"], rank)
            data = b"test-gradient"
            digest = hashlib.sha256(data).hexdigest()
            h = participants[0][1]
            self.assertEqual(self.client.put(base + "/blob/init/0/0", headers={**h, "X-Content-SHA256": digest},
                                            content=data).status_code, 200)
            self.assertEqual(self.client.put(base + "/blob/init/0/0", headers=participants[1][1],
                                            content=data).status_code, 403)
            self.assertEqual(self.client.get(base + "/blob/init/0/0", headers=participants[4][1]).status_code, 403)
            self.assertEqual(self.client.put(base + "/manifest/init/0", headers=h,
                json={"size": len(data), "hashes": [digest], "sha256": digest}).status_code, 200)
            self.assertEqual(self.client.get(base + "/blob/init/0/0", headers=participants[2][1]).content, data)
            for rank in range(4):
                reply = self.client.post(base + "/barrier/0", headers=participants[rank][1],
                    json={"weights_sha256": digest, "dataset_fingerprint": "same-data"})
                self.assertEqual(reply.status_code, 200 if rank == 3 else 202)
            self.assertFalse(reply.json()["stop"])
            state_path = Path(tmp) / cfg["run_id"] / "state.json"
            state = json.loads(state_path.read_text())
            state["started"] -= 1801
            state_path.write_text(json.dumps(state))
            for rank in range(4):
                reply = self.client.post(base + "/barrier/1", headers=participants[rank][1],
                                         json={"weights_sha256": digest})
            self.assertTrue(reply.json()["stop"])
