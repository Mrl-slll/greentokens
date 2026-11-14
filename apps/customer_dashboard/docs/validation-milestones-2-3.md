# Milestones 2–3 validation — November 14, 2026

Environment: Windows 11, Python 3.12.10, Ray 2.60.0, actual MySQL 8.4.13,
SeaweedFS 4.53, Docker Compose 5.6.1. Dependencies are installed in `.venv`.
The user approved the dependency list, dedicated MySQL container, generated local
credentials, and SeaweedFS in place of MinIO.

| Check | Actual result |
| --- | --- |
| Initial MySQL Alembic migration | Applied revision `0001` successfully |
| `alembic command.check` against MySQL | `No new upgrade operations detected.` |
| `unittest discover -s tests -p test_core.py -v` | 15 tests passed in 1.713s |
| Original `test_ray_smoke.py` after dependency changes | 1 test passed in 14.465s |
| `compileall -q core scripts tests` | Passed |
| `pip check` | `No broken requirements found.` |
| Initial real pipeline acceptance | Inline and stored-file jobs returned 10; API restarts and tenant isolation passed |
| Expanded real pipeline acceptance | Concurrent idempotency, dispatcher/API restart, actual S3 corruption/expiry checks all passed |

Latest real acceptance output:

```text
PASS durable inline job: d52e747e-2373-4936-a39b-78c282005cbf; result=10; one attempt/usage record; tenant isolation
PASS durable file job: 2f18d714-f90d-4833-ba47-b6ba8cf030ba; result=10; one attempt/usage record; tenant isolation
PASS API restart retains MySQL records and verified S3 outputs
PASS actual S3 integrity rejection and artifact expiry
MILESTONES 2-3 ACCEPTANCE PASSED (local development identity stub)
```

The real harness also checks foreign-organization denials for input references,
job/status/result/cancel access, and output/log retrieval; admin-only worker
inventory; unauthenticated request rejection; one durable usage row per attempt;
and one job under concurrent identical requests. Unit tests exercise queued and
running cancellation, execution failure/loss, no reexecution after uncertain
submission, runtime expiry, stale workers, missing/corrupt outputs, request
validation, production-mode rejection, and duplicate reconciliation.

Observed API/Ray TCP listeners were bound to `127.0.0.1` while the full stack ran.
Docker reports only `127.0.0.1:3307` and `127.0.0.1:8333` as published service
ports. After tests, no Ray GCS/raylet processes or API/Ray Jobs listeners remained.
The two dedicated containers remained running, and four successful test jobs
were retained in MySQL with persistent S3 artifacts.

## Failures and limitations encountered

The first full stack attempt exited during startup with `ValueError`; the initial
sanitized diagnostic did not capture its message. A retry with improved startup
diagnostics succeeded, followed by a second successful expanded acceptance run.
The first failure's precise cause is unverified; it is not being counted as a
successful run or a proven fix.

Starlette emitted a deprecation warning for its HTTPX-backed TestClient. All
tests passed with the approved HTTPX 0.28.1; no replacement dependency was added.
No Ruff run was performed; Python compilation and the tests above were executed.

These tests prove the local development milestones, not production readiness,
real account authentication, hostile-code isolation, multi-node execution,
database/storage host recovery, backup restoration, or billing accuracy. API and
dispatcher processes were restarted; MySQL and S3 containers were not restarted
during these acceptance runs.
