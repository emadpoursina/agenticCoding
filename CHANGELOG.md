# Changelog

## [0.36.0] - 2026-09-24
### Changed
- 019 implement pass: the Kanban board is the user-facing work queue
  (`specs/019-hermes-onboarding-contract/` on branch
  `hermes-onboarding-contract`). Feature Cards decompose into child Task
  Cards on the primary board, executors run children independently, and the
  parent completes through the automated validator with board-authoritative
  manual edits journaled fail-closed. Human gates surface as board markers;
  `confirm`/`uat` park only on real raises. See
  `personalAgent/CHANGELOG.md` (1.11.0) for the Hermes package detail and
  `specs/019-hermes-onboarding-contract/tasks.md` for the validation record.

## [0.35.0] - 2026-09-21
### Changed
- 018 apply slice implemented on Hermes only: live execution is the
  Hermes-owned feature-loop state machine with one new Pi session per agent
  state; `confirm`/`uat`/`publish` are human/parent gates, critic → tester →
  UAT → pr-review gate GitHub publish, clarify questions relay over Telegram
  and are encoded by a second clarify Pi session, per-step harness requests
  and strict per-state compact reports replace the whole-playbook request,
  and in-flight 013 whole-playbook overlays park for a human. Cursor
  `/speckit-orchestrate` is untouched. See
  `personalAgent/CHANGELOG.md` (1.5.0) for the Hermes package detail and
  `specs/018-unified-feature-loop/`.

## [0.34.0] - 2026-09-21
### Added
- Canonical live feature loop in AiNative
  (`docs/systems/feature-loop.md`) and ADR
  `docs/records/decisions/2026-09-feature-loop.md`.
- Apply spec for aligning Hermes and Cursor to that loop
  (`specs/018-unified-feature-loop/`).
- Documented two orchestrators on that graph: Cursor
  `/speckit-orchestrate` (Task or `/pi-harness`) and Hermes (Pi only).
- Scoped the 018 apply slice to Hermes (add/remove the one-shot
  playbook); Cursor orchestrate is documented, not part of that pass.

## [0.33.0] - 2026-09-17
### Added
- Feature specification, plan, research, data model, quickstart, tasks, and
  contract for mapping native Hermes Kanban project ids to operational
  enrolled project ids (`specs/017-kanban-project-identity/`).
### Fixed
- Declared native project ids with `kanban_project_ids` and canonicalized
  them at the read-only board boundary so cards created with the config id
  run the enrolled project, worktrees and records keep the operational id,
  resume/reclaim accept either form, and unmapped ids are named instead of
  silently reporting "no ready task".
- Resolved the native Kanban database per enrolled project (Hermes 0.21
  per-board layout) so project-board cards are visible to the worker, and
  sanitized drifted advisory harness-result paths so model schema drift no
  longer discards finished Pi runs.
- Proved the full pipeline live: `--doctor` with the declared alias, card
  selection, a completed Pi run, validation pass, feature-branch push, and
  PR #2 on the disposable practice repo.

## [0.32.2] - 2026-09-14
### Added
- Added a filled, non-secret Hermes `USER.md` reference in
  `personalAgent/docs/context/` while keeping the blank example template
  and the private live file.

## [0.32.1] - 2026-09-14
### Added
- Added a filled, non-secret Hermes `SYSTEM.md` reference in
  `personalAgent/docs/context/` (Pacific time `America/Los_Angeles`)
  while keeping the blank example template and the private live file.

## [0.32.0] - 2026-09-14
### Added
- Implemented Hermes startup context loading, exact-path validation,
  revision-only metadata, precedence resolution, safe templates, and
  secret-safe `--doctor` diagnostics.
### Changed
- Added focused startup and live-boundary checks while keeping registered
  context text out of coding-job and operational-record payloads.

## [0.31.0] - 2026-09-14
### Added
- Actionable, dependency-ordered implementation tasks for Hermes startup
  context loading, exact paths, revision metadata, precedence, isolation,
  diagnostics, and safe placeholder instructions.

## [0.30.0] - 2026-09-14
### Added
- Implementation plan and design artifacts for Hermes startup context
  registration, exact container-path validation, revision-only diagnostics,
  precedence, coding-job isolation, and safe placeholder templates.

## [0.29.0] - 2026-09-14
### Added
- Feature specification and requirements checklist for registering Hermes
  `AGENTS.md`, persistent `SYSTEM.md`, and persistent `USER.md` as startup
  context with exact-path validation, precedence, revision-only records, and
  safe first-delivery placeholders.

## [0.28.0] - 2026-09-13
### Added
- Delivered the AiNative four-layer alignment across the Hermes adapter,
  disposable fixtures, live setup projection, guidance, active specifications,
  and migration verification.
### Changed
- Made `docs/agents/` the only accepted adapter root and removed obsolete
  simple-roster, manifest, and top-level-agent fallback behavior.

## [0.27.0] - 2026-09-13
### Added
- Actionable task list for implementing and verifying the AiNative
  four-layer structure alignment across the Hermes consumer, fixtures,
  live setup projection, guidance, and active specifications.

## [0.26.0] - 2026-09-13
### Added
- Implementation plan and design artifacts for aligning the Hermes consumer
  and live test app with AiNative's four-layer documentation structure.

## [0.25.3] - 2026-09-09
### Fixed
- Give the Hermes overlay folder to the hermes user at container start so
  named Docker volumes are writable and live tasks can begin.

