"""GreenTokens local-development client. No runtime dependencies."""
import json
import time
from urllib.error import HTTPError, URLError
from urllib.parse import urlsplit
from urllib.request import Request, build_opener, ProxyHandler, HTTPRedirectHandler
from uuid import UUID


class GreenTokensError(Exception):
    pass


class NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


class Client:
    def __init__(self, endpoint="http://127.0.0.1:8000", user="alice"):
        url = urlsplit(endpoint)
        if (url.scheme != "http" or url.hostname not in {"127.0.0.1", "localhost", "::1"}
                or url.username or url.password or url.query or url.fragment or url.path not in {"", "/"}):
            raise ValueError("This MVP connects only to a local HTTP backend; remote authentication is not implemented")
        if user not in {"alice", "bob"}:
            raise ValueError("Choose local development identity alice or bob")
        self.endpoint, self.user = endpoint.rstrip("/"), user
        self.transport = build_opener(ProxyHandler({}), NoRedirect())

    def _call(self, method, path, body=None, raw=False):
        data = json.dumps(body, allow_nan=False).encode() if body is not None else None
        request = Request(self.endpoint + path, data=data, method=method,
                          headers={"X-Dev-User": self.user, "Content-Type": "application/json"})
        try:
            with self.transport.open(request, timeout=30) as response:
                content = response.read()
                return content if raw else json.loads(content)
        except HTTPError as exc:
            # Do not echo upstream bodies: they could contain sensitive data.
            raise GreenTokensError(f"API returned HTTP {exc.code}. Check identity, input, job status, and artifact expiry.") from None
        except (URLError, TimeoutError, OSError):
            raise GreenTokensError("Backend unreachable. For uncertain submissions, retry with the same idempotency key and input.") from None

    @staticmethod
    def _id(value):
        return str(UUID(value))

    def check(self):
        health = self._call("GET", "/health")
        self._call("GET", "/v1/usage")
        return health

    def submit(self, template_id, *, idempotency_key, parameters=None, input_artifact_id=None, requirements=None):
        if (parameters is None) == (input_artifact_id is None):
            raise ValueError("Supply exactly one of parameters or input_artifact_id")
        body = {"template_id": template_id, "idempotency_key": idempotency_key}
        body.update({"parameters": parameters} if parameters is not None else {"input_artifact_id": self._id(input_artifact_id)})
        if requirements is not None:
            body["requirements"] = requirements
        return self._call("POST", "/v1/jobs", body)

    def upload(self, data):
        return self._call("POST", "/v1/artifacts", data)

    def status(self, job_id):
        return self._call("GET", f"/v1/jobs/{self._id(job_id)}")

    def result(self, job_id):
        return self._call("GET", f"/v1/jobs/{self._id(job_id)}/result")

    def cancel(self, job_id):
        return self._call("POST", f"/v1/jobs/{self._id(job_id)}/cancel")

    def artifact(self, artifact_id):
        return self._call("GET", f"/v1/artifacts/{self._id(artifact_id)}", raw=True)

    def wait(self, job_id, timeout=180):
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            job = self.status(job_id)
            if job["status"] in {"SUCCEEDED", "FAILED", "CANCELLED"}:
                return job
            time.sleep(2)
        raise GreenTokensError("Wait timed out; the job may still be running. Use status with its job ID.")
