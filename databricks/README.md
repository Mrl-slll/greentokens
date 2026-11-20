# Databricks: remote customer notebooks

[System guide](../README.md) · [Local SDK](../sdk/README.md)

Databricks is an optional **customer interface**. The notebooks submit jobs and display results; provider/Ray computers do the training. Databricks is not required for provider login, the local dashboard, or the database.

## Components and rationale

| File | Function |
| --- | --- |
| `00_README.py` | Notebook-oriented introduction; some narrative reflects an earlier milestone |
| `01_Submit_Training_Job.py` | Reads widgets/secrets, submits once, prints/exits with job ID |
| `02_View_Results.py` | Retrieves status/results and formats computer/model metrics; optional workspace output |
| `greentokens_client.py` | HTTPS bearer adapter over the common SDK, plus pure result-summary helpers |

The adapter is a **transport specialization**: it reuses SDK operations but replaces local development headers with bearer authentication and requires a plain HTTPS origin. The base SDK's loopback restriction does not prevent this adapter from reaching the remote API. An old module comment saying backend bearer auth is unimplemented is stale; current `core/api/main.py` accepts configured bearer keys and provider sessions.

The notebooks expose sum, regression, development Ray BERT, and single-provider text fine-tuning. They do not make arbitrary training scripts runnable. Three independent text jobs on three providers are not one three-way distributed model.

## Setup boundaries

1. The operator supplies a reachable HTTPS API origin and provisions a customer credential through the existing account workflow.
2. Import the notebook folder **and make the sibling `sdk/greentokens` module available** in the workspace layout/runtime. Importing only these notebook files can fail because the adapter imports that SDK.
3. Configure the selected Databricks secret scope (default `greentokens`) with `url` and `token` through an approved secret-management workflow. Never put the token in notebook source/output.
4. Verify that this actual workspace can reach the API and use the secret scope; workspace policies are not established by local unit tests.
5. Run notebook 01, retain its request ID and job ID, then run notebook 02. Reuse the same request ID for an uncertain retry; an empty request ID generates a new submission.

Catalog/table writes and external-domain access depend on workspace permissions and product configuration. This guide does not assert a current Free Edition entitlement or that a live workspace was validated during documentation work.

## Authentication and endpoint changes

Use a customer key, not a provider session, for submissions: provider-role users are denied job submission. The URL is loaded from a secret at runtime, unlike the desktop app's compiled URL. A tunnel change can therefore require updating the notebook configuration independently of rebuilding the provider app.

The operator's `start_server.ps1` invokes `set_databricks_url.py` as a side effect. Do not run it merely to inspect local state without accounting for that external write.

## Validation and debugging

`tests/test_databricks_client.py` tests transport/formatting behavior with local test doubles. It does not establish workspace egress, secret scopes, Catalog permissions or actual remote training. Distinguish unreachable host from invalid credentials, no eligible provider and unfinished job state. Retain the job ID when reopening a notebook; the training job does not depend on keeping the submission notebook running.
