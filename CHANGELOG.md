# Changelog

## [0.13.0] - 2026-09-05
### Fixed
- Constrained smoke `--next-ready` to the validated disposable project.
- Required smoke to run a named-task or project-scoped next-ready publish path.
- Added a `main`-entry refusal check proving blank smoke targets perform no pushes or pull requests.

## [0.12.0] - 2026-09-05
### Added
- Delivered the live Hermes PIV bridge: read-only native Kanban adapter, one dispatcher/CLI entry, focused hermetic checks, and named-repository smoke guard.
### Changed
- Mounted `personalAgent` into the Hermes worker without adding a second task store, worker, scheduler, or AiNative write path.

## [0.11.0] - 2026-09-05
### Added
- Implementation task list for the live Hermes PIV bridge (`specs/010-live-piv-bridge/tasks.md`): read-only native board, one dispatcher/CLI entry, hermetic checks and named-repo smoke, Hermes wiring without rewriting methodology. No application code in this version.

## [0.10.0] - 2026-09-05
### Added
- Implementation plan and design artifacts for the live Hermes PIV bridge (`specs/010-live-piv-bridge`: plan, research, data model, contract, quickstart). No application code in this version.

## [0.9.0] - 2026-09-05
### Added
- Feature spec for the live Hermes PIV bridge (`specs/010-live-piv-bridge`): native Kanban as the only live task board, read-only live adapter, dispatcher entry through the existing orchestrator, feature-branch publish and existing pull-request-created notice, focused fixture checks, and a smoke path that refuses to push until a disposable repository is named.

## [0.8.5] - 2026-09-05
### Added
- Enrolled the disposable quiz project `ich-mag-dich` as the live managed project.

## [0.8.4] - 2026-09-05
### Removed
- Unenrolled `hermes-v0-sandbox` from the live project list, deleted the local workspace copy, and deleted the GitHub repository.

## [0.8.3] - 2026-09-04
### Added
- Project-scoped Hermes MCP configuration using the running `hermes-agent` Docker Compose service.

## [0.8.2] - 2026-09-03
### Fixed
- Rebuilt the local Hermes Docker image from the official image so live Kanban workers can start.

## [0.8.1] - 2026-09-02
### Fixed
- Enroll the live sandbox at `/workspaces/hermes-v0-sandbox` so the control plane matches the cloned repo folder.

## [0.8.0] - 2026-09-02
### Added
- Phase 8 fixture end-to-end check (`personalAgent/tests/test_v0_e2e.py`): one task from the board through plan, implement, validate, simulated pull request, and notices.

## [0.7.0] - 2026-09-02
### Added
- Phase 7 implementation: durable overlay snapshots, automatic interrupted-run reclaim, workspace recovery, and duplicate-worker prevention.
### Changed
- Kept operational state in one atomic overlay document with no second task store or Phase 8 work.

## [0.6.0] - 2026-09-02
### Added
- Implementation task list for Phase 7 restart recovery (`specs/009-restart-recovery/tasks.md`): persist overlay, automatic reclaim, workspace recover, duplicate prevention.

## [0.5.0] - 2026-09-02
### Added
- Implementation plan and design artifacts for Phase 7 restart recovery (`specs/009-restart-recovery`: plan, research, data model, contract, quickstart). No application code in this version.

## [0.4.0] - 2026-09-02
### Added
- Feature spec for Phase 7 persistence and restart recovery (`specs/009-restart-recovery`): survive control-plane restart, reclaim one interrupted run, recover the working copy and branch, and prevent duplicate workers.

## [0.3.1] - 2026-09-02
### Added
- Expanded Telegram contract coverage for recovery, blocked, failure, retry, idempotency, status, and chat-resume behavior.

## [0.3.0] - 2026-09-02
### Added
- Telegram messaging seam for meaningful workflow events, home-chat status commands, and decision-letter resume.
- In-memory contract channel with skip handling, same-notice retry limits, and occurrence idempotency.
### Changed
- Reused the existing Hermes Telegram transport without adding a bot, dependency, or task database.

## [0.2.0] - 2026-09-02
### Added
- Implementation plan and design artifacts for Phase 6 Telegram (`specs/008-telegram`: plan, research, data model, contract, quickstart). No application code in this version.

## [0.1.0] - 2026-08-30

### Added

- Implementation plan and design artifacts for workspace manager, Git safety, and execution identity (`specs/003-workspace-manager`: plan, research, data model, contract, quickstart). No application code in this version.
