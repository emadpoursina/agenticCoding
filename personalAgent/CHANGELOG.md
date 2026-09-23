# Changelog

## [1.7.0] - 2026-09-22
### Added
- Interactive front on the dispatcher: `python -m hermes_kanban --config …`
  with no other selector, in a terminal, asks whether to enroll a repository
  or add a card, then runs the existing onboard or `hermes kanban create`
  path. Card answers set `## Path` and `## Skill`. A non-interactive shell
  and a claimed worker keep the previous selector rules.

## [1.6.0] - 2026-09-22
### Added
- Card paths: the dispatcher reads `## Path` (`feature`, `change`, `job`;
  missing means `feature`) and `## Skill` (required only for `job`,
  allowlisted to `prd-writer` and `project-bootstrapper`) onto the task.
  Unknown paths or job skills fail closed before Pi starts.
- `change` path: `ready` → one `change` worker → `tester` → `COMPLETED`
  with no UAT, pr-review, or publish. `SCOPE: feature` parks `BLOCKED`.
- `job` path: `ready` → one allowlisted skill worker → `COMPLETED` with
  no publish. `needs_human` parks and resumes in a new job session, same
  as clarify. `SCOPE: feature` parks `BLOCKED`.
- New AiNative `change` agent (`docs/agents/change/`); `ready` skips the
  Spec Kit layout check for `change` and `job` cards (git and branch
  preflight only).
- Hermetic fixture-Pi coverage for both short paths, `SCOPE` stop, and
  fail-closed validation (no network, no publish).
### Changed
- `WorkflowRecord` persists `card_path` (old overlays default to `feature`)
  so a resume cannot switch graphs. Ready inputs carry `card_path`.

## [1.5.0] - 2026-09-21
### Changed
- Live execution is now the Hermes-owned **feature loop** state machine
  (`ready → specify → clarify → confirm → plan → tasks → [analyze] →
  implement ↔ converge → critic → tester → uat → pr-review → publish`),
  matching `AiNative/docs/systems/feature-loop.md`. Every agent state starts
  **one new Pi session** prompted for that step only; Hermes checks the
  per-state compact report and advances, retries (3 attempts per state), or
  parks.
- Harness start requests carry a per-step `StepStartRequest` (step id,
  flow id, skill path, worktree, per-step model profile, inputs, resume
  context). Requests for a whole-playbook job, a non-agent state
  (`confirm`/`uat`/`publish`), or an unknown step are refused at the
  boundary, not translated. Per-state compact reports
  (`READY`/`STATUS`/`ANALYZE`/`IMPLEMENT_STATUS`/`CONVERGE_OUTCOME`/
  PASS-FAIL verdicts) are parsed strictly; unknown or missing fields fail
  the step.
- Validation is critic → tester → UAT → pr-review before any GitHub publish.
  The tester state receives the project's declared `validation_commands` as
  inputs and runs them in the worktree; `_run_validation` no longer runs in
  Hermes and no longer unlocks GitHub. Publish runs only after critic PASS ∧
  tester PASS ∧ uat pass ∧ pr-review PASS, on the feature branch only, and
  only when the operator approves the post-pr-review park.
- Clarify questions park and are relayed one question at a time over the
  existing Telegram path; recorded answers are encoded by a **second clarify
  Pi session** (same `clarify` step id — no new graph state). `confirm`
  always precedes `plan`, including under operator `skip`; UAT is simple
  human QA with a feature-derived checklist and no auto-loop; after
  pr-review completes the record parks for operator decision.
### Removed
- The one-shot whole-playbook Pi run (`speckit-orchestrate` as a flow),
  whole-playbook resume, and `_run_validation` as the GitHub gate. Config no
  longer defines `harness.playbook`; an optional per-step `step_profiles`
  model-profile mapping replaces it (unknown keys fail closed at startup).
  The live role map (scout/specs-planner/builder/tester-as-shell-role) is
  removed with it.
### Added
- In-flight 013 whole-playbook overlay records park
  `HUMAN_DECISION_REQUIRED` with the diagnostic "superseded by 018 —
  whole-playbook run" at startup; they are never auto-migrated onto the new
  graph.
- Hermetic tests for per-state session starts, prompt isolation, human
  gates, the implement↔converge loop, and the critic-before-publish gate
  (fixture Pi runtime, no network).
- `AGENTS.md`/`README.md` now link `/ainative/docs/systems/feature-loop.md`
  as the methodology source of truth instead of describing a forked loop;
  `docs/context/SYSTEM.md` reference copy updated to match.

