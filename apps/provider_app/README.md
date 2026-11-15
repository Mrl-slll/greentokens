# GreenTokens Provider (Windows desktop app, demo)

Works like a VPN app: **install it, open it, press the big power button.**

**Status: demo.** Hardware detection is real. Connecting, limits and activity are **simulated** (labeled in the UI) because the GreenTokens worker agent and provider APIs don't exist yet. See [INTEGRATION.md](INTEGRATION.md).

## Download (Windows 10/11)

**[Download GreenTokens-Provider-Setup.exe](https://github.com/Mrl-slll/greentokens/releases/download/provider-v0.1.0/GreenTokens-Provider-Setup.exe)**

1. Open the file. If Windows says *"Windows protected your PC"*, click **More info → Run anyway** (the demo build isn't code-signed yet).
2. Open **GreenTokens Provider** from the Start menu and press the power button. The first time, you'll be asked to agree once.

No administrator password, no account, no terminal. It never connects by itself, always opens disconnected, and doesn't start with Windows. To remove it: **Settings → Apps → Installed apps → GreenTokens Provider → Uninstall**.

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
