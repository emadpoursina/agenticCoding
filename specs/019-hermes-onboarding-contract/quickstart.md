# Quickstart: validating the Hermes onboarding contract (019)

Validation guide for the plan stage outputs. Everything here is hermetic —
no live GitHub, Telegram, model, or operator board (package rule). Full
implementation details live in [plan.md](./plan.md),
[data-model.md](./data-model.md), and [contracts/](./contracts/).

## Prerequisites

- Python 3.12 via uv in `personalAgent/` (workspace standard).
- Existing suite green: `tests/test_onboarding.py` (17 guarantees,
  11 behaviors) must pass untouched before any new check is added.

```bash
cd personalAgent
uv run pytest tests/test_onboarding.py -q   # baseline: must pass unchanged
```

## Scenario A — Onboarding guarantees preserved (US-2, FR-001..FR-007, FR-020)

1. Run the existing suite: `uv run pytest tests/test_onboarding.py -q`
2. Expected: all tests pass without modification; fixture `kanban.db`
   projects.db behavior unchanged.
3. New (FR-021): the fixture config now also yields `OnboardResult.board_path`
   pointing at a fixture board; a missing board fails closed.

## Scenario B — Feature Card end-to-end (US-1, FR-011/012/016, FR-021/022)

Hermetic flow using the fixture board + `MemoryTaskBoard`/fake CLI seams
(patterns from `tests/test_piv_orchestrator.py`):

1. Enroll a fixture project (fake cloner + fixture `projects.db` + board).
2. Create one Feature Card body with `## Path: feature` and the auto-composed
   `## Profile: task-generator` (asserted by `validate_card_draft`).
3. Drive the loop with a fake harness: `tasks` step completes with
   `specs/<id>/tasks.md` → child Task Cards appear on the board, each with
   `## Parent: <feature-id>` and `## Profile: executor`.
4. Complete every child (simulated executor runs).
5. Expected: validator states run on the parent; with PASS and no raised
   gate the parent completes with **zero** operator actions (FR-028).

## Scenario C — Board shows work, not workflow (US-3, FR-009/010, FR-027, SC-002)

1. Mid-run, list every card on the fixture board.
2. Assert: only Feature Cards and child Task Cards; zero cards whose
   Path/Profile encodes a workflow state name.
3. Restart the orchestrator mid-feature (new instance, same fixture
   overlay dir): record resumes from board + overlay; no workflow-state
   card appears; no conversation is reconstructed.

## Scenario D — Profiles, not providers (US-4, FR-013/014/014a)

1. Attempt card bodies with `## Profile: openai`, `## Profile: gpt-4`,
   `## Profile: some/provider` → all rejected fail-closed.
2. `## Profile: task-generator`, `## Profile: executor`,
   `## Profile: validator` (and `role:named-strategy`) accepted.
3. Feature Card created without a `## Profile` gets the Path-selected
   default; operator override later is honored.

## Scenario E — Human gates on the board (FR-017, SC-006)

1. Force a clarify/confirm/uat/blocked park via the fake harness.
2. Assert: a visible gate marker lands on the parked card (fake
   `live_add_card_note` seam records the call) with decision + resume hint.
3. Resolve via `resume_workflow` → closing note recorded; no stale open
   gate; zero silent bypasses.

## Scenario F — Manual board edits (FR-029, Q5, SC-007)

1. With a parent AWAITING_CHILDREN, mark one child `done` directly on the
   fixture board → re-evaluation counts it; `decisions.jsonl` gains a
   `child-completed` entry.
2. Delete one child from the fixture board → re-evaluation drops it and
   journals `child-deleted`; if the remaining set is satisfied the parent
   may complete.
3. All children satisfied + validator PASS → parent completes; journal
   records `parent-completed`.

## Scenario G — PRD import (US-5, FR-019)

1. Import a 2-section PRD with card creation (fake card creator): 2
   top-level Feature Cards on the native project, `## Path: feature`,
   default task-generator profile, none encoding a workflow state.
2. Same import draft-only: drafts are files; nothing hits the board.
3. `--dry-run`: nothing written anywhere (existing guarantee).

## Cross-checks

- FR-021..FR-029 each have one automated hermetic check
  (`tests/test_onboarding_contract.py`, `tests/test_feature_parent_completion.py`)
  that fails if the behavior regresses (SC-005).
- SC-003: re-running the onboarding fixture twice yields zero diffs
  (config bytes, board rows, scaffold files).
- SC-004: interruption at decomposition, child execution, validator, and
  park points all resume from board + overlay (fixture restart matrix).
