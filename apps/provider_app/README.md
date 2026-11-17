# GreenTokens Provider

Install the desktop app, **create an account or sign in**, then press **Connect** and approve setup. No invite or group code is needed. The installed app runs approved jobs through an outbound connection to the operator's server. The browser preview is explicitly simulated.

See [the owner guide](../../docs/provider-guide.md) and [operator checklist](../../docs/operator-checklist.md). Version 0.3.1 is prepared as an unsigned test release. See [Windows distribution](../../docs/windows-distribution.md) for the signed-release requirements.

## Develop

Use Node 24 from this folder:

```powershell
npm run dev
npm test
npm run typecheck
npm run build
```

Browser preview: http://127.0.0.1:1420. Use made-up credentials in the simulated preview. Desktop development additionally requires Rust and the platform build tools (`npm run tauri dev`).

## Server configuration

The backend runs on the operator's PC. The app embeds its public HTTPS tunnel address at build time; providers never type it:

```powershell
node scripts/configure-server.mjs https://YOUR-CURRENT-TUNNEL.trycloudflare.com
npm run tauri build
```

The script updates `provider-server.json` and Tauri's exact `connect-src` allowlist together. For development on this PC only, `http://127.0.0.1:8000` is also accepted. CI rejects plain HTTP. GitHub Actions optionally uses repository variable `GT_PROVIDER_SERVER`; otherwise it uses `provider-server.json`.

A changing quick-tunnel address requires rebuilding the installer. Keep the tunnel running for the pilot. A permanent hostname can still point to this same PC later.

## Accounts

- React/TypeScript UI calls FastAPI's provider signup/login/logout endpoints over HTTPS.
- The backend stores salted scrypt password hashes and hashes of device-bound, 24-hour sessions in MySQL. Signup always creates a provider, never a customer or administrator.
- Passwords and session tokens stay in memory. Old localStorage invite credentials are discarded during upgrade. Reopen the app and sign in again; the sharing consent and hardware setup remain remembered.
- Signing out stops the worker and revokes that session. An offline sign-out reports that server-side expiry is still pending.
- Tauri passes the session to the Python worker in its environment, never its command-line arguments. The worker polls for approved work and returns results. No Ray cluster is created on provider computers.
- Training remains one job per provider; this change does not implement distributed model training or hostile-provider isolation.

## Build and release

`.github/workflows/provider-app.yml` tests and builds Windows/Mac installers. Tag `provider-v0.3.1` publishes an explicitly labeled unsigned preview after both platform builds and checksum checks succeed. Other `provider-v*` tags still require verified Windows signing. Branch builds remain development artifacts. No commit, push or release is required to run local tests. Password recovery and persistent keychain sign-in are future work.
