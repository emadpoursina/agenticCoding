# Phase 0 Research: Hermes onboarding contract (019)

Feature context: `specs/019-hermes-onboarding-contract/spec.md` — after
onboarding, the primary Kanban board is the user-facing work queue; Feature
Cards decompose into child Task Cards; the parent completes only when all
children complete and automated validation (plus raised gates) passes.
All NEEDS CLARIFICATION items were already resolved in
`spec.md ## Clarifications Session 2026-09-23`; this file records the
engineering decisions that satisfy them with the least code.

Every decision follows the Least Code ladder from the constitution: first
attempt to reuse an existing Hermes primitive (rung 2), stdlib (rung 3), or
the native Hermes CLI (rung 4) before proposing anything new.

## D1 — Parent/child representation

**Decision**: A child Task Card references its parent Feature Card with a
`## Parent` section in the card body containing the parent task id, and
additionally via the native `task_links(parent_id, child_id)` table where the
native board supports it. `SqliteTaskBoard._task` already unions
`task_links` parents with the `## Dependencies` body section into
`BoardTask.dependencies`; the plan adds a parallel, minimal read of the
`## Parent` section into a new `BoardTask.parent_id` field.

**Rationale**: FR-023 requires the parent to be identifiable from any child.
The card-body mechanism works even when the native board does not materialize
`task_links`, costs one regex-section parse (the `_sections` helper already
exists in `board.py`), and matches the spec assumption that parent/child
"reuses the existing card-body dependency/reference mechanisms rather than a
new schema."

**Alternatives considered**:
- New `task_children` table → rejected: second task database (constitution III).
- Only `task_links` → rejected: table presence is checked (`LIMIT 0`) but
  population depends on the native CLI; body reference is the fail-closed fallback.
- Only body `## Parent` → rejected: loses the native link when available.

## D2 — Board is authoritative for manual edits (Q5)

**Decision**: On every resume (`resume_workflow`) and every
`run_next_workflow` scan, the orchestrator re-reads the board and
re-evaluates open Feature Cards: a child that is now `done`/`archived`
counts toward the parent; a child that disappeared triggers
re-evaluation (its requirement is dropped and recorded). Each re-evaluation
appends one entry to a decision journal — an append-only JSONL file
`decisions.jsonl` inside the existing `execution.overlay_dir`:
`{ts, kind: "child-completed"|"child-deleted"|"parent-completed",
project_id, parent_id, child_id, evidence}`.

**Rationale**: FR-029 requires honoring board edits with the board as
authoritative and recording decisions durably. The orchestrator already
treats the board as truth at `become_ready`/`_board_record` (it re-reads
`task_board.get` and fails on mismatch); extending the same read-at-boundary
pattern costs no new state. The journal rides the existing overlay directory
(a plain file, not a database), preserving "no second task database."

**Alternatives considered**:
- Deriving children from `task_links` only → rejected: a deleted child leaves
  no row; deletion would be invisible.
- In-memory re-evaluation only → rejected: FR-029 requires durable recording.
- A second SQLite "decisions.db" → rejected (constitution III; hard constraint).

## D3 — Profiles: strategy, never a provider (Q1, FR-013/014/014a)

