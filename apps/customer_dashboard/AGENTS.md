# GreenTokens — project guidance for Codex

GreenTokens is a Ray-based distributed cloud computing platform.

## GitHub-first, reuse-before-build

Goal: save tokens and time by reusing existing code and libraries. Apply this only to
substantial new functionality. Skip it for simple bug fixes, formatting, renames, and
small edits.

### Order of checks (stop at the first rung that solves the task)

1. Existing project code: search this repo for helpers, modules, or patterns that already do it.
2. Installed dependencies: check requirements.txt / pyproject.toml / package.json for a
   package already installed that covers the need.
3. Standard library or a native platform feature.
4. GitHub search (GitHub MCP, read-only): for substantial new functionality, look for an
   existing open-source solution. Compare at most 3 candidates on: license, last commit date,
   open-issue health, stars, and fit.
5. Current docs (Context7): before using any library, fetch its current, version-specific
   documentation (Ray, FastAPI, MySQL drivers, Docker). Use the exact version in this project.
6. Only then write custom code, and keep it to the minimum integration needed.

### Selection rules

- Prefer well-maintained libraries (recent commits, active releases).
- Prefer permissive licenses (MIT, Apache-2.0, BSD). Flag GPL/AGPL/unlicensed code and
  ask me before using it.
- Do not copy large chunks of third-party code into this repo. Add the dependency instead.
- Summarize findings in a short table (name, license, last update, why/why not), then ask
  me to approve before adding a new dependency.

### Token discipline

- Do not repeat a search already done in this task. Reuse earlier findings.
- Ask Context7 for one library and one topic at a time, not whole manuals.
- Do not run research for tiny tasks.
- Use read-only GitHub tools only. Never create issues, PRs, branches, or commits unless I ask.
- Never print or store tokens/API keys in files, logs, or chat.
