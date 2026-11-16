"""Thin Databricks-side wrapper over the existing GreenTokens SDK Client.

It only adds a bearer token and an https endpoint. It has no scheduler and no polling loop.
NOTE (unverified): the backend does not accept bearer tokens yet; see README.md, Path A step 1.
"""
import json
import sys
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.parse import urlsplit
from urllib.request import Request

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "sdk"))
from greentokens import Client, GreenTokensError  # noqa: E402


class DatabricksClient(Client):
    def __init__(self, endpoint, token):
        url = urlsplit(endpoint)
        if (url.scheme != "https" or not url.hostname or url.username or url.password
                or url.query or url.fragment or url.path not in {"", "/"}):
            raise ValueError("Endpoint must be a plain https://host URL")
        if not token:
            raise ValueError("Missing API token; read it from a Databricks secret, never from notebook text")
        Client.__init__(self, "http://127.0.0.1:8000")  # reuse the opener (no redirects, no proxies)
        self.endpoint, self.user, self._token = endpoint.rstrip("/"), "bearer", token

    def _call(self, method, path, body=None, raw=False):
        data = json.dumps(body, allow_nan=False).encode() if body is not None else None
        request = Request(self.endpoint + path, data=data, method=method,
                          headers={"Authorization": f"Bearer {self._token}", "Content-Type": "application/json"})
        try:
            with self.transport.open(request, timeout=30) as response:
                content = response.read()
                return content if raw else json.loads(content)
        except HTTPError as exc:
            raise GreenTokensError(f"API returned HTTP {exc.code}. Check token, input and job ID.") from None
        except (URLError, TimeoutError, OSError):
            raise GreenTokensError("GreenTokens unreachable (or blocked by Free Edition egress rules). "
                                   "Retry with the same idempotency key.") from None
