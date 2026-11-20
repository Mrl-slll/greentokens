# GreenTokens Provider @VERSION@

- **[Download Windows x64 installer](https://github.com/@REPO@/releases/download/@TAG@/GreenTokens-Provider-Setup.exe)** — Windows 10/11 x64
- **[Download Mac installer](https://github.com/@REPO@/releases/download/@TAG@/GreenTokens-Provider-macOS.dmg)** — Apple silicon and Intel; macOS 11+
- **[SHA256SUMS.txt](https://github.com/@REPO@/releases/download/@TAG@/SHA256SUMS.txt)**

Windows publisher: **@PUBLISHER@**. Both the app executable and Windows installer are Authenticode-signed and timestamped. Code signing identifies the publisher; it does not guarantee immediate SmartScreen reputation or override organization policy.

## Install
1. Download the installer from the official link above.
2. On Windows, check Properties → Digital Signatures for the expected publisher. Run the installer for your own Windows account. Uninstall via Settings → Apps → GreenTokens Provider.
3. Open the app, create an account or sign in, then choose Connect and approve setup. The app downloads a private Python and training packages only after consent. It does not install GPU drivers.

Mac signing/notarization is separate: this preview is not notarized. If macOS blocks it, stop and contact the operator.

## Verify the download
Download SHA256SUMS.txt from this same release. In PowerShell:
```powershell
Get-FileHash "$HOME\Downloads\GreenTokens-Provider-Setup.exe" -Algorithm SHA256
```
Compare the complete hash with its entry in SHA256SUMS.txt. A matching checksum verifies the downloaded bytes, not that the program is risk-free.

## Download trouble
- Open Edge Downloads (Ctrl+J) and record the exact failure message. Retry the official link if the transfer was interrupted.
- For a warning or Defender detection, stop and check Windows Security → Protection history. Send the release version, SHA-256 and detection name to the maintainer for review.
- On managed devices, ask the administrator to approve the signed application. Do not disable browser/Windows protection or override an organizational block.

The operator's server must remain online. Sessions expire after 24 hours; password recovery is not yet available. Each job runs on one provider computer, not across multiple computers. This is a pilot, with no earnings offered.

Build commit: `@SHA@`.
