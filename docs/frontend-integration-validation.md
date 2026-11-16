# Frontend and backend integration — 14 November 2026

Integrated remote `main` through `f0f304e` into the existing backend checkout using a fast-forward. No new merge commit was created. Compatibility fixes remain uncommitted for review.

## Changes

- Restored Python virtual-environment/cache exclusions alongside frontend exclusions; excluded `.venv` from TypeScript and ESLint scans.
- Corrected root-level frontend startup instructions. Installed the existing npm lockfile using a checksum-verified portable Node.js 24.22.3 runtime under ignored `.tools/`.
- Restored proxy origin validation, including Next.js's internal localhost normalization when the browser uses 127.0.0.1.
- Increased the bounded job-request limit to 16 KiB to fit all 1,000 permitted signed integers and request metadata.
- Reset page state on identity, mode, and route changes. Abort pending submissions when leaving the page.
- Preserve submission keys and uploaded artifact IDs after uncertain submission responses; generate a different key when input changes. Keep admin submission disabled.

## Verification

- Backend: 15 tests passed (`python -m unittest discover -s tests -p test_core.py`).
- Frontend: 16 Vitest tests passed, including submission retry and proxy regression tests.
- ESLint, TypeScript checking, and Next.js production build passed.
- Running production frontend served dashboard, jobs, new-job, settings, and job-detail routes.
- `python -m scripts.verify_frontend` passed against the running real backend: inline and uploaded JSON submissions each returned result `10` through Next.js → FastAPI → Ray with MySQL and S3 storage.
- Live checks covered submission replay, cross-identity job/result/artifact isolation, completed-job cancellation behavior, usage, blocked worker routes, missing identity, and foreign-origin rejection.

The live check exercises HTTP routes, not browser clicks. Submission UI retry behavior is covered with React Testing Library in jsdom. Active-job cancellation and a full visual browser walkthrough were not tested in this integration pass. Existing development identity restrictions remain in place.

The toolchain reports non-failing Vite configuration and Starlette HTTPX deprecation warnings. Dependencies were not upgraded as part of these fixes.

## Reproduce

Start the backend using `python -m scripts.local_stack`. In another terminal at the repository root, run `npm.cmd ci`, `npm.cmd run build`, and `npm.cmd start` (Node.js must be on PATH; see README for this workspace's portable runtime). Then run:

```powershell
.\.venv\Scripts\python.exe -m scripts.verify_frontend
```

Open http://127.0.0.1:3000 and choose **Settings → Live** to use the actual backend. The default mock mode does not execute real jobs.
