# Contract: Orchestrator lifecycle, parent completion, decision journal

Owner module: `personalAgent/src/hermes_kanban/orchestrator.py` (+
`persist.py` durability). The board (`kanban.db`, read via
`SqliteTaskBoard`) owns card identity and lifecycle; the orchestrator owns
workflow state. All writes to the board go through the native `hermes kanban`
CLI seams; `SqliteTaskBoard` stays read-only.

## Public seams (signatures the tasks stage must implement or extend)

```python
# orchestrator.py — new/extended public surface
def evaluate_parent(self, parent_id: str) -> WorkflowRecord:
    """Re-read the board and re-evaluate one Feature Card's children."""

def decompose_children(self, record: WorkflowRecord) -> WorkflowRecord:
    """After the tasks state, create child Task Cards from
    specs/<feature-id>/tasks.md and park the parent AWAITING_CHILDREN."""

def run_validator(self, record: WorkflowRecord) -> WorkflowRecord:
    """Run critic then tester against the parent when all children are done."""

# persist.py
def append_decision(directory: Path, entry: dict[str, object]) -> None:  # NEW
    """Append one JSONL line to <overlay_dir>/decisions.jsonl (fsync'd)."""
```

## Board seams (writes, all seam-injectable like `live_create_card`)

```python
# onboard.py — new seam beside live_create_card / _run_hermes
def live_add_card_note(card_id: str, text: str) -> None:
    """Post one visible gate marker/comment on a card via the native CLI."""
```

## Lifecycle (FR-016, FR-011/012)

1. **Feature Card claimed** — existing `run_workflow` path; profile =
   card `## Profile` else Path default (task-generator).
2. **Internal planning** — existing agent states; `_retry_or_park`
   (3 attempts/state), parks, fail-closed unchanged.
3. **Decompose** — on `tasks` completion with `specs/<id>/tasks.md`,
   child Task Cards are created on the same board (bodies per
   `contracts/card-body.md`, `## Parent` set, `## Path: change` — the short
   executor path `ready → change → tester`, `## Profile: executor`);
   idempotent via idempotency keys. Zero children produced = parent stays
   open, failure durable + surfaced (spec edge case; never empty-complete).
4. **AWAITING_CHILDREN** — orchestrator record state (durable overlay,
   invisible on board). Children are claimed independently by
   `run_next_workflow` (FR-025); a child failure parks/retries the *child*
   only; the parent stays open.
5. **Parent re-evaluation** — triggered when a child record completes, and
   at every `become_ready`/`resume_workflow`/`run_next_workflow` scan:
   - child column `done`/`archived` (including manual completion) counts;
   - child absent from the board (manual deletion) is dropped from the
     requirement set;
   - each observation appends a `decisions.jsonl` entry (FR-029).
6. **Validator** — when the required-child set is empty of incomplete
   members: run `critic` → `tester` on the parent (automated validator,
   FR-026/FR-028). PASS with no raised gate → `_complete` with zero human
   actions. A raised gate parks per the human-gate contract below.
7. **Human gates** — parks behave exactly as today; the parked card gets a
   visible marker (D5). Per-gate raise conditions (only `confirm`/`uat` are
   narrowed; every other gate behaves exactly as before):
   - `clarify` — parks whenever the clarify session reports `needs_human`
     questions (unchanged).
   - `confirm` — raised only when the completed clarify report still carries
     unresolved questions (non-empty report `questions`), or when clarify was
     self-answered under `skip` (skip behavior unchanged).
   - `uat` — raised only when the tester verdict (PASS) flags unresolved
     acceptance items or a blocked dependency in the verdict summary.
   - `pr-review` — unchanged: when the parent record runs the pr-review step
     it always parks for the operator's publish decision (human authority V).
     The automated parent-completion path ends at the validator and does not
     enter pr-review/publish; publishing a parent feature branch remains an
     explicit operator action (FR-028: absent a raised gate, completion
     MUST NOT wait on a human).
   - `blocked` — stable `READY: blocked`, blocked verdicts, and blocked
     recovery park exactly as today (unchanged).
   Gate resolution via the existing `resume_workflow` path; a closing note is
   posted on the card. Gate markers ride `live_add_card_note`: a marker CLI
   failure is surfaced and leaves the park state unchanged (operator retries).
8. **Completion** — `COMPLETED` record; board card done; journal records
   `parent-completed`.

## Journal failure semantics (fail-closed, one behavior)

`append_decision` is fail-closed: on a journal write failure the evaluation
that was recording the decision **halts and is retried by the next scan or
resume** — the parent is never completed past a lost decision, the park state
is left unchanged, and the failure is surfaced (raised as
`OrchestratorError`, never swallowed). One behavior, no per-call variation.

## Restart recovery (FR-018, SC-004)

`become_ready` reloads the overlay record; `_board_record` re-reads the
card; children truth is re-derived **from the board** (never from a
conversation or a stored status snapshot). `WorkflowRecord` **NEW** fields
`parent_task_id`, `children` and the **NEW** `AWAITING_CHILDREN` state are
round-tripped through the existing `_jsonable`/`_record_from_dict` path;
`persist._canonical_phase` gains `awaiting_children`.

## Durability rules

- `decisions.jsonl` lives in the existing `execution.overlay_dir`; no new
  database, no new config surface.
- Journal writes are append-only and never gate progress (a journal write
  failure is surfaced, not silently swallowed — fail-closed).
- The overlay slot/heartbeat semantics (`alive`, `SlotHeldError`) are
  unchanged.

## Manual-edit rule (FR-029, Q5)

Board authoritative, in priority order:
1. Manual completion of a child → counts toward the parent (board column is
   the evidence).
2. Manual deletion of a child → re-evaluation drops it; the parent may
   complete if the remaining set is satisfied; the deletion is journaled.
3. The orchestrator never "restores" a deleted child and never demotes a
   completed child; it records the decision and moves on.
