# Phase 1 Data Model: Hermes onboarding contract (019)

Entities extracted from `spec.md ## Key Entities`, expressed against the
existing `hermes_kanban` types. Extension fields are marked **NEW**; reused
fields keep their current meaning.

## Entity: Feature Card

A top-level board card representing a desired outcome. Represented today as
a `BoardTask` row with `card_path == "feature"`; becomes a parent under the
new contract.

| Field | Source | Validation |
|-------|--------|------------|
| `id` | native board (`tasks.id`) | non-empty; validated by `SqliteTaskBoard` |
| `project_id` | native board → canonical via `registry.canonical_id` | must match enrolled project (FR-022) |
| `body headings` | `## Path` (`feature`/`change`/`job`), `## Profile`, `## Problem`, `## Expected Result`, `## Priority` | parsed by `board._sections`; profile per contract (see Contracts) |
| `parent_id` | — (always empty: top level) | must be absent |
| `children` | derived: board rows whose `parent_id == this id` | FR-023 |
| `profile` | **NEW** read of `## Profile` | role ∈ {task-generator, executor, validator} + named strategy; provider names rejected |
| lifecycle | native column (`todo`/`ready`/…/`done`) | completed only per parent-completion rule below |

**Completion rule (FR-012/028)**: complete ⟺ every child Task Card produced
by the task-generator is complete (board-authoritative; manual completion
counts) ∧ automated validator (critic ∧ tester) PASS ∧ no open raised gate.
Partial child sets never complete the parent.

**State transitions (orchestrator record, invisible on board)**:

```
queued → RUNNING → (planning sub-loop states) → tasks complete
       → decompose (children created on board)
       → AWAITING_CHILDREN  ⇄ children execution (each child its own record)
       → validator (critic, tester)
       → COMPLETED            # all children done + validator PASS + no gate
       → HUMAN_DECISION_REQUIRED / RETRYABLE_FAILURE / BLOCKED / FAILED  # as today
```

## Entity: Task Card

A child board card produced by the task-generator.

| Field | Source | Validation |
|-------|--------|------------|
| `id`, `project_id`, `priority`, `owner(assignee)`, `column` | native board | as today |
| `parent_id` | **NEW** read of `## Parent` body section (+ `task_links` row) | must reference an existing Feature Card on the same project (FR-023); fail-closed at creation |
| `dependencies` | existing union: `task_links` parents ∪ `## Dependencies` body parse (`_body_dependencies`) | unchanged |
| `profile` | `## Profile` (`executor` default) | same profile contract |
| execution | claimed by one executor via existing single workflow slot | FR-025: one card, one executor at a time |

## Entity: Primary Kanban Board

The single native board (`kanban.db`) the project is enrolled onto;
per-project visibility by project identity.

| Field | Source |
|-------|--------|
| `db_path` | `HERMES_HOME/kanban.db` (resolved read-only by `SqliteTaskBoard`; **NEW** recorded at onboarding as `OnboardResult.board_path`) |
| `cards` | Feature Cards + child Task Cards only (FR-009/FR-027); verified by inspection check |
| `project visibility` | `task.project_id` filter (existing `run_next_workflow`) |

## Entity: Project Identity

Resolved once at onboarding, idempotently (existing `run_onboard` + registry
entry). All fields already exist; one **NEW** result field.

| Field | Source |
|-------|--------|
| `repository` (owner/name) | `OnboardRequest`, `_OWNER_NAME` regex |
| `project_id` (derived) | `_derive_project_id` |
| `native_id` | `native_project_id` (single slug match; fail-closed) |
| `location` (workspace clone) | `workspace_root / project_id` |
| `default_branch` | request/config |
| `board_path` | **NEW** read-only check of the native `kanban.db` |

Validation: all 17 guarantees (FR-020) unchanged — idempotent re-run returns
identical identity, zero writes; conflicts fail closed.

## Entity: Execution Profile

A strategy attached to a card body; never a provider/vendor name.

| Field | Value |
|-------|-------|
| `role` | `task-generator` \| `executor` \| `validator` (FR-013) |
| `strategy_ref` | optional named reference (same rules as harness model profiles: non-empty, no `/`, no `\`) |
| `assignment` | auto-applied at card creation by Path (FR-014a): `feature` → project-default task-generator profile; `change`/`job` → their path-selected defaults; operator-overridable later |
| `forbidden` | any value matching the provider-leak pattern or a provider-style reference |

Defaults source: project config/overlay (`profiles.defaults`), fallback = the
role name itself. No invention beyond the project contract (FR-007).

## Entity: Workflow Record (orchestrator-owned, never a card)

Existing `WorkflowRecord` (durable via `persist.write_overlay`).

| Field | Status |
|-------|--------|
| existing fields (`state`, `current_phase`, `task`, `steps`, `state_attempts`, `resume_context`, `question_queue`, `decision`, …) | unchanged; retries (3/state), park, fail-closed preserved |
| `parent_task_id` | **NEW** `str \| None` — set on child records so parent re-evaluation can find them |
| `children` | **NEW** `tuple[str, ...]` — child ids captured at decomposition; truth re-derived from board on reclaim (D7) |
| `AWAITING_CHILDREN` | **NEW** record state between decomposition and validator; added to `_ACTIVE_STATES` and the persist phase allowlist |

## Entity: Gate Marker (comment on parked card)

Not a card; a comment/annotation written through the native CLI seam.

| Field | Value |
|-------|-------|
| `card_id` | the parked card (Feature or Task) |
| `gate kind` | `clarify` \| `confirm` \| `uat` \| `pr-review` \| `blocked` (from the existing park path) |
| `decision text` | rendered from the existing `DecisionBrief` (decision, why, options) |
| `resume hint` | `--resume <project> <task> <option>` |
| `resolution` | written as a closing note on resume/complete; stale open markers are never left |

## Entity: Decision Journal Entry (durability of manual-edit handling)

Append-only JSONL in `execution.overlay_dir/decisions.jsonl`.

| Field | Value |
|-------|-------|
| `ts` | clock timestamp |
| `kind` | `child-completed` \| `child-deleted` \| `parent-completed` \| `gate-raised` \| `gate-resolved` |
| `project_id`, `parent_id`, `child_id` | board ids as observed |
| `evidence` | board observation that justified the decision (column, presence/absence) |

## Entity: PRD Section → Feature Card (optional import)

Existing `import_prd` mapping (one `##` section → one card draft → one
native card via idempotency key). **NEW**: drafts composed with
`## Path: feature` + default `## Profile: task-generator`. Draft-only and
dry-run remain write-free.

## Validation rules summary (from spec)

- FR-009/FR-027: no card encodes an internal workflow state — enforced by
  card-body validation (Path/Profile/Parent are the only new sections; none
  may hold a state name) and by the inspection check.
- FR-014: provider/vendor profile values rejected — reused provider-leak +
  named-reference checks.
- FR-023: parent identifiable from any child — `## Parent` + `task_links`.
- FR-029: manual edits honored with board authoritative — re-scan + journal.
- FR-002/FR-003: onboarding idempotent, fail-closed — unchanged code paths.
