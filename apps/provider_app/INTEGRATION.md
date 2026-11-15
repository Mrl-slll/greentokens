# Provider app ↔ GreenTokens Core: integration requirements

Audience: GreenTokens core team. The provider app is built and installable; everything below is what it needs from Core to stop being a demo. Checked against the repository on 14 November 2026.

## What exists today

| Capability | In Core today | Provider app today |
|---|---|---|
| Worker agent on provider PC | None. The only worker row is the local Ray node registered by the heartbeat in `scripts/local_stack.py` | Mock service |
| Hardware discovery | None outside Ray resource totals | App reads CPU/RAM/GPU/OS itself (read-only CIM script) |
| Pause | `Worker.paused` column; dispatcher already skips paused workers (`core/jobs/dispatcher.py`) | Simulated |
| Provider identity / pairing | None (`X-Dev-User` development stub only) | Simulated sign-in |
| Provider job history / usage | None (`/v1/usage` and jobs are customer-org scoped; `/v1/workers` admin-only) | Simulated |
| Reachability from another PC | API binds 127.0.0.1 only | Shows "Demo mode: not connected" |

## What Core needs to provide

Each item maps to a method of `src/services/ProviderService.ts`. When an item exists, implement that method in a `liveProviderService.ts` and switch `App.tsx` to it; the screens don't change.

1. **Worker agent (core-owned) with a narrow local interface**, e.g. an HTTP server on `127.0.0.1` authenticated with a per-install token the installer writes to the user profile. No shell or arbitrary-command endpoints.
   - `GET /status` → `{ participation: "paused"|"active", connected: bool, current_job: {id, name, started_at} | null }` → `getActivity()`
   - `POST /pause`, `POST /resume` → confirmed state, only after the agent has stopped/started accepting work → `pause()`, `start()`
   - `PUT /limits` `{ cpu_percent, ram_gb, gpu_enabled }` → `{ enforced: bool }` → `savePreferences()`
   - Optionally `GET /hardware` to replace the app's own detection.
2. **Device pairing and provider identity:** a pairing flow (e.g. a one-time code shown in the app and confirmed in a browser) that issues the agent a device credential. The app should never handle passwords or long-lived tokens itself → `signIn()`, `signOut()`.
3. **Backend provider APIs** (provider-scoped, not customer-org scoped):
   - `POST /v1/provider/devices/{id}/pause|resume` writing `Worker.paused` (the dispatcher already honours it)
   - `GET /v1/provider/devices/{id}/jobs` (recent jobs, durations, outcome) and `/usage` (total compute time)
   - Earnings remain "Unavailable during pilot" until a pricing/payout design exists.
4. **Pause semantics decision:** does Pause only stop *new* jobs, or also stop the active job? The app currently shows "No new jobs will be accepted" and records an in-flight demo job as "Stopped by pause".
5. **Limit enforcement:** map CPU %/RAM GB/GPU to Ray node resources (e.g. `--num-cpus`, `--memory`, `--num-gpus`) when the agent starts its Ray worker. Until enforced, the app labels limits "Not enforced yet".
6. **Network endpoint:** a public, TLS, authenticated Core endpoint for agents (the API is loopback-only today), plus agent packaging (Python/Ray runtime) that the installer can bundle or download with consent.

## Rules the app already follows (keep them when going live)

- Opens **Paused** every launch; participation is never persisted.
- "Available for jobs" appears only after `start()` resolves; a failed or unconfirmed pause never shows "Paused".
- No start-on-login, no background sharing, no shell access from the UI, minimal Tauri capabilities (`core:default` only).
- Demo/simulated values are labeled in the UI; earnings are never invented.