**Decision**:
- Card bodies gain an optional `## Profile` section. Allowed values are the
  three role names `task-generator`, `executor`, `validator`, optionally
  suffixed with a named strategy reference validated the same way existing
  model profiles are (named reference, no `/`, no `\`).
- Provider/vendor rejection reuses the two existing checks in
  `external_framework.py` / `executor.py`: the named-reference rule
  (`must be a named reference`, rejects path separators) and the
  `_PROVIDER_LEAK` regex (openai/anthropic/gpt/claude/vendor forms). A card
  whose `## Profile` value trips either rule is rejected at validation
  (fail-closed), matching FR-014.
- Auto-apply (FR-014a): at card creation, `onboard.create_cards_from_drafts`
  and `guide._add_card`/`card_text` compose `## Profile` into the body —
  default `task-generator` for `Path: feature`, and the path-selected
  default for `change`/`job` paths, sourced from project config
  (`profiles.defaults` in config/overlay, falling back to the role name
  itself). The operator may override the section value later; overrides pass
  through the same validator.

**Rationale**: Runtime/model selection already lives in
`ExecutionSettings.profile_for_step` and the harness `model_profile` config;
profiles on cards must therefore name strategy/roles only, which keeps the
dispatch model clean and reuses the existing named-reference plumbing
instead of inventing a new profile type.

**Alternatives considered**:
- Separate profile registry/file → rejected: extra artifact not requested;
  config + overlay fallback already exists (guarantee 12).
- Storing provider names in profiles and translating at dispatch → rejected:
  directly violates FR-014 and the constitution's model-routing rule.

## D4 — Lifecycle mapping onto the existing loop (FR-011/016/024/028)

**Decision**: The three execution roles map onto the existing
`PivOrchestrator` state machine with no new runtime:

| Role | Existing machinery it rides |
|------|-----------------------------|
| task-generator | The Feature Card runs the internal planning sub-loop (`ready → specify → clarify → confirm → plan → tasks`) as today; when the `tasks` state completes with `specs/<feature-id>/tasks.md`, the orchestrator parses that artifact into child Task Cards (existing `_artifact_for_step` seam) and creates them on the board via the existing `CardCreateFn`/`live_create_card` seam, each body carrying `## Parent`. The Feature Card then parks in a new orchestrator-owned record state `AWAITING_CHILDREN` (durable in the overlay, invisible on the board). |
| executor | Child Task Cards are ordinary runnable cards; `run_next_workflow` already selects by project, dependencies, and priority. One executor per card is the existing single-slot workflow (`_assert_slot_free`, `max_concurrent_tasks: 1`). |
| validator | After the last child completes, the orchestrator re-enters the parent record and runs the existing `critic` and `tester` verdict states against the parent worktree (feature-level validation, FR-026). PASS + no raised gate → `_complete`. `pr-review`/`publish` behavior is unchanged at parent level. |

`change` and `job` paths keep their existing short-path behavior
(`_after_short_path_step`, `_park_job`); the task-generator role applies to
`feature`-path Feature Cards (and path-selected defaults per D3).

**Rationale**: FR-016's lifecycle is exactly the existing graph with the
`tasks` state acting as the decomposition boundary and critic/tester as the
feature validator. Reusing `LoopState`, `_enter_state`, `_retry_or_park`
(3 attempts per state), `_park_step_human`, and `resume_workflow` preserves
FR-018 with zero new recovery code.

**Alternatives considered**:
- A new parallel "decomposition" engine → rejected: orchestrator rewrite
  forbidden by the spec assumptions and constitution.
- Children as sub-steps of one workflow slot → rejected: children must be
  independently claimable cards (FR-025).

## D5 — Human gates surfaced on the board (Q3, FR-017)

**Decision**: When the workflow parks (`_park_step_human`, clarify, confirm,
uat, pr-review, generic park), the orchestrator additionally writes one
visible comment/marker on the parked card through a new `live_add_card_note`
CLI seam (same shape as `live_create_card`: `hermes kanban …`, fail-closed,
seam-injectable for tests). The marker text is the existing
`DecisionBrief` rendered flat: gate kind, decision, options letters, and the
`--resume project task option` hint. Resolution stays on the existing
Telegram/board resume path (`resume_workflow`); on resume or completion the
orchestrator posts a resolution note (gate closed) so the board never shows
a stale open gate.

**Rationale**: FR-017 requires a visible marker on the parked card resolvable
there, and gates "ride the existing park/resume path" (spec assumptions).
The park record already holds everything the marker needs.

**Alternatives considered**:
- Encoding gates as board columns → rejected: workflow state on the board (FR-009).
- A separate gate file per card → rejected: invisible on the board.

## D6 — Primary board discoverability (FR-008, FR-021)

**Decision**: Onboarding already resolves `native_id` (the single native
project). `run_onboard` additionally verifies the native board database is
present and readable (`HERMES_HOME/kanban.db`, read-only) and returns its
path as a new `OnboardResult.board_path` field; absent board = fail-closed
`OnboardError`. The enroll report prints it. Idempotent re-runs return the
same path with no writes.

**Rationale**: FR-008/FR-021 need the board to exist and be discoverable from
the project's identity record. One read-only check + one result field.

**Alternatives considered**:
- Creating a per-project board → rejected: contradicts "one native board per
  install" (spec assumptions, AGENTS.md).

## D7 — Restart recovery (FR-018)

**Decision**: `WorkflowRecord` gains `parent_task_id: str | None` and
`children: tuple[str, ...]` (ids captured at decomposition); `persist.py`
round-trips them via the existing `_jsonable`/`_record_from_dict` path, with
the new `AWAITING_CHILDREN` phase added to the canonical-phase allowlist in
`persist._canonical_phase`. On `become_ready`, the existing `_board_record`
re-read plus a new children re-scan rebuilds completion state **from the
board**, never from a conversation: children missing from the board are
recorded in the journal per D2 and re-evaluation proceeds.

**Rationale**: SC-004 requires resume in 100% of interruption points with no
conversation reconstruction; the board is authoritative, so children truth is
re-derived, not replayed.

**Alternatives considered**:
- Persisting child status snapshots → rejected: would drift from the board
  (Q5 says board wins).

## D8 — PRD import (FR-019, US-5)

**Decision**: No structural change. `import_prd` → `create_cards_from_drafts`
already lands one top-level card per `##` PRD section on the native project;
the only addition is composing the `## Path: feature` + default
`## Profile: task-generator` sections (D3) so PRD cards are Feature Cards
under the new hierarchy. Draft-only mode and dry-run remain write-free
(existing guarantees 12/13).

**Alternatives considered**:
- Mapping PRD sections directly to child Task Cards → rejected: FR-019 says
  each section is a top-level Feature Card.

## D9 — Card body is a trust boundary

**Decision**: All new body sections (`Path`, `Profile`, `Parent`,
`Dependencies`, gate notes) are validated where cards enter the system:
`validate_card_draft` extended to check profile/parent shapes, and
`SqliteTaskBoard` continuing to tolerate/treat absent sections as defaults
(`card_path` already defaults to `feature`). Malformed `## Profile` or
`## Parent` values fail closed at creation/validation.

**Rationale**: Constitution IV (trust-boundary tests) and the existing
`validate_card_draft` behavior.

## Open items for Phase 2 (tasks)

None blocking. The `confirm`/`uat` trigger narrowing (Complexity Tracking)
is the only behavioral change to an existing state and should land as its
own task with its own hermetic check so the 17 guarantees remain provably
untouched.
