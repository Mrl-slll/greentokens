# GreenTokens Provider: setup for a computer owner

You lend this computer's processor and NVIDIA graphics card to approved GreenTokens training jobs.
You need **one download**. Create your own provider account in the app; no invite code is needed.

## 1. Install (2 minutes)
- **Windows 10/11:** download **GreenTokens-Provider-Setup.exe** from the release page the operator sends you and run it.
  If Windows shows *"Windows protected your PC"*, click **More info → Run anyway** (the app isn't code-signed yet).
- **Mac:** download **GreenTokens-Provider-macOS.dmg**, drag the app into **Applications**, then the first time
  **right-click → Open → Open**.
- **Linux:** not available as an installer yet.

## 2. Connect (1 minute of clicks)
1. Open **GreenTokens Provider**.
2. Click **New here? Create account**. Choose a username and a password of 12-128 characters, confirm the password, then click **Create account**. If you already have an account, **Sign in**. You can use the same account on your other computers.
3. Press the big **power button** and choose **Yes, set up & connect**.
   - The first time, the app installs Python and PyTorch **inside its own folder**: a few GB on NVIDIA computers,
     about 10–20 minutes. Keep the app open.
4. It says **Connected**. Done. Leave the app open while you want to share the computer.

The computer connects to GreenTokens by itself: no network settings, no firewall changes, no other computers to join.
It reconnects after a Wi-Fi change while the app is open. After reopening the app, **sign in again**, then press the power button. Sessions last up to 24 hours. The app does not save your password or session token.

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
