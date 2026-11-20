# Documentation index and authority

[Start with the system README](../README.md). It is the canonical whole-project guide. Component READMEs explain their implementation; these documents supply runbooks, contracts and evidence.

## Current entry points

| Document | Scope |
| --- | --- |
| [System guide](../README.md) | Whole architecture, technology vocabulary, directory map, paths and startup |
| [Architecture](architecture.md) | Compact current architecture reference |
| [Security boundaries](security-boundaries.md) | Current development/authentication/trust limitations |
| [Local development](local-development.md) | Local stack runbook entry point |
| [Operator checklist](operator-checklist.md) | Remote provider test-day checks |
| [Provider owner guide](provider-guide.md) | Instructions for people lending their computers |
| [Developer quickstart](developer-quickstart.md) | Local sum/regression client tutorial, not all platform capabilities |
| [Windows distribution](windows-distribution.md) | Signing/release prerequisites and existing preview exception |
| [Setup/Git guide](setup-guide.md) | Workstation/Git onboarding; check checkout paths against the current root guide |
| [Roadmap / project memory](roadmap.md) | Deferred OpenViking task and persistent connectivity plan |
| [operator-server server migration plan](server-migration-plan.md) | Stationary Linux host, Tailscale/public access, recovery, migration and acceptance gates; not deployed |

## Contracts, plans and historical evidence

`trocr-training-contract.md` describes a proposed backend contract; it does not prove a runnable TrOCR template. `sdk-packaging-proposal.md` describes packaging work, not a published SDK.

The following are scoped records of earlier stages, not the current system specification: `core-setup-history.md`, `frontend-team-checklist-history.md`, `applications-handoff.md`, `milestone-checklist.md`, `milestones-2-3-plan.md`, `validation-milestones-2-3.md`, `developer-mvp-validation.md`, `frontend-integration-validation.md`, and `provider-architecture-review-2026-11-16.md`. Their test counts, plans and feature exclusions belong to their recorded time/scope. They remain available to preserve evidence.

For the completed four-PC run, use the [experiment guide](../experiments/four_pc_cpu/README.md) and its measured report. Do not confuse the earlier per-step-gradient plan with the final periodic-weight-change algorithm.

## Updating these docs

Put shared concepts and overall capability status in the root README. Put source maps, contracts, commands and component limitations in the owning component README. Link rather than duplicate long explanations. Date historical observations and keep planned work in the roadmap. Verify relative links after edits.

The web app renders only files allowlisted by `lib/guides.ts`; other Markdown links may be rewritten to GitHub `main`. Local/unpublished documentation can therefore be readable in the editor but absent from the hosted documentation site. Updating that renderer or publishing docs is separate from this documentation-only pass.
