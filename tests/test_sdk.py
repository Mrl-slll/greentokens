import contextlib
import io
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "sdk"))
from greentokens import Client
from greentokens.cli import main, load_pipeline


class SDKTests(unittest.TestCase):
    def test_fail_closed_for_remote_or_secret_urls(self):
        for url in ("https://example.com", "http://alice:password@localhost", "http://localhost?key=value"):
            with self.assertRaises(ValueError):
                Client(url)

    def test_init_explain_and_no_overwrite(self):
        with tempfile.TemporaryDirectory() as tmp, contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
            target = str(Path(tmp) / "example")
            self.assertEqual(main(["init", target]), 0)
            config, data = load_pipeline(Path(target) / "training.toml")
            self.assertEqual(config["template_id"], "linear_regression_v1")
            self.assertEqual(data["y"], [1, 3, 5, 7, 9])
            self.assertEqual(main(["init", target]), 1)
            with patch.object(Client, "_call", side_effect=AssertionError("explain must not call API")):
                self.assertEqual(main(["explain", str(Path(target) / "training.toml")]), 0)

    def test_submit_preserves_key_and_input(self):
        client = Client()
        with patch.object(client, "_call", return_value={"job_id": "test"}) as call:
            for _ in range(2):
                client.submit("linear_regression_v1", parameters={"x": [1, 2], "y": [3, 5]}, idempotency_key="same")
            self.assertEqual(call.call_args_list[0], call.call_args_list[1])
        with self.assertRaises(ValueError):
            client.submit("sum_numbers_v1", idempotency_key="key")

    def test_result_refuses_overwrite(self):
        with tempfile.TemporaryDirectory() as tmp, contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
            path = Path(tmp) / "model.json"
            path.write_text("keep me")
            with patch.object(Client, "result", return_value={"result": 10}):
                self.assertEqual(main(["result", "some-id", "--output", str(path)]), 1)
            self.assertEqual(path.read_text(), "keep me")
