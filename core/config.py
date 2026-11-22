import json
import os
from pathlib import Path
from dataclasses import dataclass, field
from urllib.parse import urlsplit


def load_api_keys():
    """sha256(key) -> existing user id. Hashes only; read from GT_API_KEYS and, if present,
    ~/.greentokens/api_keys.json (kept outside the repository)."""
    keys = json.loads(os.environ.get("GT_API_KEYS", "{}"))
    path = Path.home() / ".greentokens" / "api_keys.json"
    if path.is_file():
        keys.update(json.loads(path.read_text(encoding="utf-8")))
    return keys


@dataclass
class Settings:
    database_url: str = field(repr=False)
    s3_access_key: str = field(repr=False)
    s3_secret_key: str = field(repr=False)
    s3_endpoint: str = "http://127.0.0.1:8333"
    bucket: str = "greentokens"
    ray_endpoint: str = "http://127.0.0.1:8265"
    artifact_ttl_seconds: int = 86400
    max_bytes: int = 65536
    api_keys: dict = field(default_factory=dict, repr=False)  # sha256(key) -> existing user id
    provider_only: bool = False

    def reload_api_keys(self):
        self.api_keys = load_api_keys()

    @classmethod
    def from_env(cls):
        mode = os.environ.get("GT_MODE")
        if mode not in {"development", "provider-only"}:
            raise RuntimeError("Set GT_MODE to development or provider-only")
        result = cls(
            database_url=os.environ["GT_DATABASE_URL"],
            s3_access_key=os.environ["GT_S3_ACCESS_KEY"],
            s3_secret_key=os.environ["GT_S3_SECRET_KEY"],
            s3_endpoint=os.environ.get("GT_S3_ENDPOINT", "http://127.0.0.1:8333"),
            ray_endpoint=os.environ.get("GT_RAY_ENDPOINT", "http://127.0.0.1:8265"),
            provider_only=mode == "provider-only",
        )
        result.api_keys = load_api_keys()
        for value in (result.s3_endpoint, result.ray_endpoint):
            if urlsplit(value).hostname not in {"127.0.0.1", "localhost", "::1"}:
                raise RuntimeError("This development build requires loopback service endpoints")
        if urlsplit(result.database_url).hostname not in {"127.0.0.1", "localhost", "::1"}:
            raise RuntimeError("This development build requires a loopback database")
        return result
