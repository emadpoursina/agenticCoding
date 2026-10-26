# Changelog

## [0.2.3] - 2026-10-26

### Changed
- pr-reviewer merge gate: only Critical blocks; Warning and Suggestion never change the verdict; APPROVE is allowed and zero findings is a valid result.
- pr-reviewer scores: trouble sets severity (Critical at 0.8+); frequency only sorts.
- pr-reviewer scope: only lines the PR changes; pre-existing code is never Critical.
- pr-reviewer Phase 5: "try to break the change" with file:line, trigger, and observable effect; unsupported candidates are dropped.
- pr-reviewer Phase 1.5: blocking only for a bypassed safety layer or a broken documented rule.
- pr-reviewer Phase 2: adds a None rating; Phase 4 is skipped when nothing is Medium or High.
- pr-reviewer re-review: review only new commits, no repeated findings, accepted risks, Criticals only from round 3.
- pr-reviewer: merged `rules.md` into `rule.md`, the file name every agent folder uses.

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
