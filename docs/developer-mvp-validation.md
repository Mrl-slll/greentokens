> Scope: historical plan, handoff, or validation evidence. Feature statements and test results apply to its recorded stage, not the whole current system. Start with the [current developer guide](../README.md).

# Developer MVP validation — 14 November 2026

## Implemented

- Plain developer quickstart homepage and pipeline/data-flow reference.
- Source Python SDK and CLI: init, check, pipelines, explain, submit, status, wait, logs, result, and cancel.
- TOML pipeline configuration and JSON dataset example; no runtime dependencies in the SDK.
- Approved `linear_regression_v1` CPU pipeline using Python's `statistics.linear_regression`, integrated into the existing validation, MySQL, Ray, and S3 lifecycle.
- Job lookup by ID, model/result download, artifact/log inspection, input-source and resource details.
- Existing sum connection test retained.

## Passed

- 18 backend tests, including training schema, template/input matching, cross-organization uploaded-data access, and fitted-model assertions.
- 4 SDK tests, including source init/explain, non-overwriting output, local-only connection configuration, and stable submission keys.
- 17 frontend tests, including model rendering, result download link, log retrieval, and earlier submission/proxy regressions.
- ESLint, TypeScript (including production-build type checking), and Next.js production build.
- `python -m scripts.verify_developer`: real source CLI init/explain/submit, Ray completion, model download, operational logs, retry deduplication, and isolation. Expected slope=2, intercept=1, training MSE=0 verified. A second run used an uploaded S3 dataset and produced the same model.
- `python -m scripts.verify_frontend`: original inline and file sum jobs still complete with result=10 through the frontend proxy, with artifact and identity checks.
- HTTP checks for quickstart/pipelines pages and actual training result through the Next.js proxy. UI model/log behavior verified in jsdom; no full visual browser walkthrough performed.

Backend runs on port 8000; frontend on port 3000. Real workloads used the existing local MySQL, SeaweedFS, and Ray services. No database migration was needed.

## Remaining

Installable SDK packaging awaits approval for setuptools as required by AGENTS.md. A concrete package specification is in [SDK packaging proposal](sdk-packaging-proposal.md). Source-run commands are available now. No package has been published, and clean-environment pip installation is not yet tested.

The fitted model is a small single-feature CPU example, not a general training-script service or distributed/GPU training. Remote authentication, external dataset connections, and cloud provisioning remain future work. No checkpoint stream or held-out evaluation is implemented. The existing development identities and artifact-expiry limitations remain unchanged.

## Reuse

Reused the existing job lifecycle and storage components. Python 3.12 standard-library [linear regression](https://docs.python.org/3.12/library/statistics.html#statistics.linear_regression) supplies the fitting operation; TOML, argparse, urllib, and JSON provide the client tooling. No application dependency was added.