## [1.4.7] - 2026-09-20
### Added
- One-command onboarding: when no native `projects.db` project matches the
  repository, `--onboard` now creates it through the upstream
  `hermes project create` CLI (fail-closed on CLI failure; dry-run never
  creates) and re-resolves the native id, so the operator no longer runs
  any Hermes command manually.
- `--create-cards`: publishes validated PRD drafts to the native board via
  upstream `hermes kanban create` (`--project <native-id>`, `--priority`,
  card body as the draft text, and an `--idempotency-key` slug per title
  so re-runs do not duplicate cards). Drafts with TODO sections fail
  closed unless `--allow-todo` parks them in triage (`--triage`) for the
  specifier to flesh out and promote.

## [1.4.6] - 2026-09-20
### Added
- `--onboard owner/name` on the one dispatcher: resolves the native
  `projects.db` id by slug (read-only, `HERMES_PROJECTS_DB` override),
  clones the repository into `workspace.root/<id>`, scaffolds `README.md`,
  `AGENTS.md`, and `.ainative/project.yaml` without overwriting, then
  appends and revalidates a `config/default.yaml` project entry
  (restore-on-failure). Idempotent for already-enrolled projects and
  supports `--branch`, `--project-id`, and `--dry-run`.
- PRD card drafting behind `--prd` (with `--drafts-out`,
  `--default-priority`): splits PRD `##` sections into validated card
  drafts with the exact native headings (`## Priority` P0–P3,
  `## Problem`, `## Expected Result`); the bridge still never writes
  `kanban.db` — drafts are paste-ready for Hermes grooming.

## [1.4.5] - 2026-09-17
### Added
- Declared native Hermes project ids per enrolled project via
  `kanban_project_ids` in `config/default.yaml`.
### Fixed
- Translated a card's native Kanban `project_id` to the operational id at
  the read-only board boundary, so cards created with the config id no
  longer fail as `UnknownProjectError` or silently report "no ready task".
- Resolved the native Kanban database per enrolled project
  (`kanban/boards/<id>/kanban.db`) with the legacy single-`kanban.db`
  layout as fallback, so project-board cards are no longer invisible to
  the worker on Hermes 0.21.
- Canonicalized resume input and legacy overlay records so either id form
  resumes and reclaims the same workflow.
- Tolerated model-drifted harness result shapes: bare-path artifacts, and
  advisory `changes`/`output_reference` entries are sanitized instead of
  discarding a finished Pi run.
- Named unmapped native project ids in the `--next-ready` error and listed
  declared aliases in `--doctor`.

## [1.4.4] - 2026-09-15
### Added
- Wired fail-closed startup loading for `AGENTS.md`, `SYSTEM.md`, and
  `USER.md`, plus `--doctor` and blank persistent-file templates.
### Changed
- Refreshed the Git `SYSTEM.md` snapshot so it matches the private live
  file. Hermes still loads only `/opt/data/hermes-context/SYSTEM.md`.

## [1.4.3] - 2026-09-14
### Changed
- Rewrote `AGENTS.md` as Hermes identity and operating rules (job,
  forbidden actions, piece boundaries, and which rules win), with
  package-coding notes scoped only to this repository.
- Clarified `SYSTEM.md` and `USER.md` so environment, identity, and
  operator preference stay in separate files.

## [1.4.2] - 2026-09-14
### Added
- Added a filled, non-secret `USER.md` reference under `docs/context/`
  for operator preferences. The blank `USER.example.md` template is
  unchanged. Hermes still loads the private live file, not the Git copy.

## [1.4.1] - 2026-09-14
### Added
- Added a filled, non-secret `SYSTEM.md` reference under `docs/context/`
  for this Hermes install, with Pacific time (`America/Los_Angeles`).
  The blank `SYSTEM.example.md` template is unchanged. Hermes still loads
  the private live file, not the Git copy.

## [1.4.0] - 2026-09-14
### Added
- Registered exact Hermes startup context paths for `AGENTS.md`, `SYSTEM.md`,
  and `USER.md`, with fail-closed loading and revision-only metadata.
- Added safe persistent-context templates, operator setup guidance, precedence
  resolution, secret-safe `--doctor` diagnostics, and focused checks.
### Changed
- Live startup validates all three context files before board selection or
  command handling while keeping coding-job and overlay payloads unchanged.

## [1.3.6] - 2026-09-13
### Changed
- Aligned AiNative agent discovery, fixtures, live setup links, guidance,
  and adapter-related specifications with the current `docs/agents/`
  contract and four semantic layers.
