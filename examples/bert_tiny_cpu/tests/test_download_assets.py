import hashlib
import importlib.util
import io
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

SCRIPT = Path(__file__).resolve().parents[1] / "download_assets.py"
SPEC = importlib.util.spec_from_file_location("download_assets", SCRIPT)
assets = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(assets)


class DownloadTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.payload = b"known fixture content"
        self.entry = {"path": "dataset/fixture.parquet", "size": len(self.payload),
                      "sha256": hashlib.sha256(self.payload).hexdigest(),
                      "url": "https://huggingface.co/fixture"}

    def test_verified_download_is_skipped_on_second_run(self):
        with patch.object(assets.urllib.request, "urlopen", return_value=io.BytesIO(self.payload)) as request:
            assets.download_file(self.root, self.entry)
            assets.download_file(self.root, self.entry)
            self.assertEqual(request.call_count, 1)
        self.assertEqual((self.root / self.entry["path"]).read_bytes(), self.payload)

    def test_wrong_hash_does_not_replace_existing_file(self):
        destination = self.root / self.entry["path"]
        destination.parent.mkdir()
        destination.write_bytes(b"existing file")
        with patch.object(assets.urllib.request, "urlopen", return_value=io.BytesIO(b"x" * len(self.payload))):
            with self.assertRaisesRegex(ValueError, "SHA-256"):
                assets.download_file(self.root, self.entry)
        self.assertEqual(destination.read_bytes(), b"existing file")
        self.assertEqual(list(destination.parent.glob(".download-*")), [])

    def test_network_failure_cleans_temporary_files(self):
        with patch.object(assets.urllib.request, "urlopen", side_effect=OSError("offline")):
            with self.assertRaises(OSError):
                assets.download_file(self.root, self.entry)
        self.assertFalse((self.root / self.entry["path"]).exists())
        self.assertEqual(list(self.root.rglob(".download-*")), [])

    def test_verify_reports_missing_and_corrupt_files_without_network(self):
        with patch.object(assets.urllib.request, "urlopen") as request:
            self.assertEqual(assets.verify_assets(self.root, {"files": [self.entry]}), [self.entry["path"]])
            destination = self.root / self.entry["path"]
            destination.parent.mkdir()
            destination.write_bytes(b"x" * len(self.payload))
            self.assertEqual(assets.verify_assets(self.root, {"files": [self.entry]}), [self.entry["path"]])
            request.assert_not_called()


if __name__ == "__main__":
    unittest.main()
