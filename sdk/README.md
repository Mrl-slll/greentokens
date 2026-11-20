# Local Python SDK and command-line client

[System guide](../README.md) · [Step-by-step local quickstart](../docs/developer-quickstart.md)

An **SDK** wraps HTTP calls in language-level methods. A **CLI** exposes those operations as terminal commands. Here `greentokens/__init__.py` defines `Client`, `cli.py` parses commands/configuration, and `__main__.py` enables `python -m greentokens`.

The client uses Python's standard library rather than another HTTP dependency. It validates local endpoints/identities, rejects redirects and disables ambient proxies in its opener. This keeps the local onboarding client small and limits accidental credential forwarding. It is not the remote bearer-auth client; see [Databricks adapter](../databricks/README.md).

## Contract

`Client` provides `check`, `submit`, `upload`, `status`, `wait`, `cancel`, `result`, and `artifact`. `submit` forwards a template to backend validation; the TOML CLI deliberately exposes only sum and regression. The backend supports additional paths that the CLI does not model.

Constructor endpoints are loopback HTTP only, with `alice` or `bob` development identities. The error message about remote authentication describes this base client, not the whole backend. The separate remote adapter overrides transport and uses bearer credentials.

## Run from source

There is no published PyPI package or approved installable packaging here. From the repository root:

```powershell
$env:PYTHONPATH = "$PWD\sdk"
.\.venv\Scripts\python.exe -m greentokens check
.\.venv\Scripts\python.exe -m greentokens pipelines
.\.venv\Scripts\python.exe -m greentokens init new-training-example
.\.venv\Scripts\python.exe -m greentokens explain new-training-example/training.toml
.\.venv\Scripts\python.exe -m greentokens submit new-training-example/training.toml
```

`init` refuses to overwrite an existing directory. `explain` reads but does not submit. Dataset paths are relative to the TOML file, not whichever terminal directory happens to be active. Input is bounded JSON, not arbitrary Python source.

Use a returned ID in `status JOB_ID`, `wait JOB_ID`, `logs JOB_ID`, `cancel JOB_ID` and `result JOB_ID --output model.json`. A timed-out wait does not cancel the job. Saving a result refuses to overwrite an existing file.

## Python example

With `sdk` on `PYTHONPATH` and the local stack running:

```python
from uuid import uuid4
from greentokens import Client

client = Client(user="alice")
request_id = str(uuid4())  # retain for retries of this same submission
job = client.submit(
    "linear_regression_v1",
    parameters={"x": [0, 1, 2, 3], "y": [1, 3, 5, 7]},
    idempotency_key=request_id,
)
state = client.wait(job["job_id"])
if state["status"] == "SUCCEEDED":
    result = client.result(job["job_id"])
```

Idempotency means the same key and content refer to the same submission. Generating a new key after an uncertain timeout risks another job. Uploaded input is a separate artifact operation and is not deduplicated by the job key.

## Maintenance

Keep transport errors free of secrets and avoid reflecting upstream response bodies. `tests/test_sdk.py` tests the client and CLI without establishing remote deployment behavior. Preserve base-client limitations unless explicitly implementing a new authentication/endpoint contract.
