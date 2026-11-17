# Setup & Git guide

How to get the GreenTokens code onto a computer, keep it up to date, and run each part. Written for our two machines: the **AMD ThinkPad (Windows)** and the **MacBook Air M4 (macOS)**.

## What lives where

The code is one GitHub repository: `https://github.com/Mrl-slll/greentokens`. Different parts live on different **branches**:

| Branch | What's on it | Who uses it |
| --- | --- | --- |
| `main` | Customer web app (this site), backend (FastAPI, Ray, MySQL, storage), Python client, docs | Everyone |
| `provider-app` | GreenTokens Provider desktop app (Windows + Mac) and its download page | Provider-app work |
| `feat/...` | Older feature branches | Reference only |

> **Important:** Git only shares work that has been **committed and pushed**. Changes that exist only on one computer (shown by `git status` as `M` or `??`) do not reach anyone else when they run `git pull`.

## 1. Install Git (once per computer)

**ThinkPad (Windows)**, in PowerShell:

```powershell
winget install --id Git.Git -e
```

Close and reopen the terminal, then check:

```powershell
git --version
```

**MacBook (macOS)**, in Terminal:

```bash
xcode-select --install
git --version
```

Tell Git who you are (once per computer):

```bash
git config --global user.name "Your Name"
git config --global user.email "you@example.com"
```

## 2. Get the code (once per computer)

Go to the folder where you keep projects, then:

```bash
git clone https://github.com/Mrl-slll/greentokens.git
cd greentokens
```

Already have the folder? Don't clone again: open it in VS Code and use the terminal there.

## 3. Everyday Git commands

See what changed on this computer:

```bash
git status
```

Get the latest code from GitHub (safe: refuses to mix in unexpected changes):

```bash
git pull --ff-only
```

See the last few changes:

```bash
git log --oneline -5
```

Switch to another branch, for example the provider app:

```bash
git fetch origin
git switch provider-app
```

Go back to the main code:

```bash
git switch main
```

## 4. Save and share your work

Never push straight to `main`. Make a branch, commit, push, then open a pull request on GitHub.

```bash
git switch -c my-change
git add path/to/changed-file
git commit -m "Describe what you changed"
git push -u origin my-change
```

Then open `https://github.com/Mrl-slll/greentokens/pulls` and click **New pull request**.

If `git pull` reports a **conflict**, stop and ask before running more commands. Nothing is lost; conflicts are fixed by editing the marked files.

## 5. ThinkPad (Windows): run the backend and the web app

Install once: **Python 3.12**, **Docker Desktop**, and **Node.js 24** (or use the portable Node in `.tools`, see the README).

Create the Python environment (once), from the repository folder in PowerShell:

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements-core.txt
```

Start the backend. Open **Docker Desktop** first and wait until it says the engine is running. Keep this terminal open:

```powershell
.\.venv\Scripts\python.exe -m scripts.local_stack
```

Check it: open `http://127.0.0.1:8000/docs`. If it says **"refused to connect"**, the backend isn't running.

Start the web app in a **second** terminal:

```powershell
npm.cmd ci
npm.cmd run dev
```

Open `http://127.0.0.1:3000`. In **Settings**, choose **Live** to see real jobs.

## 6. MacBook Air M4: get ready for the training stage

The backend is tested on Windows only. On the Mac, set up Git, the web app, and a Python environment for model training.

Install once with [Homebrew](https://brew.sh):

```bash
brew install python@3.12 node@24
```

Run the web app (it works in **Mock** mode without a backend):

```bash
npm ci
npm run dev
```

Prepare a separate training environment for the planned TrOCR stage (see [Train AI model contract](trocr-training-contract.md)):

```bash
python3.12 -m venv .venv-ml
source .venv-ml/bin/activate
python -m pip install torch==2.15.0 transformers==4.57.6 datasets==4.8.5 pillow
```

Check whether Apple's GPU acceleration (MPS) is available:

```bash
python -c "import torch; print('MPS available:', torch.backends.mps.is_available())"
```

`True` means PyTorch can use the M4's GPU. Training must still be benchmarked before relying on it.

## 7. Provider app (both computers)

Download it from the [0.3.1 unsigned preview release page](https://github.com/Mrl-slll/greentokens/releases/tag/provider-v0.3.1) (Windows `.exe`, Mac `.dmg`) after the release is published. Its source code is on the `feat/bert-training-and-live-usage` branch.

## Troubleshooting

| You see | Meaning | Fix |
| --- | --- | --- |
| `127.0.0.1 refused to connect` | That server isn't running on this computer | Start the backend (port 8000) or web app (port 3000) |
| Docker: `failed to connect to the docker API` | Docker Desktop isn't running | Open Docker Desktop and wait for "Engine running" |
| `Port 8000 is in use` | An old backend is still running | Close the other terminal, or press Ctrl+C there |
| `not a git repository` | The terminal is in the wrong folder | `cd` into the `greentokens` folder |
| `git pull` says `Not possible to fast-forward` | Your computer and GitHub both changed | Stop and ask; don't force anything |
