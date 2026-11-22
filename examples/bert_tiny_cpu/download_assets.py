"""Download pinned training assets and verify their SHA-256 hashes.

The model is committed in Git. SST-2 is downloaded locally, not redistributed.
Only Python's standard library is required; certifi is used when available.
"""
import argparse
import hashlib
import json
import os
import ssl
import tempfile
import urllib.request
from pathlib import Path

ASSET_ROOT = Path(__file__).resolve().parent / "assets"


def load_manifest():
    return json.loads((ASSET_ROOT / "manifest.json").read_text(encoding="utf-8"))


def matches(path, entry):
    if not path.is_file() or path.stat().st_size != entry["size"]:
        return False
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest() == entry["sha256"]


def verify_assets(directory, manifest):
    return [entry["path"] for entry in manifest["files"]
            if not matches(directory / entry["path"], entry)]


def download_file(directory, entry):
    destination = directory / entry["path"]
    if matches(destination, entry):
        print(f"VERIFIED {entry['path']}", flush=True)
        return
    destination.parent.mkdir(parents=True, exist_ok=True)
    try:
        import certifi
    except ImportError:
        context = ssl.create_default_context()
    else:
        context = ssl.create_default_context(cafile=certifi.where())
    # Never turn off certificate verification. Only replace a file after its
    # size and hash match the manifest; failed transfers keep existing files.
    fd, name = tempfile.mkstemp(prefix=".download-", dir=destination.parent)
    temporary = Path(name)
    try:
        with os.fdopen(fd, "wb") as target:
            request = urllib.request.Request(entry["url"], headers={"User-Agent": "GreenTokens-CPU-Starter/1.0"})
            with urllib.request.urlopen(request, timeout=60, context=context) as response:
                while chunk := response.read(1024 * 1024):
                    target.write(chunk)
        if not matches(temporary, entry):
            raise ValueError(f"Downloaded file failed size/SHA-256 verification: {entry['path']}")
        temporary.replace(destination)
        print(f"DOWNLOADED AND VERIFIED {entry['path']}", flush=True)
    finally:
        temporary.unlink(missing_ok=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--assets-dir", type=Path, default=ASSET_ROOT)
    parser.add_argument("--verify-only", action="store_true", help="Check local files without network access")
    args = parser.parse_args()
    manifest = load_manifest()
    if not args.verify_only:
        print("SST-2 upstream license metadata: unknown; files are downloaded for local use, not committed.", flush=True)
        for entry in manifest["files"]:
            download_file(args.assets_dir, entry)
    problems = verify_assets(args.assets_dir, manifest)
    if problems:
        parser.exit(1, "Missing or mismatched assets: " + ", ".join(problems) + "\n")
    print(f"READY: all {len(manifest['files'])} assets verified in {args.assets_dir.resolve()}")


if __name__ == "__main__":
    main()
