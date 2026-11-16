# Developer quickstart

GreenTokens runs approved CPU pipelines on a local Ray worker. Start with one real linear-regression training run, then inspect the job and download its model. This is not yet a service for arbitrary Python training scripts, GPUs, or remote cloud accounts.

## Prerequisites

- Python 3.11+ for the client (tested on 3.12.10).
- The backend running on this computer at `http://127.0.0.1:8000`. Follow [local development](local-development.md); the SDK does not provision services.
- The optional dashboard at `http://127.0.0.1:3000`.

## Run the client from source

SDK packaging is pending approval of the setuptools build dependency. No PyPI package has been published. Until packaging is enabled, run these commands from the repository root in PowerShell:

```powershell
$env:PYTHONPATH = "$PWD\sdk"
.\.venv\Scripts\python.exe -m greentokens check
.\.venv\Scripts\python.exe -m greentokens pipelines
.\.venv\Scripts\python.exe -m greentokens init my-training
.\.venv\Scripts\python.exe -m greentokens explain my-training/training.toml
.\.venv\Scripts\python.exe -m greentokens submit my-training/training.toml
```

On macOS/Linux, use `PYTHONPATH="$PWD/sdk" python -m greentokens ...`. The client uses only the Python standard library. Planned installation after packaging approval is `python -m pip install ./sdk`, exposing the `greentokens` command.

`init` creates a new directory and refuses to overwrite an existing one. It writes a nonsecret idempotency key, a TOML configuration, and a five-sample JSON dataset. Paths are relative to the pipeline file. `explain` reads the configuration but sends no data.

## Follow the job

Replace `JOB_ID` with the returned ID:

```powershell
.\.venv\Scripts\python.exe -m greentokens status JOB_ID
.\.venv\Scripts\python.exe -m greentokens wait JOB_ID
.\.venv\Scripts\python.exe -m greentokens logs JOB_ID
.\.venv\Scripts\python.exe -m greentokens result JOB_ID --output model.json
```

The sample produces slope `2`, intercept `1`, and training mean-squared error `0`. Predict with `y = slope * x + intercept`. This metric measures the training set, not held-out accuracy. The downloaded file includes job/attempt IDs and model parameters under `result`. Downloads refuse to overwrite existing files.

The CLI prints a dashboard URL. Select **Settings > Live** and the same identity (`alice` by default) before viewing it. The Jobs page also accepts a pasted job ID. Browser-local recent history does not automatically include CLI submissions.

For cancellation: `python -m greentokens cancel JOB_ID`. A request is not confirmation; check status. Logs are collected after execution finishes. A timed-out wait does not cancel the job.

## Use Python

With `sdk` on PYTHONPATH (or the package installed once available):

```python
from greentokens import Client
from uuid import uuid4

client = Client(user="alice")
client.check()
key = str(uuid4())  # retain this key for an uncertain retry
data = {"x": [0, 1, 2, 3, 4], "y": [1, 3, 5, 7, 9]}
job = client.submit("linear_regression_v1", parameters=data, idempotency_key=key)
status = client.wait(job["job_id"])
if status["status"] == "SUCCEEDED":
    model = client.result(job["job_id"])["result"]
    prediction = model["slope"] * 6 + model["intercept"]  # 13
```

For an uploaded dataset, first call `artifact = client.upload(data)`, then submit with `input_artifact_id=artifact["artifact_id"]` instead of `parameters`. Preserve both the artifact ID and submission key for retries; uploading again creates another artifact.

## Data and database access

| Stage | Location and access |
| --- | --- |
| Original dataset | Your local JSON file; the client reads it on submit |
| Inline submission | Dataset copied through FastAPI into the MySQL job record |
| Upload alternative | Dataset stored in S3; job holds its artifact ID |
| Execution | Ray reads validated data and executes an approved CPU template |
| Outputs and logs | S3-compatible storage, with metadata/checksums in MySQL |
| Retrieval | API checks ownership, expiry, and integrity before returning bytes |

Developers never need internal MySQL/S3 credentials. No direct external database or bucket connector is implemented. The dataset limit is 64 KiB; training accepts 2–1,000 finite paired samples within ±1,000,000, with varying x. Artifact access expires after 24 hours, but physical cleanup is not guaranteed. Inline data remains in the database.

Keep the same pipeline, data, resources, and key for an uncertain retry. A new dataset or new run needs a new key. Reusing a key with changed input is rejected rather than silently changing a job.

## Local access only

`alice` and `bob` are development identity selectors, not credentials or real authentication. Put `--user bob` before a command to test the second organization. Both the backend and SDK reject remote service use in this MVP. Cloud-hosted clients require authenticated remote access and reachable workers in a later milestone.
