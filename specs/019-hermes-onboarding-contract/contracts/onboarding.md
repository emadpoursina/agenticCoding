# Contract: Onboarding extension (identity, board, card creation)

Owner module: `personalAgent/src/hermes_kanban/onboard.py` (+ `runtime.py`
report, `guide.py` interview). All 17 existing guarantees (FR-020) are
preserved byte-for-byte in behavior; this contract only adds.

## OnboardResult extension

```python
@dataclass(frozen=True)
class OnboardResult:
    # existing fields unchanged: project_id, repository, native_id, location,
    # default_branch, cloned, scaffolded, already_enrolled, drafts,
    # incomplete_drafts, created_cards, triaged_cards, pushed
    board_path: Path = ...   # NEW: resolved native board (read-only check)
```

- **FR-008/FR-021**: `run_onboard` fails closed with `OnboardError` if the
  native board database is missing/unreadable; otherwise returns its path.
- Idempotent re-run (guarantee 4): returns the same `board_path`, zero
  writes, zero diffs (SC-003).
- Dry-run (guarantee 13): the check is read-only; the projected primary-board
  result (board path, native id, would-be cards) is part of the printed plan;
  nothing is written.

## Card-creation composition (FR-014a, FR-019)

- `create_cards_from_drafts` / `guide.card_text` compose the body with:
  - `## Path` (feature/change/job — existing behavior for guide; `feature`
    default for PRD cards),
  - `## Profile` default role selected by Path (project defaults from
    config/overlay; fallback = role name),
  - `## Parent` (never for top-level cards).
- Values pass `validate_card_draft` (extended per `contracts/card-body.md`);
  provider/vendor profile values are rejected before any CLI call.

## CLI surface (`python -m hermes_kanban`)

- No new flags required for the contract; the enroll/import reports gain one
  line: `board: <path>` (FR-021).
- `--dry-run` unchanged: validates identity + board discoverability, writes
  nothing (existing guarantee).
- Operator override of a card profile happens on the board (edit the card's
  `## Profile` section) or via the existing card-creation flow; validation
  rules apply identically either way.

## Failure modes (fail-closed, FR-003)

| Condition | Behavior |
|-----------|----------|
| native board missing/unreadable | `OnboardError`, no enrollment, no scaffold |
| board write (card creation) fails mid-import | error propagates; already-created cards remain (per-card idempotency keys make a re-run safe) |
| gate marker CLI write fails | error surfaced; park state unchanged (retry by operator) |
| ambiguous native project / duplicate alias / mismatched re-enrollment | unchanged existing failures |

## Preserved guarantees cross-reference (FR-020)

owner/name validation · derived project id · single native slug match ·
idempotency · fail-closed conflicts · clone · validated reuse (origin/branch)
· scaffold only missing README/AGENTS/.ainative/project.yaml · single
control-plane section · scaffold commit message · opt-in push · config+overlay
fallback · dry-run writes nothing · PRD→cards · read-only AiNative · no
overwrite · no SYSTEM/USER context copying. The check suite in
`tests/test_onboarding.py` must keep passing unchanged.
