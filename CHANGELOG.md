# Changelog

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
