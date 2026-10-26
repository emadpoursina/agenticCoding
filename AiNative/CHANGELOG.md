# Changelog

## [0.3.0] - 2026-10-26

### Added
- PIVS evidence bundle methodology: Plan test flows declare a proof type (UI = Playwright trace, video, and screenshots with Playwright commands only; API; CLI/job; logic); critic plan review **blocks** on orphan acceptance criteria, missing proof types, and UI proof without Playwright commands.
- Tester persists command-produced captures under `specs/<flow>/evidence/` and a single-table manifest at `specs/<flow>/evidence.md` (replaced on each run, FAIL still records every executed flow, full 40-char `HEAD` per row, API captures redact credentials/`Authorization`); tester compact report adds `EVIDENCE: <path>` without dropping PASS/FAIL.
- Validation layer: vendor-neutral PR CI re-run of `validation_commands` with Playwright capture and workflow-artifact uploads (GitHub Actions example only), recommended `specs/*/evidence/` and `specs/*/evidence.md` ignores, secrets guidance, and an optional fail-before/pass-after check.
- Ship adds mandatory PR `## Evidence` beside `## Walkthrough` and `EVIDENCE: included|none` (walkthrough unchanged); pr-reviewer gains an on-demand evidence audit — completeness, stale SHA vs PR head, CI job-success agreement — with **stale** and **claimed but unproven** as blocking findings, re-runnable after every fix push.

## [0.2.2] - 2026-10-25

### Added
- Ready `worker-runtime` antigravity auth accepts an authenticated Antigravity CLI (`agy models`) via PATH or `~/.local/bin`, in addition to Gemini API key and Vertex env.

## [0.2.1] - 2026-10-24

### Changed
- Worker backend default is `antigravity` (was `pi`). Override with `SPECKIT_WORKER=pi` or `git config speckit.worker pi`.

## [0.2.0] - 2026-10-24

### Added
- Antigravity SDK worker harness (`docs/agents/antigravity-harness/`) with `agy-spawn.py`, host skill symlink, and `/antigravity-harness` command.
- Ready-stage `worker-runtime` check for the selected backend only (`SPECKIT_WORKER` / `speckit.worker`: `pi` or `antigravity`).

### Changed
- Speckit orchestrate resolves worker backend Pi vs Antigravity SDK instead of assuming Pi for every worker stage.

## [0.1.0] - 2026-10-19

### Changed

- Model selection: three roles (reasoning, worker, validation) replace Tier 0–3; one model per role; validation is first-class.
