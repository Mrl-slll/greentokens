# GreenTokens Provider @VERSION@ — unsigned test release

This is an **unsigned preview** for testing on computers whose owners and security settings permit it. Windows will show **Publisher: Unknown**, and Edge or Windows may block the installer. Do not disable protection or override a managed-device policy. Azure identity verification and Windows code signing are still pending.

- **[Download Windows x64 installer](https://github.com/@REPO@/releases/download/@TAG@/GreenTokens-Provider-Setup.exe)** — Windows 10/11 x64
- **[Download Mac installer](https://github.com/@REPO@/releases/download/@TAG@/GreenTokens-Provider-macOS.dmg)** — Apple silicon and Intel; macOS 11+. This preview is not notarized.
- **[SHA256SUMS.txt](https://github.com/@REPO@/releases/download/@TAG@/SHA256SUMS.txt)**

## Install and connect

Download from this GitHub release, verify the SHA-256 checksum, and follow [the provider guide](https://github.com/@REPO@/blob/@TAG@/docs/provider-guide.md). In the app, create an account or sign in, then choose Connect and approve setup. The app stays signed in (kept in Windows Credential Manager or the macOS Keychain) until you sign out; your password is never saved. The app does not install GPU drivers.

In PowerShell, compare the complete output of this command with the Windows entry in SHA256SUMS.txt:

```powershell
Get-FileHash "$HOME\Downloads\GreenTokens-Provider-Setup.exe" -Algorithm SHA256
```

A matching checksum verifies the downloaded bytes; it does not establish publisher identity or safety. If a download or installation is blocked, check Edge Downloads (Ctrl+J) and Windows Security Protection history for the exact reason. Ask the device administrator about managed-device blocks.

This version connects to the GreenTokens server at its permanent address, so it does not need rebuilding when the operator's PC restarts. Each job runs on one provider computer. Password recovery is not yet available.

Build commit: `@SHA@`.
