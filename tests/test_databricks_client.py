from pathlib import Path
import sys
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "databricks"))
from greentokens_client import DatabricksClient, model_artifact_id, summarize


class DatabricksClientTests(unittest.TestCase):
    def test_rejects_non_https_credentials_and_missing_token(self):
        for url in ("http://x.example", "https://u:p@x.example", "https://x.example/a?k=v"):
            with self.assertRaises(ValueError):
                DatabricksClient(url, "t")
        with self.assertRaises(ValueError):
            DatabricksClient("https://x.example", "")

    def test_sends_bearer_token_only_in_header(self):
        client = DatabricksClient("https://x.example/", "secret")
        seen = {}

        class Resp:
            def __enter__(self): return self
            def __exit__(self, *a): return False
            def read(self): return b'{"ok": true}'

        def fake_open(request, timeout):
            seen["url"], seen["auth"] = request.full_url, request.get_header("Authorization")
            return Resp()

        with patch.object(client.transport, "open", side_effect=fake_open):
            self.assertEqual(client.check(), {"ok": True})
        self.assertEqual(seen["auth"], "Bearer secret")
        self.assertNotIn("secret", seen["url"])


    def test_summarize_a_two_computer_training_job(self):
        job = {"job_id": "j1", "status": "SUCCEEDED", "template_id": "bert_tiny_ddp_v1", "created_at": "t0", "updated_at": "t1",
               "error_code": None, "artifacts": [{"kind": "output", "artifact_id": "o"},
                                                 {"kind": "model", "artifact_id": "m", "size_bytes": 16700000, "sha256": "abc"}]}
        result = {"result": {"eval_before": {"accuracy": 0.545}, "eval_after": {"accuracy": 0.62}, "first_loss": 0.67,
                             "last_loss": 0.54, "wall_seconds": 55.7,
                             "computers": [{"host": "Mac", "os": "Darwin arm64", "rank": 0, "train_seconds": 6.8},
                                           {"host": "Cody", "os": "Windows AMD64", "rank": 1, "train_seconds": 50.6}]}}
        summary, rows = summarize(job, result)
        self.assertEqual((summary["computers"], summary["computer_names"]), (2, "Mac, Cody"))
        self.assertEqual((summary["accuracy_before"], summary["accuracy_after"], summary["model_mb"]), (0.545, 0.62, 16.7))
        self.assertEqual([r["computer"] for r in rows], ["Mac", "Cody"])
        self.assertEqual(model_artifact_id(job), "m")

    def test_summarize_simple_and_unfinished_jobs(self):
        simple = {"job_id": "j2", "status": "SUCCEEDED", "template_id": "linear_regression_v1", "artifacts": []}
        summary, rows = summarize(simple, {"result": {"slope": 2.0}})
        self.assertEqual((summary["computers"], summary["model_mb"], rows), (None, None, []))
        running = {"job_id": "j3", "status": "RUNNING", "template_id": "bert_tiny_ddp_v1", "artifacts": []}
        summary, rows = summarize(running, None)
        self.assertEqual((summary["status"], summary["result_json"], rows), ("RUNNING", None, []))


if __name__ == "__main__":
    unittest.main()