### Removed
- Removed retired simple-roster, manifest, and top-level-agent fallback
  behavior and obsolete fixture files.

## [1.3.5] - 2026-09-11
### Fixed
- Reuse a valid same-task feature worktree after Pi leaves uncommitted files,
  without resetting or discarding the work.
- Run declared project validation commands without requiring or calling a
  validation model; explicit model-backed validation slots still require an
  assignment.
- Store Pi's writable state under the persisted Hermes home and seed its
  image-provided model defaults at container start.
### Changed
- Documented that upstream Hermes Kanban must preserve the task-template
  headings, including exact `## Priority` values, because this repository's
  native board adapter remains read-only.

## [1.3.4] - 2026-09-11
### Fixed
- Honor the dispatcher-provided `HERMES_KANBAN_DB` path so live workers read
  the board that owns the claimed task instead of falling back to the legacy
  Hermes home board.
- Added a regression check for dispatcher board selection.

## [1.3.3] - 2026-09-09
### Fixed
- Give the Hermes overlay folder to the hermes user at container start so
  named Docker volumes are writable and live tasks can begin.

## [1.3.2] - 2026-09-09
### Added
- Added the Hermes Kanban worker contract so claimed workers delegate
  implementation to the Pi harness instead of editing managed projects.

## [1.3.1] - 2026-09-09
### Changed
- Marked the old V0 plan as historical so agents follow the Pi harness
  path and do not restore the removed Hermes stage list.

## [1.3.0] - 2026-09-08
### Added
- Baked a Linux-runnable Pi 0.84.3 runtime into the Hermes image.
- Configured the live runtime to use the local OpenAI-compatible 9router endpoint
  and the DeepSeekFlash model through environment-provided credentials.

## [1.2.0] - 2026-09-08
### Fixed
- Adapted the live Pi subprocess transport to Pi's JSONL `prompt` command and
  settlement events while preserving one normalized Hermes result.
- Added offline coverage for prompt framing, structured-result extraction, and
  multiple-result rejection.

## [1.1.0] - 2026-09-08
### Added
- One-shot `pi --mode rpc` process execution with task-worktree cleanup.
- Strict timeout loading, executable runtime validation, and acknowledged
  legacy-work restart recovery.

## [1.0.2] - 2026-09-08
### Added
- Focused Pi playbook fixtures for conditional analyze omission and repeated
  implement/converge cycles.

## [1.0.1] - 2026-09-08
### Fixed
- Skip now records its assumptions and choice report before one continuation
  confirmation, while human parking fixtures cover implementation and later
  question batches.
### Added
- Focused isolation snapshots for the enrolled project, AiNative fixture,
  control-plane state, and sibling worktree.
### Removed
- Deleted the leftover empty legacy Spec Kit fixture tree.

## [1.0.0] - 2026-09-08
### Added
- Provider-neutral harness start/result records and the first Pi adapter.
- Whole-run human parking, retry, validation, and publication gating.
### Removed
- Hermes-owned Spec Kit stage execution and the legacy stage adapter.

## [0.9.1] - 2026-09-07
### Fixed
- Image Spec Kit manifests now include the implement lifecycle so the live runtime matches the fixture pin.
- Model HTTP failures report the status code instead of a generic parse error.

## [0.9.0] - 2026-09-07
### Added
- Spec Kit implementation handoff from native plan/task files through validation and recovery.
- Strict native handoff, implementation artifact, overlay, and runtime identity checks.
### Changed
- Full external runs continue past `PLANNING_COMPLETE` and publish only after validation passes.
- Retryable workspace fixes use Spec Kit `implement` with the configured implementation model.

## [0.8.1] - 2026-09-07
### Fixed
- Require a validated active external framework and matching runtime on the live entry path.
- Add scout-only, fail-closed provider, and byte-for-byte isolation checks.

## [0.8.0] - 2026-09-07
### Added
- Added the provider-neutral external framework contract and pinned GitHub Spec Kit adapter.
- Added isolated runtime bootstrap, native plan/task artifacts, planning-only completion, and fixture checks.
### Changed
- Live planning now runs AiNative discovery followed by Spec Kit plan and task generation through Hermes's configured model service.
- Retained native setup and artifact paths in the existing execution overlay without adding a task store.

