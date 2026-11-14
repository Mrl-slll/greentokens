# GreenTokens Core

GreenTokens orchestrates approved compute workloads on a local trusted Ray
runtime. Milestones 0–1 provide the CPU smoke test; Milestones 2–3 add a FastAPI
job API, durable MySQL records, a Ray Jobs dispatcher/reconciler, and verified
S3 artifacts in SeaweedFS. This is a local development pilot with a deliberately
limited identity stub; production startup is blocked.

Start the implemented pipeline from PowerShell (Docker Desktop must be running):

```powershell
.\.venv\Scripts\python.exe -m scripts.local_stack
```

Open <http://127.0.0.1:8000/docs>. See
[local development](docs/local-development.md) for job submission, testing,
shutdown, credentials, and limitations;
[architecture](docs/architecture.md) and
[security boundaries](docs/security-boundaries.md) describe the implementation.

Frontend teammates: start with the [applications handoff](docs/applications-handoff.md),
including its first-day checklist and verified API contract.

The remaining sections preserve the original Milestone 0–1 setup and validation.

## Initial environment inspection — November 14, 2026

| Item | Observed state |
| --- | --- |
| Workspace | Only `AGENTS.md`, `CLAUDE.md`, and `.clinerules/github-first.md` existed; no application code or dependency manifests to reuse. |
| Git | `git status --short --branch` reports that this is not a Git repository. No repository was initialized. |
| OS | Windows 11 Pro, build 10.0.26200, 64-bit; Python reports AMD64. |
| Python | `python` runs CPython 3.12.10; `py -0p` reports no registered installations. Use `python`, not the launcher. |
| Packages | Ray is absent. Global packages include SQLAlchemy 2.1.5 and PyMySQL 1.2.3; neither is needed for the smoke test. No project virtual environment exists. |
| WSL | WSL2 is configured, but its only registered distribution is `docker-desktop` (stopped). Ubuntu is not installed. |
| Docker | CLI 29.9.2 exists; the Linux engine connection fails because its named pipe is absent. |
| MySQL | Two `mysqld` processes were observed. No matching Windows service was listed. Server version, ownership, and database connectivity remain unverified; no credentials were accessed. |

Initial sandbox restrictions blocked WSL and OS queries. Approved read-only
queries outside the sandbox established the OS, WSL, and Docker observations.
Python version/package inspection and the Ray import-availability check succeeded.
These observations describe the environment before installation. See the
validation section below for subsequent execution results.

## Dependency decision

One direct dependency is installed, along with its transitive packages, in a
dedicated virtual environment rather than the global environment above.

| Name | License | Last update evidence | Why |
| --- | --- | --- | --- |
| `ray[default]==2.60.0` | Apache-2.0 | Official release dated November 4, 2026 | Matches the blueprint and supplies Ray Core plus standard tooling. No Train, PyTorch, or GPU extras are needed. |
| Python standard library | Included with Python | Existing Python 3.12.10 | `unittest`, `subprocess`, `socket`, and `os` cover testing and reporting without more direct dependencies. |

