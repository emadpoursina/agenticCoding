# Changelog

## [0.5.0] - 2026-10-26

### Added
- Agentic Validation loop: feature-path live graph and dispatcher sequence updated to `converge(converged) → critic → tester → ship → pr-review → uat`.
- Validator compact reports: critic and PIVS tester add `LOOP_BACK: implement | plan | none`; implement-target failures route through converge, while plan-target or mixed failures park.
- Automatic PR review: `pr-reviewer` runs automatically as a loop state after Ship on feature and change paths; compact header with `VERDICT`, `CRITICAL_COUNT`, and `CRITICALS` routes Criticals back through converge (feature) or change worker (change) without a separate fix loop.
- Same-PR ship contract: subsequent ship passes on the same run reuse the existing PR URL and refresh walkthrough/evidence rather than opening a second PR; re-review runs with `--extra @<previous-review>.md`.
- Converge fingerprint extended to include validator IDs alongside sorted source-refs; validator IDs appear in task descriptions only, preserving spec/plan/constitution source-refs.
- Path isolation: change path remains tester-only (no critic, no LOOP_BACK, FINDINGS retry, no `tasks.md`); job path skips PR review and UAT.
- `keep-local` (alias `no-ship`) support: runs path validation then emits `SHIP: declined` and skips ship, automatic PR review, and UAT.

## [0.4.0] - 2026-10-26

### Changed
- Switch Antigravity worker runtime from Python SDK (`google.antigravity.Agent`) to official CLI headless `agy -p` invoked through `agy-spawn.py`.
- Edit jobs pass `--mode accept-edits --dangerously-skip-permissions`; scout jobs pass `--mode plan`. Child stdin is ignored (`DEVNULL`) and `--prompt-interactive` is omitted.
- Short jobs with wrapper `--print` use text stdout; long jobs use `--output-format stream-json` and persist raw CLI events to `events.jsonl`. Worker STATUS reconstructed from stream-json events or text stdout.
- Dual timeout enforcement when wrapper `--timeout` is set: maps to `agy --print-timeout {n}s` and sets wrapper SIGTERM then SIGKILL kill timer.
- Ready `worker-runtime` check for Antigravity now checks `agy` on PATH and successful `agy models`. The Python SDK is neither required nor checked.

## [0.3.1] - 2026-10-26

### Added
- `/handoff-speckit` command now lives in `.cursor/commands/` (was a local-only file) and is symlinked like the others.
- `/handoff-speckit` emits `keep-local` when the chat said not to ship, and lists unsettled questions under **Open decisions** for clarify to answer in its choice report. `skip` stays the default.

## [0.3.0] - 2026-10-26

### Added
- PIVS evidence bundle methodology: Plan test flows declare a proof type (UI = Playwright trace, video, and screenshots with Playwright commands only; API; CLI/job; logic); critic plan review **blocks** on orphan acceptance criteria, missing proof types, and UI proof without Playwright commands.
- Tester persists command-produced captures under `specs/<flow>/evidence/` and a single-table manifest at `specs/<flow>/evidence.md` (replaced on each run, FAIL still records every executed flow, full 40-char `HEAD` per row, API captures redact credentials/`Authorization`); tester compact report adds `EVIDENCE: <path>` without dropping PASS/FAIL.
- Validation layer: vendor-neutral PR CI re-run of `validation_commands` with Playwright capture and workflow-artifact uploads (GitHub Actions example only), recommended `specs/*/evidence/` and `specs/*/evidence.md` ignores, secrets guidance, and an optional fail-before/pass-after check.
- Ship adds mandatory PR `## Evidence` beside `## Walkthrough` and `EVIDENCE: included|none` (walkthrough unchanged); pr-reviewer evidence audit maps **stale** and **claimed but unproven** onto the Critical merge gate (trouble ≥ 0.8, file:line, trigger) so they REQUEST CHANGES without a second blocker; re-review audits the new head.

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
