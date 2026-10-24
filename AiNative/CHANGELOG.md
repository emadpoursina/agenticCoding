# Changelog

## [0.2.0] - 2026-10-24

### Added
- Antigravity SDK worker harness (`docs/agents/antigravity-harness/`) with `agy-spawn.py`, host skill symlink, and `/antigravity-harness` command.
- Ready-stage `worker-runtime` check for the selected backend only (`SPECKIT_WORKER` / `speckit.worker`: `pi` or `antigravity`).

### Changed
- Speckit orchestrate resolves worker backend Pi vs Antigravity SDK instead of assuming Pi for every worker stage.

## [0.1.0] - 2026-10-19

### Changed

- Model selection: three roles (reasoning, worker, validation) replace Tier 0–3; one model per role; validation is first-class.