[Ray's repository](https://github.com/ray-project/ray) displayed approximately
44.3k stars and 2.8k open issues. Its
[2.60.0 release](https://github.com/ray-project/ray/releases/tag/ray-2.60.0)
contains recent fixes. These indicate ongoing maintenance, but issue resolution
health was not independently audited. The retrieved commit-history page was
cached from September 11, 2026, so the actual latest commit date is unverified.
No competing framework is necessary for this explicitly Ray-based milestone.

GitHub MCP and Context7 are unavailable in this session. Official documentation
and read-only GitHub pages were used instead. The version-specific documentation
URL could not be retrieved; the current official pages identify themselves as
Ray 2.60.0. There is no existing project pin to preserve.

[Ray installation documentation](https://docs.ray.io/en/latest/ray-overview/installation.html)
lists Python 3.12 on Linux and Windows AMD64. Windows support is beta, and
multi-node Windows clusters are untested. This verifies documented compatibility,
not a successful installation on this computer.

WSL2 Ubuntu/Linux remains the preferred development environment. For the first
single-machine check, the smallest change is to use the existing Windows Python.
The Windows route is used for this milestone; a separately approved Ubuntu setup
remains an option for later development. Do not use Docker's internal WSL
distribution for development.

## Milestone 1 implementation

The implementation consists of `scripts/ray_smoke_test.py`,
`requirements-smoke.txt`, and `tests/test_ray_smoke.py`.

1. Disable Ray usage reporting before startup. With no `RAY_ADDRESS`, start a
   fresh local runtime through `ray.init(address="local", ...)`, disable the
   dashboard, and configure local-only networking. Verify listening interfaces
   during execution; do not assume disabling the dashboard isolates Ray's other
   services. Do not open firewall ports.
2. With an explicit `RAY_ADDRESS`, connect to that designated trusted cluster
   using `ray.init(address=...)`; never silently fall back to a new cluster after
   connection failure. Remote operation is outside this milestone's acceptance.
3. Submit eight deterministic independent sum tasks before collecting results.
   Each task requests one logical CPU and zero GPUs and returns its input/result,
   hostname, process ID, and Ray node ID.
4. Collect with `ray.get()` and a finite timeout; validate all eight results
   against locally calculated expectations. Print logical cluster resources,
   successful task count, and participating hostnames. Do not require eight
   distinct processes or nodes: scheduling may reuse workers.
5. Report failures visibly with a nonzero exit status and always call
   `ray.shutdown()` in cleanup. Use a main guard for Windows subprocess behavior.
6. Add one standard-library integration test that runs the script in a subprocess
   with a timeout and verifies completion and the eight validated results. Run
   the script twice to check repeatability, then run the test. Record actual
   output and failures before declaring Milestone 1 complete.

API references: [initialization](https://docs.ray.io/en/latest/ray-core/api/doc/ray.init.html)
and [remote tasks](https://docs.ray.io/en/latest/ray-core/tasks.html).

## Windows setup and run commands

Run these in PowerShell from this workspace. Skip virtual-environment creation
and installation when using the already prepared environment.
`requirements-smoke.txt` pins `ray[default]==2.60.0`.

```powershell
Set-Location -LiteralPath 'C:\Users\kcody\OneDrive\Desktop\Greentokens core'
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements-smoke.txt
.\.venv\Scripts\python.exe -m pip check
Remove-Item Env:RAY_ADDRESS -ErrorAction SilentlyContinue
$env:RAY_USAGE_STATS_ENABLED = '0'
.\.venv\Scripts\python.exe scripts/ray_smoke_test.py
.\.venv\Scripts\python.exe scripts/ray_smoke_test.py
.\.venv\Scripts\python.exe -m unittest discover -s tests -p test_ray_smoke.py -v
```

Virtual-environment activation is unnecessary. Package installation needs network
access; executing the local smoke workload must not require external services,
API keys, Docker, MySQL, MinIO, or a GPU. The top-level Ray version is pinned;
transitive dependencies are not yet locked.

## Optional WSL2 route — separate installation approval required

In PowerShell, first check the available distribution names, then install Ubuntu
24.04 if listed, following
[Microsoft's WSL instructions](https://learn.microsoft.com/en-us/windows/wsl/install):

```powershell
wsl --list --online
wsl --install -d Ubuntu-24.04
wsl -d Ubuntu-24.04
```

Complete Ubuntu's interactive account setup, then run in its shell after the
Milestone 1 files exist:

```bash
sudo apt update
sudo apt install python3.12-venv
cd '/mnt/c/Users/kcody/OneDrive/Desktop/Greentokens core'
python3.12 --version
python3.12 -m venv "$HOME/.venvs/greentokens-smoke"
"$HOME/.venvs/greentokens-smoke/bin/python" -m pip install -r requirements-smoke.txt
"$HOME/.venvs/greentokens-smoke/bin/python" -m pip check
unset RAY_ADDRESS
export RAY_USAGE_STATS_ENABLED=0
"$HOME/.venvs/greentokens-smoke/bin/python" scripts/ray_smoke_test.py
"$HOME/.venvs/greentokens-smoke/bin/python" scripts/ray_smoke_test.py
"$HOME/.venvs/greentokens-smoke/bin/python" -m unittest discover -s tests -p test_ray_smoke.py -v
```

Keep Linux and Windows virtual environments separate. This optional route is
documented but has not been executed or verified on this machine.

## Validation — November 14, 2026

- Created `.venv` with Python 3.12.10 and installed the pinned requirements.
- `python -m pip check` inside `.venv`: `No broken requirements found.`
- Imported Ray and verified version `2.60.0`.
- Ran `scripts/ray_smoke_test.py` twice: both exited 0 with eight validated results,
  four worker processes, and one node on host `Cody`.
- Ran `python -m unittest discover -s tests -p test_ray_smoke.py -v` inside
  `.venv`: one integration test passed in 13.606 seconds. This executes the real
  script in another subprocess, rather than mocking Ray.
- During the first successful run, `netstat -ano -p tcp` showed the observed GCS,
  raylet, and Python TCP listeners on `127.0.0.1`. This check covers that Windows
  run, not future Linux or remote-cluster deployments.

Actual second-run stdout (resource values, PIDs, and node IDs vary by run):

```text
Cluster resources: {'CPU': 4.0, 'node:127.0.0.1': 1.0, 'memory': 457499034.0, 'node:__internal_head__': 1.0, 'object_store_memory': 196071014.0}
Available resources: {'CPU': 4.0, 'node:127.0.0.1': 1.0, 'memory': 457499034.0, 'node:__internal_head__': 1.0, 'object_store_memory': 196071014.0}
Task input=10000 result=50005000 hostname=Cody pid=3932 node_id=9641e26011a53a1fd43756b435a38c357e9cf576a9a3721f3a92bbc3
Task input=20000 result=200010000 hostname=Cody pid=27528 node_id=9641e26011a53a1fd43756b435a38c357e9cf576a9a3721f3a92bbc3
Task input=30000 result=450015000 hostname=Cody pid=29288 node_id=9641e26011a53a1fd43756b435a38c357e9cf576a9a3721f3a92bbc3
Task input=40000 result=800020000 hostname=Cody pid=15320 node_id=9641e26011a53a1fd43756b435a38c357e9cf576a9a3721f3a92bbc3
Task input=50000 result=1250025000 hostname=Cody pid=15320 node_id=9641e26011a53a1fd43756b435a38c357e9cf576a9a3721f3a92bbc3
Task input=60000 result=1800030000 hostname=Cody pid=15320 node_id=9641e26011a53a1fd43756b435a38c357e9cf576a9a3721f3a92bbc3
Task input=70000 result=2450035000 hostname=Cody pid=29288 node_id=9641e26011a53a1fd43756b435a38c357e9cf576a9a3721f3a92bbc3
Task input=80000 result=3200040000 hostname=Cody pid=27528 node_id=9641e26011a53a1fd43756b435a38c357e9cf576a9a3721f3a92bbc3
Successful tasks: 8/8
Hostnames: ['Cody']
Distinct worker PIDs: 4
Distinct node IDs: 1
SMOKE TEST PASSED
```

The initial sandboxed pip attempt failed with Windows socket error 10013. The
approved network-enabled installation succeeded. The initial sandboxed smoke
run exited 1 because access to `C:\Users\kcody\.ray` was denied; both subsequent
direct runs and the integration test succeeded outside the sandbox. No firewall
rules were changed. Usage reporting is disabled before Ray is imported.

Milestone 1 is proven on this Windows machine. Remote `RAY_ADDRESS` execution,
WSL, and multi-node behavior have not been tested. Windows remains a beta Ray
platform; later cluster development should use the planned supported Linux setup.

## Next milestone

Milestones 2–3 are implemented; see [the checklist](docs/milestone-checklist.md).
Milestone 4 requires four explicitly authorized machines, private networking,
hardware discovery, worker pause/loss handling, and bounded retries. It has not
been started. Dashboards, training, billing, and public onboarding remain later work.
