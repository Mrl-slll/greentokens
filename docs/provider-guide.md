# GreenTokens Provider: setup for a computer owner

You lend this computer's processor and NVIDIA graphics card to approved GreenTokens training jobs.
You need **one download**. Create your own provider account in the app; no invite code is needed.

## 1. Install
Use the [official Releases page](https://github.com/Mrl-slll/greentokens/releases). Current test release: **0.4.0 unsigned preview**. Windows shows **Publisher: Unknown** because no verified code-signing identity is available yet. A signed public release is pending identity verification.

- [Windows x64 download (0.4.0 unsigned preview)](https://github.com/Mrl-slll/greentokens/releases/download/provider-v0.4.0/GreenTokens-Provider-Setup.exe): Windows 10/11 x64. If Windows or Edge blocks it, stop and follow the troubleshooting guidance; do not disable protection or override organizational policy.
- Mac: download the `.dmg` from the same release. This preview is not notarized; if blocked, contact the operator.
- Linux: no installer yet.

Verify the Windows file with `Get-FileHash "$HOME\Downloads\GreenTokens-Provider-Setup.exe" -Algorithm SHA256` and compare all characters with the release's SHA-256 information. The checksum establishes matching bytes, not safety. Future signed releases must also show the verified publisher under Properties → Digital Signatures.

For **Couldn't download**, open Edge Downloads (Ctrl+J) for the exact error. For a detection, check Windows Security ? Protection history and send the version/hash/detection name to the maintainer. Organization-managed blocks require the administrator's approval.

## 2. Connect (1 minute of clicks)
1. Open **GreenTokens Provider**.
2. Click **New here? Create account**. Choose a username and any password, confirm the password, then click **Create account**. If you already have an account, **Sign in**. You can use the same account on your other computers.
3. Press the big **power button** and choose **Yes, set up & connect**.
   - The first time, the app installs Python and PyTorch **inside its own folder**: a few GB on NVIDIA computers,
     about 10–20 minutes. Keep the app open.
4. It says **Connected**. Done. Leave the app open while you want to share the computer.

The computer connects to GreenTokens by itself: no network settings, no firewall changes, no other computers to join.
It reconnects after a Wi-Fi change while the app is open. After reopening the app you stay signed in: just press the power button. The sign-in is kept securely by Windows (Credential Manager) or macOS (Keychain) and renewed each time you open the app; it lapses after 30 days without use. **Sign out** forgets it. The app never saves your password, and it does not start sharing by itself.

Keep your password safe: password recovery is not available in this pilot. The operator's server PC and tunnel must be running. If its public address changes, the operator needs to provide an updated app; creating another account will not fix a connection error.

## What you'll see
- **Home:** Connected or Not connected, and "GreenTokens is using X% of this computer right now".
- **Activity:** live processor, memory and **GPU** use, and the current job with its progress.

## NVIDIA graphics cards
- RTX 50-series (for example RTX 5070) needs an NVIDIA driver supporting **CUDA 12.8 or newer**. If the app says the
  driver is too old, update it from nvidia.com, then open **Settings → Repair setup**.

## Stop sharing
Press the power button again (Disconnect), click **Sign out**, or close the app. Sign out also revokes the current login session when the server is reachable. To remove it: Windows **Settings → Apps → Installed apps →
GreenTokens Provider → Uninstall**; Mac: drag it to the Trash.

## What runs on your computer
Only **approved** GreenTokens workloads (for example fine-tuning a text model). They run in the app's own folder,
download public models and datasets they need, and their temporary files are deleted after each job.
