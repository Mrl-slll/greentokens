# Project memory and roadmap

> Publication note: machine names, private addresses and deployment URLs are placeholders. Recorded probe outcomes refer to the original private deployment, not to the example hostname. This documentation branch does not deploy the plan or publish the local experiment runtime.


Recorded from the user's instructions on 19 November 2026. This file is durable repository documentation for future developers/agents; it is not a claim that an external assistant memory service was updated.

## Shared agent knowledge with OpenViking — deferred

**User intent:** share project context and agent knowledge with a teammate using OpenViking. Keep this task remembered while documentation is cleaned up. Do not install or integrate it as part of the README work.

Proposed shape: one shared server with persistent storage and a stable HTTPS endpoint, one team/account, separate user credentials, and selected shared project sources. Private sessions/memories should not be assumed to merge automatically. Git remains the source of truth for source code/versioned docs.

Before implementation:

- Confirm which agent tools each teammate uses and where the service will run.
- Confirm hosting/model-service choices, data-sharing scope and credential handling.
- Check the exact selected release, its documentation and license. The reviewed current main project was AGPLv3; `AGENTS.md` requires user approval before using GPL/AGPL/unlicensed code. CLI/component licenses may differ.
- Keep the live database out of Git and out of OneDrive file synchronization; share through its service interface.
- Verify cross-user sharing, private-data isolation, restart persistence and backup restoration before importing broad project history.

References for later verification: [official repository](https://github.com/volcengine/OpenViking), [deployment](https://docs.openviking.ai/en/guides/03-deployment), [sharing](https://docs.openviking.ai/en/getting-started/22-sharing). No dependency, server, account or plugin was installed by this documentation task.

## Persistent provider connectivity — planned, not configured

**User intent:** providers install once and remain able to connect after ordinary operator/server restarts.

**Updated host plan:** use `operator-server`, the user-reported stationary Raspberry Pi with 8 GB RAM, 1 TB external storage and Debian, as the operator server; keep the development PC for development/administration. The user confirmed providers should install only GreenTokens, with Tailscale for administration. Tailscale connectivity to `<SERVER_TAILSCALE_IP>` and HTTPS health at `https://operator-server.example.com` were verified. The endpoint lacks the newer provider-auth marker, returns 404 for provider login, and accepts a remote development selector. Backend/version/authentication remediation is required before public rollout; public reachability and unattended recovery remain unverified. See the [detailed Pi deployment plan and probe evidence](server-migration-plan.md).

Required work:

1. Choose a domain/public API origin and configure a persistent tunnel route to the existing loopback API.
2. Run the tunnel and backend under explicit startup/recovery management. Handle Docker readiness and unattended reboot behavior.
3. Separate API/provider-login availability from unnecessary Ray startup dependencies.
4. Add container recovery/readiness policies, monitoring, backups and tested restoration.
5. Configure provider origin and Tauri CSP, verify any CI override, build and deliberately publish a replacement installer once.
6. Validate from a remote computer: login/job, API restart, tunnel restart, machine reboot and internet interruption without reinstalling.

The current Python provider loop already has transient network retry/backoff. Do not duplicate it under the assumption that no reconnection exists. Session persistence/renewal and interrupted-training recovery are separate features.

A stable hostname does not provide availability while the sole operator PC or internet link is down. Additional tunnel connectors alone do not replicate MySQL, object storage or experiment state. A failover design must address those dependencies and single-dispatcher/experiment-lock assumptions.

## Documentation maintenance agreement

The user wants developer-facing explanations detailed enough to understand AI-written code: what each tool is, where it is used, why it fits, what the architectural pattern is called, how to run/debug it and what its limits are. Preserve this level of explanation in the root/component READMEs.

Label facts as implemented, measured, historical, or proposed. Do not invent an original design rationale when only the current implementation is known. Do not imply that local work is pushed, deployed or present in an installed binary. GitHub writes require explicit authorization under project guidance.
