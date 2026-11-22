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


def summarize(job, result):
    """Turn a job status + result into (summary_row, computer_rows) for display and Catalog tables.

    Pure function (no Spark), so it is unit-tested. Numbers stay numbers; missing values are None.
    """
    metrics = (result or {}).get("result") if isinstance((result or {}).get("result"), dict) else {}
    computers = metrics.get("computers", [])
    model = next((a for a in job.get("artifacts", []) if a.get("kind") == "model"), None)
    before, after = metrics.get("eval_before") or {}, metrics.get("eval_after") or {}
    summary = {
        "job_id": job["job_id"], "status": job["status"], "template_id": job["template_id"],
        "created_at": str(job.get("created_at")), "updated_at": str(job.get("updated_at")),
        "error_code": job.get("error_code"),
        "computers": len(computers) or None,
        "computer_names": ", ".join(c["host"] for c in computers) or None,
        "accuracy_before": before.get("accuracy"), "accuracy_after": after.get("accuracy"),
        "first_loss": metrics.get("first_loss"), "last_loss": metrics.get("last_loss"),
        "wall_seconds": metrics.get("wall_seconds"), "model_name": metrics.get("model"), "device": metrics.get("device"),
        "gpu": metrics.get("gpu"),
        "model_mb": round(model["size_bytes"] / 1e6, 2) if model else None,
        "model_sha256": model["sha256"] if model else None,
        "result_json": json.dumps(result) if result is not None else None,
    }
    rows = [{"job_id": job["job_id"], "rank": c.get("rank"), "computer": c.get("host"), "os": c.get("os"),
             "python": c.get("python"), "ray": c.get("ray"), "gpu": c.get("gpu"), "device": c.get("device"),
             "train_seconds": c.get("train_seconds"),
             "sync_seconds": c.get("sync_seconds"), "total_seconds": c.get("seconds"),
             "last_loss": c.get("last_loss")} for c in computers]
    return summary, rows


def model_artifact_id(job):
    return next((a["artifact_id"] for a in job.get("artifacts", []) if a.get("kind") == "model"), None)
