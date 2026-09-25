# Implementation Plan: Hermes onboarding contract (Kanban as the user-facing work queue)

**Branch**: `hermes-onboarding-contract` | **Date**: 2026-09-23 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `specs/019-hermes-onboarding-contract/spec.md`

## Summary

Extend the Hermes onboarding contract so that after enrollment the project's
primary Kanban board is the user-facing work queue: operators submit desired
outcomes as top-level **Feature Cards**; the task-generator execution profile
runs the existing internal planning loop against a Feature Card and lands its
decomposition as child **Task Cards** on the same board; each child is
independently executable by one executor; an automated feature-level validator
(and any operator-raised human gate) completes the parent. Internal workflow
states (`ready…publish`) stay orchestrator-owned, durable, and invisible on
the board. All 17 existing onboarding guarantees and the 11 established
test behaviors are preserved. Implementation extends the existing
`hermes_kanban` package in place — `SqliteTaskBoard`, `BoardTask`,
`LoopState`, dependency parsing, park/retry/recovery, and harness model
profiles are reused; no second task database, no board redesign, no
orchestrator rewrite.

## Technical Context

**Language/Version**: Python 3.12 (`>=3.12,<3.14`) via uv (workspace standard)

**Primary Dependencies**: Python standard library only (sqlite3, subprocess,
dataclasses); native Hermes CLI (`hermes kanban`, `hermes project`) for all
board/project writes; Pi harness (`pi --mode rpc`) for agent states — no new
external dependencies.

**Storage**: existing native stores only — `kanban.db` (read-only through
`SqliteTaskBoard`), `projects.db` (read-only through `onboard.native_project_id`),
config + `enrolled-projects.yaml` overlay, orchestrator overlay records via
`persist.py` (`WorkflowRecord` snapshots + alive heartbeat). New: an
append-only decision journal file inside the existing `execution.overlay_dir`
(no second task database).

**Testing**: pytest + ruff (hermetic — no live GitHub, Telegram, model, or
operator board), matching `tests/test_onboarding.py` and
`tests/test_piv_orchestrator.py` patterns.

**Target Platform**: local/container Hermes control plane
(`python -m hermes_kanban --config …`); macOS dev, container runtime.

**Performance Goals**: n/a — single worker, `max_concurrent_tasks` is 1; one
workflow slot per install.

**Constraints**: fail-closed on identity conflicts; dry-run writes nothing;
AiNative read-only; no workflow-state cards on the board; no conversation
reconstruction on restart; provider/vendor names never appear as profiles.

**Scale/Scope**: one install, one native board, one active workflow at a
time; a Feature Card decomposes to a handful of child Task Cards.

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle | Check | Result |
|-----------|-------|--------|
| I. Spec-First | Written spec exists (clarified 2026-09-23); plan precedes tasks/implement | PASS |
| II. Least Code (Ponytail) | Reuse ladder applied in research.md: parent/child via existing `task_links` + body sections; retries/parks/recovery via existing `WorkflowRecord` machinery; profile validation via existing named-reference + provider-leak checks; decision durability via existing overlay dir (append file, not a DB) | PASS |
| III. Platform-Native Over Rebuild | All board writes stay on the native `hermes kanban` CLI; `SqliteTaskBoard` stays read-only; no second task database; AiNative remains read-only methodology | PASS |
| IV. Trust-Boundary Tests | Card body (`## Path`, `## Profile`, `## Parent`, `## Dependencies`) is external input — validated at the boundary; every new behavior FR-021..FR-029 gets one hermetic check; integration-style checks for the board↔orchestrator contract | PASS |
| V. Human Authority | Gates never silently bypassed; publish/merge/protected-branch rules untouched; scaffold commit/push remain opt-in | PASS |

Hard constraints honored: Python 3.12 via uv; no new dependencies; isolated
`~/.hermes/personal-agent` home; model routing stays in Hermes config (no
provider names in agents); surgical edits only.

**Post-Phase-1 re-check**: PASS — no design artifact introduces a second
task database, a provider abstraction, or a new workflow-state card type.
One recorded collision (existing unconditional `confirm`/`uat` parks vs.
FR-028) is resolved in Complexity Tracking below.

## Project Structure

### Documentation (this feature)

```text
specs/019-hermes-onboarding-contract/
├── plan.md              # This file
├── research.md          # Phase 0 output — decisions & rationale
├── data-model.md        # Phase 1 output — entities, fields, transitions
├── quickstart.md        # Phase 1 output — runnable validation guide
├── contracts/           # Phase 1 output — interface contracts
│   ├── card-body.md     # Feature/Task card body headings & profile rules
│   ├── orchestrator.md  # Lifecycle, parent completion, decision journal
│   └── onboarding.md    # OnboardResult/CLI extension contract
└── tasks.md             # Phase 2 output (/speckit-tasks — NOT created here)
```

### Source Code (repository root)

```text
personalAgent/
├── src/hermes_kanban/
│   ├── onboard.py        # EXTEND: card-body profile/parent composition,
│   │                     #   board discoverability check, OnboardResult
│   ├── board.py          # EXTEND: expose parent link + Profile + Path
│   │                     #   sections on BoardTask (read-only, existing parse)
│   ├── orchestrator.py   # EXTEND: task-generator/executor/validator wiring,
│   │                     #   parent-completion evaluation, decision journal
│   ├── executor.py       # EXTEND: profile-for-role resolution (named refs)
│   ├── external_framework.py  # EXTEND: role allowlist + provider-name rejection
│   ├── runtime.py        # EXTEND: report lines for board/parent state
│   └── persist.py        # EXTEND: journal + new record phase allowlist
└── tests/
    ├── test_onboarding.py          # PRESERVED (17 guarantees, 11 behaviors)
    ├── test_onboarding_contract.py # NEW: FR-021..FR-029 hermetic checks
    └── test_feature_parent_completion.py  # NEW: lifecycle + manual-edit rules
```

**Structure Decision**: Single-package extension. Every change lands in the
existing `hermes_kanban` modules listed above; no new subpackage, no new
module graph. The two new test files mirror the existing hermetic style
(fixture `kanban.db`, `MemoryTaskBoard`, fake cloners/creators).

## Complexity Tracking

> Recorded collisions only.

| Violation / Collision | Why Needed | Resolution Recorded |
|-----------------------|------------|---------------------|
| Existing loop parks `confirm` unconditionally before `plan` (and `uat` after tester) vs. FR-028 "completion MUST NOT wait on a human absent a raised gate" | The feature loop's human states predate the Kanban contract | The loop *raises* `confirm`/`uat` only when the step report or verdict flags unresolved questions / acceptance items; otherwise the automated validator passes without parking. Existing `skip` flag behavior is unchanged. (Rung 2 reuse: same states, same park path, narrower trigger.) |
| Spec says "single native board" while native Hermes keys cards by `project_id` | Per-project visibility is by project identity, not per-project boards | No code change: `run_next_workflow` already filters by `task.project_id`; onboarding records the native board for discoverability (FR-021) instead of creating one |
| FR-012 "ALL child Task Cards produced by the task-generator are required" vs. FR-029 "manual deletion of a child MUST trigger re-evaluation of the parent" | Read literally, a deleted child makes "all children" unsatisfiable forever | Resolution (implemented): the completion requirement set is **all non-deleted children** — a child deleted from the board is dropped from the requirement set and the deletion is journaled (`child-deleted`); the parent completes when every non-deleted child is complete ∧ the automated validator passes ∧ no open raised gate. Asserted in `tests/test_feature_parent_completion.py`. |

