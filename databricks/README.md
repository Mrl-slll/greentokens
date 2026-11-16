# GreenTokens + Databricks (optional customer workspace)

Status: **scaffold, untested in a real workspace.** Everything marked *unverified* must be tested first.

| Item | State |
|---|---|
| Notebooks `00`/`01`/`02`, `greentokens_client.py` | written; import into your workspace (see Setup) |
| Free Edition can reach GreenTokens | **unverified** (outbound limited to an allowlist) |
| Backend bearer-token auth + public HTTPS | **not built**; today the API is loopback-only with a dev identity |
| Table in Catalog | **unverified** on Free Edition |
| TrOCR preset | **not available**; backend has only `linear_regression_v1` and `sum_numbers_v1` |

## Setup
1. Import this folder into the workspace (Workspace > Import, or `databricks workspace import-dir databricks /Workspace/Users/<you>/GreenTokens`).
2. Create secret scope `greentokens` with keys `url` (https endpoint) and `token`. Free Edition may not allow secret scopes: unverified.
3. Run `01_Submit_Training_Job`, copy the printed `job_id`, later run `02_View_Results`.

## Costs and limits
Free Edition is non-commercial with serverless-only compute and daily quotas. Do not assume production use is free.
The notebooks only submit and fetch, so they use little compute and never wait for training.

## Next (see the approved plan)
Egress probe, then bearer API keys plus a tunnel to port 8000 only (Path A), or a reverse bridge through a Catalog table (Path B).
