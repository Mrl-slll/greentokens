<<<<<<< HEAD
# Provider desktop application

[System guide](../../README.md) · [Backend](../../core/README.md) · [Operations](../../scripts/README.md)

## What this component does

This is the application a hardware owner installs to lend computing capacity. The owner creates a provider account, signs in, approves local setup and presses Connect. The app starts a Python worker that connects **outward** to the operator's API, asks for work and returns results. Closing the app stops sharing.

The current worker path does not create or join a Ray cluster. Earlier group-code helpers still exist in the Python source for old experiments, but the current Rust bridge exposes setup/capabilities and independent worker start/stop/state, not general Ray host/join actions.

## Architecture and technology choices

```text
React UI → Tauri IPC → Rust native bridge → private Python worker
   │                                            │
   └─ HTTPS signup/login/logout                 └─ HTTPS heartbeat/work/lease/artifacts
                         ↓
                    Operator API
```

- **React/TypeScript** builds the interface and defines service/state types.
- **Vite** serves the development preview and compiles frontend assets. It is a build tool, not the worker server.
- **Tauri** packages the UI in a native webview. Its IPC bridge lets JavaScript call explicitly registered Rust functions.
- **Rust** manages native process lifecycle, hardware/usage probes and runtime paths. It validates arguments before spawning work.
- **uv** provisions a private Python 3.12.16 runtime in the app's data directory. ML packages are installed after setup consent. This avoids requiring every provider to manually install a development environment.
- **Python/PyTorch** runs the approved calculation/training workload. GPU drivers remain a separate machine prerequisite.

The native bridge narrows available actions; it does not turn approved subprocesses into an OS security sandbox.

## Source map

| File | Responsibility |
| --- | --- |
| `src/App.tsx`, `src/screens/` | Account flow and Home/Hardware/Activity/Settings UI |
| `src/hooks/useProvider.tsx` | Connection/setup state and lifecycle |
| `src/services/providerAuth.ts` | Signup/login/logout and in-memory session |
| `src/services/liveProviderService.ts` | Calls Tauri worker commands and maps state |
| `src/services/mockProviderService.ts` | Simulated browser-preview behavior |
| `src/services/hardware.ts`, `usage.ts` | Hardware/usage adapters |
| `src-tauri/src/main.rs` | Registers allowed native commands and stops worker on window destruction |
| `src-tauri/src/agent.rs` | Private runtime, argument validation, worker process handling |
| `src-tauri/src/hardware.rs`, `usage.rs` | Native hardware/usage collection |
| `src-tauri/agent/gt_agent.py` | Setup, capabilities, package download, execution and retry loop; also contains historical group helpers |
| `provider-server.json`, `vite.config.ts` | API origin compiled as `__PROVIDER_SERVER__` |
| `src-tauri/tauri.conf.json` | Native app settings and frontend connection policy |
| `scripts/configure-server.mjs` | Validates an origin and updates endpoint/CSP together |

## Authentication and persistence

Passwords and sessions stay in memory on the client. The server stores salted scrypt password hashes and session-token hashes. Sessions expire after 24 hours and are bound to a device ID. Re-signing in on the same device replaces that account's prior session there. Sign-out stops the worker and attempts server revocation.

Account credentials are not group codes. Other computers sign in independently. Remembered hardware setup/preferences do not imply persistent authentication: reopening the app requires sign-in. An offline logout cannot guarantee immediate server-side revocation, though expiry remains in effect.

The Rust bridge passes credentials to Python through environment variables, not command-line arguments. Do not print worker environments or export them into diagnostic files.

## Worker protocol

1. Report capabilities and online/paused status with a heartbeat.
2. Long-poll for a job (normally requesting a 20-second wait).
3. Download the allowlisted workload package and verify its SHA-256.
4. Run its fixed entry point in a subprocess; collect progress and enforce timeout/stop handling.
5. Renew the attempt lease while running; respect the server's continue/cancel response.
6. Upload output/log/model artifacts, report completion and clean job files.

Transient network exceptions cause reconnect backoff from 2 to 60 seconds while the worker remains enabled. Friendly/authentication failures stop with an error. A long network outage can kill a running workload and allow its server lease to expire. Reconnection is not guaranteed continuation of an interrupted job.

Provider-reported hardware is not attestation. A GPU contributes usable capacity only if PyTorch reports CUDA availability. Current training setup selects a supported PyTorch/CUDA package; it does not install or upgrade NVIDIA drivers.

## Endpoint and loopback explained

The installed frontend calls the origin compiled from `provider-server.json`. `127.0.0.1:1420` in the Vite/Tauri dev configuration is the local UI preview, not the remote API. `http://ipc.localhost` is native IPC policy, not the operator server. The backend's `127.0.0.1:8000` is reachable by the tunnel connector on the operator PC.

For remote machines, the compiled API origin must be public HTTPS. Development on the operator PC can use `http://127.0.0.1:8000`. The configurator updates both the URL and Tauri `connect-src` policy:

```powershell
# From apps/provider_app; replace this example with the real, configured origin.
node scripts/configure-server.mjs https://api.example.com
```

That changes source only. Rebuild and distribute the installer separately. CI may override the origin with `GT_PROVIDER_SERVER`. An existing installer does not learn a new temporary tunnel address by itself.

## Development and builds

From this directory, with Node 24 available:

```powershell
npm.cmd ci
npm.cmd run dev
npm.cmd test
npm.cmd run typecheck
npm.cmd run build
```

The browser preview is simulated; use made-up credentials. Native development additionally needs Rust and platform build tools:

```powershell
npm.cmd run tauri dev
npm.cmd run tauri build
```

A full distributable also needs bundled resources and platform configuration supplied by the release workflow. Do not assume a bare local build reproduces the published installer. See [delivery](../../.github/README.md) and [Windows distribution](../../docs/windows-distribution.md). Version 0.3.1 is an unsigned test release, not proof of production signing/notarization.

## Verification and extension

Use `tests/` for frontend flows and `src-tauri/agent/test_gt_agent.py` for worker behavior. Then test a real installed app on a second computer: login, heartbeat, one approved job, pause/stop, network interruption and sign-out. Browser tests cannot validate native packaging or remote connectivity.

For a new workload, coordinate backend schemas/package mapping and Python dependencies. For a new UI capability, coordinate service interface, mock and live adapters, native command if needed, and lifecycle tests. Do not expose arbitrary shell commands through IPC.
=======
# GreenTokens Provider (Windows desktop app, demo)

A beginner-friendly app that lets a PC owner choose whether and how much of their computer to share with GreenTokens: **Sign in → Check hardware → Choose limits → Start/Pause**.

**Status: demo.** Hardware detection is real. Sign-in, Start/Pause, limits enforcement and activity are **simulated** (clearly labeled in the UI) because the GreenTokens worker agent and provider APIs don't exist yet. See [INTEGRATION.md](INTEGRATION.md).

## Download and install (any Windows 10/11 PC)

1. Download **[GreenTokens-Provider-Setup.exe](https://github.com/Mrl-slll/greentokens/releases/download/provider-v0.1.0/GreenTokens-Provider-Setup.exe)**.
2. Run it. The build is not code-signed yet, so Windows may show *"Windows protected your PC"*. Choose **More info → Run anyway**.
3. It installs for your user account only (no administrator rights) and adds **GreenTokens Provider** to the Start menu.
4. Uninstall any time: **Settings → Apps → Installed apps → GreenTokens Provider → Uninstall**.

The app never starts at login and never starts sharing by itself; it always opens **Paused**.

## How it's built

| Part | Tech |
|---|---|
| Desktop shell + installer | Tauri 2 (NSIS, per-user install) |
| UI | React 19, TypeScript, Tailwind CSS 4, lucide-react, Vite |
| Hardware detection | One Rust command (`detect_hardware`) running a fixed, bundled, read-only PowerShell/CIM script (`src-tauri/src/detect_hardware.ps1`) |
| Tests | Vitest + Testing Library (CI); Rust unit test for the command encoder (`cargo test`, local) |

```
src/services/ProviderService.ts      interface the UI uses; swap the mock for a live client here
src/services/mockProviderService.ts  MOCK implementation (in-memory, no network)
src/services/hardware.ts             Tauri hardware call + normalisation
src/hooks/useProvider.tsx            app state; participation is never persisted (always opens Paused)
src/screens/                         Welcome, Hardware, Control, Activity, Settings
src-tauri/                           Rust shell, config, icons
```

## Develop

Needs Node 24. From this folder:

```powershell
npm ci
npm run dev        # browser preview at http://127.0.0.1:1420 (hardware shows "desktop app only")
npm test
npm run typecheck
```

Building the desktop app locally also needs Rust and the Microsoft C++ Build Tools (`npm run tauri dev` / `npm run tauri build`). Without them, use the GitHub Actions build.

## Release build (GitHub Actions)

`.github/workflows/provider-app.yml` runs on every push that touches `apps/provider_app/**`: it type-checks, runs the tests, builds the NSIS installer on `windows-latest`, uploads it as a run artifact, and (on `provider-app` or `main`) republishes the `provider-v0.1.0` pre-release with `GreenTokens-Provider-Setup.exe`.

## Before a public release

- **Code signing:** sign the installer and executable with an OV/EV code-signing certificate (configure `bundle.windows.certificateThumbprint`/`signCommand`) so SmartScreen trusts it.
- **Updates:** add `tauri-plugin-updater` with a signing key pair; keep the private key in CI secrets only.
- **Worker runtime:** this installer contains only the UI. Installing and configuring the GreenTokens worker agent is a separate, core-owned packaging step (see INTEGRATION.md).
>>>>>>> d5fa911 (Add GreenTokens Provider Windows desktop app (demo))
