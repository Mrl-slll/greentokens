# GreenTokens Provider (Windows desktop app, demo)

Works like a VPN app: **install it, join a group, press the big power button.**

**Status: preview.** Groups are real: one computer clicks **Start a group** and shares a code; others click **Join a group** and paste it. The power button then really starts or joins a private [Ray](https://www.ray.io/) cluster on the local network (`ray start` / `ray stop`). GreenTokens jobs aren't sent to groups yet; the group is ready for your own Ray workloads (e.g. multi-PC training). In the browser preview and in tests, a clearly labeled mock is used instead.

## Download (Windows 10/11)

**[Download GreenTokens-Provider-Setup.exe](https://github.com/Mrl-slll/greentokens/releases/download/provider-v0.1.0/GreenTokens-Provider-Setup.exe)**

1. Install on each computer. If Windows says *"Windows protected your PC"*, click **More info → Run anyway**.
2. Computer 1: **Start a group** → **Copy** the code. Other computers: **Join a group** → paste it.
3. Press the power button on each. The first time, the app downloads a private Python + Ray (about 150 MB) and Windows asks once to allow it on your **Private** network.

It never connects by itself, always opens disconnected, closing the app disconnects, and it doesn't start with Windows. To remove it: **Settings → Apps → Installed apps → GreenTokens Provider → Uninstall**.

## How groups work

| Piece | Detail |
|---|---|
| Group code | `GT1-<leader LAN IP>-<32-hex token>`; the token is Ray's access token (`RAY_AUTH_MODE=token`). Only private LAN addresses are accepted. |
| Runtime | First use: bundled `uv` (pinned, checksum-verified in CI) creates `%LOCALAPPDATA%i.greentokens.provideruntime` with Python 3.12 and `ray[default]==2.60.0`, so every computer matches. |
| Agent | `src-tauri/agent/gt_agent.py`: fixed actions `check`, `firewall`, `host`, `join`, `stop`, `status`; validated arguments; one JSON line out. The Rust command `agent` only accepts those actions. |
| Ports / firewall | Fixed ports TCP 6379-6386 and 10002-10101; one elevated rule `GreenTokens Provider (Ray)` on the **Private** profile only. Dashboard stays on 127.0.0.1. |
| Limits | Processor share → `ray start --num-cpus`. Memory isn't enforced (Ray 2.60's CLI has no memory flag). |
| Caveats | Ray multi-node on Windows is **experimental** (`RAY_ENABLE_WINDOWS_OR_OSX_CLUSTER=1`). The leader can run code on members: only join trusted groups. |

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
src/screens/                         Home (one-button connect + consent prompt), Hardware, Activity, Settings
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