## [0.7.7] - 2026-09-07
### Added
- Verified github.com SSH host keys that persist across container recreate (no ssh-keyscan, no accept-new).
- Optional runtime `GH_TOKEN` passthrough so the boot script can log the GitHub CLI in without storing a token in git.
### Changed
- GitHub CLI config is kept under the persisted Hermes home (`/opt/data/.config/gh`).

## [0.7.6] - 2026-09-07
### Fixed
- Live config loading now ignores full-line YAML comments.
- OpenAI-compatible execution requests non-streaming JSON and repeats the structured output contract in the user message.
- Fenced JSON model responses are accepted, while fully specified tasks are instructed not to ask routine clarification questions.
- The dispatcher now returns a failure code for `FAILED` and `BLOCKED` workflow records instead of reporting success.
- The Hermes image now includes the `gh` CLI required for pull-request operations.

## [0.7.5] - 2026-09-07
### Fixed
- Send a stable OpenCode session header (`x-opencode-session`) on live model calls so the gateway can route the request (live HTTP 400 was MissingSessionID).

## [0.7.4] - 2026-09-05
### Fixed
- Call `/v1/chat/completions` once when `OPENAI_BASE_URL` already ends in `/v1` (the live empty-body failure was `.../v1/v1/chat/completions` plus a 62KB prompt).
- Send only `index.html` and a few nearby notes to discovery, with a size cap.

## [0.7.3] - 2026-09-05
### Fixed
- Discovery (and other roles) receive a read-only snapshot of workspace file text. Discovery still cannot write or commit; implementation remains the write step.

## [0.7.2] - 2026-09-05
### Fixed
- Read OpenAI-compatible replies that append an SSE `data: [DONE]` trailer after one JSON object (the live 9router shape). Extra leftover after that object still fails closed.
- Ask the live model for one JSON object and no tools, and accept empty `files`/`commit` when they mean no writes.

## [0.7.1] - 2026-09-05
### Fixed
- Scoped smoke next-ready selection to the validated disposable project.
- Required smoke to execute a named or next-ready publish workflow after validation.
- Added a `main`-entry smoke refusal check with zero pushes and pull requests.

## [0.7.0] - 2026-09-05
### Added
- Read-only `SqliteTaskBoard` over Hermes' native `kanban.db`.
- One dispatcher/CLI entry for named, next-ready, resume, and guarded smoke runs.
- Hermetic live-bridge checks and a fail-closed named-repository smoke gate.
### Changed
- Kept the existing PIV, GitHub, Telegram, and recovery seams; no second task store or worker.

## [0.6.5] - 2026-09-05
### Added
- Enrolled the disposable quiz project `ich-mag-dich` at `/workspaces/ich-mag-dich`.

## [0.6.4] - 2026-09-05
### Removed
- Unenrolled and deleted the local `hermes-v0-sandbox` project so the control plane starts with no managed projects.
- Deleted the GitHub repository `emadpoursina/hermes-v0-sandbox`.

## [0.6.3] - 2026-09-04
### Fixed
- Use the mounted `/opt/data` path inside the container for Hermes state so the Kanban board survives service restarts.

## [0.6.2] - 2026-09-04
### Fixed
- Aligned the package version metadata and import test at `0.6.2`.
- Updated the workspace-manager default-config check for the enrolled sandbox path.

## [0.6.1] - 2026-09-03
### Fixed
- Rebuilt `hermes-agent:local` from one official Hermes image so Kanban workers no longer crash on a missing `opencode_provider_family` import.

## [0.6.0] - 2026-09-02
### Added
- Hermes web UI on http://localhost:9119 (chat and settings page) by publishing dashboard port 9119.
### Changed
- Stopped using Docker host networking so the web UI works on Mac Docker Desktop.

## [0.5.1] - 2026-09-02
### Fixed
- Point enrolled sandbox `location` at `/workspaces/hermes-v0-sandbox` (the real clone), not `/workspaces/sandbox`.

## [0.5.0] - 2026-09-02
### Added
- Phase 8 fixture end-to-end check: one board task through plan, implement, validate, simulated PR, and Telegram notices, plus interrupt/reclaim on the same identity.

## [0.4.0] - 2026-09-02
### Added
- Durable restart recovery with atomic execution snapshots and a 60-second liveness signal.
- Automatic reclaim of one interrupted workflow with safe phase restart and duplicate-worker prevention.
- Dirty working-copy recovery and local feature-branch recreation without network fetches.

### Changed
- Require `execution.overlay_dir` and keep the overlay on a persistent Compose volume.

## [0.1.0] - 2026-08-28
### Added
- Initial Hermes Kanban control-plane package scaffold.