## [0.25.2] - 2026-09-09
### Added
- Added an explicit Hermes Kanban worker contract so claimed workers
  delegate implementation to the Pi harness instead of editing managed
  projects directly.

## [0.25.1] - 2026-09-09
### Changed
- Marked the old Hermes Spec Kit stage specs as historical so the live
  path stays Pi-owned, with leftover old-path work parked for a person.

## [0.25.0] - 2026-09-08
### Fixed
- Updated the live Pi harness contract and implementation to use Pi's JSONL
  `prompt` command and private settlement events, extracting one normalized
  Hermes result without exposing the event stream.

## [0.24.0] - 2026-09-08
### Added
- Delivered the live Pi RPC process boundary, strict timeout loading, and
  acknowledged legacy-work restart recovery.

## [0.23.0] - 2026-09-08
### Added
- Implementation plan and design artifacts for closing the live Pi process,
  timeout configuration, and acknowledged legacy-restart harness gaps.

## [0.22.0] - 2026-09-08
### Added
- Focused Pi playbook fixtures for conditional analyze omission and repeated
  implement/converge cycles.

## [0.21.0] - 2026-09-08
### Fixed
- Skip now records its assumptions and choice report before one continuation
  confirmation, while human parking fixtures cover implementation and later
  question batches.
### Added
- Focused isolation snapshots for the enrolled project, AiNative fixture,
  control-plane state, and sibling worktree.
### Removed
- Deleted the leftover empty legacy Spec Kit fixture tree.

## [0.20.0] - 2026-09-08
### Added
- Delivered the provider-neutral Harness Adapter boundary with Pi as the
  first execution harness.
### Changed
- Moved the full Spec Kit playbook behind Pi and kept Hermes responsible for
  human decisions, validation, and pull-request publication.
### Removed
- Removed the legacy Hermes Spec Kit stage machine from the live path.

## [0.19.0] - 2026-09-08
### Added
- Feature specification for a generic Harness Adapter with Pi as the first
  execution harness.
### Changed
- Defined full Spec Kit playbook ownership in Pi, human decision handling in
  Hermes, and removal of the legacy Hermes stage machine.

## [0.18.1] - 2026-09-08
### Added
- Agent brief for starting Harness Adapter work through the global `/speckit-orchestrate` skill.

## [0.18.0] - 2026-09-08
### Changed
- Locked the next-step harness plan: Pi runs the full Spec Kit orchestrate pipeline; Hermes no longer owns the short plan/tasks/implement path.

## [0.17.1] - 2026-09-07
### Fixed
- Live Spec Kit image manifests now include implement so Docker matches the delivered runtime pin.

## [0.17.0] - 2026-09-07
### Added
- Delivered Spec Kit implementation, native handoff continuation, validation/recovery routing, and publish gating.
### Changed
- Kept `PLANNING_COMPLETE` as an intermediate checkpoint and documented the full `PR_CREATED` live path.
- Marked Phase 9 complete in the scratch V0 plan.

## [0.16.0] - 2026-09-07
### Added
- Implementation plan and design artifacts for Spec Kit implementation, existing validation/recovery, and orchestrator-owned GitHub publish.
### Changed
- Defined strict native handoff resume semantics so `PLANNING_COMPLETE` remains distinct from PIV completion.

## [0.15.0] - 2026-09-07
### Added
- Feature specification for the next live Hermes slice: Spec Kit implementation from native plan/task artifacts, existing validation/recovery, and orchestrator-owned GitHub publish.
### Changed
- Recorded that `PLANNING_COMPLETE` remains a planning checkpoint rather than PIV-complete, with implementation continuing in the same isolated worktree.

## [0.14.2] - 2026-09-07
### Changed
- Updated the scratch V0 plan so live planning uses one Spec Kit adapter after scout, stops at planning complete, and does not copy framework agents into AiNative.

## [0.14.1] - 2026-09-07
### Fixed
- Fail closed when the live external-framework provider or pinned runtime is missing or mismatched.
- Added live-style isolation and scout-only planning checks for the external framework path.

## [0.14.0] - 2026-09-07
### Added
- Delivered the offline external-framework planning adapter with pinned Spec Kit runtime metadata and native plan/task artifact handling.
### Changed
- Documented the single-provider planning path, isolated setup retention, and planning-complete workflow outcome.

## [0.13.6] - 2026-09-07
### Added
- Verified github.com SSH host keys that persist across container recreate (no ssh-keyscan, no accept-new).
- Optional runtime `GH_TOKEN` passthrough so the boot script can log the GitHub CLI in without storing a token in git.
### Changed
- GitHub CLI config is kept under the persisted Hermes home.

## [0.13.5] - 2026-09-07
### Changed
- Spec Kit orchestration now falls back to inheriting the current chat model when the required worker model is unavailable but exactly matches it.

## [0.13.4] - 2026-09-07
### Fixed
- Hardened the live bridge against comment-bearing config files and non-streaming/fenced model responses.
- Routine, fully specified tasks no longer needlessly ask for clarification.
- Dispatcher failures now return a non-zero result for failed or blocked workflows.
- The Hermes image now includes the `gh` CLI required for pull-request operations.

## [0.13.3] - 2026-09-07
### Fixed
- Live model calls now send the OpenCode session header the gateway requires.

## [0.13.2] - 2026-09-05
### Fixed
- Live model calls no longer hit a doubled `/v1/v1` URL that returned an empty answer.

## [0.13.1] - 2026-09-05
### Fixed
- Live discovery can read the quiz project files (read-only) so the first step does not stall asking whether `index.html` exists.

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
