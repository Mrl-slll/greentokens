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
