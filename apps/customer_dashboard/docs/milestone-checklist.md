# Milestone checklist

- [x] 0: inspect runtime and document setup/dependencies.
- [x] 1: eight deterministic CPU tasks; repeatable local smoke and integration test.
- [x] 2: approved-job API, MySQL/Alembic, durable Ray Jobs submission IDs,
  dispatcher/reconciler, status/result 10, records retained across API restart.
- [x] 3: persistent S3-compatible SeaweedFS, authorized input files and outputs,
  checksums/sizes/expiry, organization-scoped retrieval across API restart.
- [ ] 4: four explicitly authorized trusted machines and robust worker lifecycle.
- [ ] 5: additional approved data/inference templates and validated usage measurement.
- [ ] 6: real customer authentication/dashboard and later provider UX.
- [ ] 7: separate coordinated training experiment.

Completion of 2–3 refers to the local development acceptance criteria. The
permanent MVP's real authentication, deployment isolation, and operational
hardening remain unfinished; the development identity stub is not a substitute.
