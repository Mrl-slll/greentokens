from pathlib import Path
import sys
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "databricks"))
from greentokens_client import DatabricksClient


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


if __name__ == "__main__":
    unittest.main()
