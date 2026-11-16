import json
import os
from dataclasses import dataclass, field
from urllib.parse import urlsplit


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

    @classmethod
    def from_env(cls):
        # No production authentication provider exists yet: fail closed.
        if os.environ.get("GT_MODE") != "development":
            raise RuntimeError("Only explicit GT_MODE=development is supported; production is disabled")
        result = cls(
            database_url=os.environ["GT_DATABASE_URL"],
            s3_access_key=os.environ["GT_S3_ACCESS_KEY"],
            s3_secret_key=os.environ["GT_S3_SECRET_KEY"],
            s3_endpoint=os.environ.get("GT_S3_ENDPOINT", "http://127.0.0.1:8333"),
            ray_endpoint=os.environ.get("GT_RAY_ENDPOINT", "http://127.0.0.1:8265"),
        )
        result.api_keys = json.loads(os.environ.get("GT_API_KEYS", "{}"))
        for value in (result.s3_endpoint, result.ray_endpoint):
            if urlsplit(value).hostname not in {"127.0.0.1", "localhost", "::1"}:
                raise RuntimeError("This development build requires loopback service endpoints")
        if urlsplit(result.database_url).hostname not in {"127.0.0.1", "localhost", "::1"}:
            raise RuntimeError("This development build requires a loopback database")
        return result
