"""Hermetic parent-completion checks for the 019 feature lifecycle.

Fake-harness scaffolding mirroring `tests/test_piv_orchestrator.py`:
board seams with injectable card creation/note/complete functions and the
fixture Pi runtime. No live GitHub, Telegram, model, or operator board.
"""

from __future__ import annotations

import json
from dataclasses import replace
from pathlib import Path

import pytest

from hermes_kanban import OverlaySnapshot, write_overlay
from hermes_kanban.onboard import OnboardError, child_card_args
from hermes_kanban.orchestrator import (
    OrchestratorError,
    PivOrchestrator,
    WorkflowBusyError,
)
from hermes_kanban.persist import PersistError, read_overlay
from test_piv_orchestrator import (
    CHILD_RUN,
    PARENT_PLANNING,
    VALIDATOR_RUN,
    _runtime_class,
    environment,
)

FULL_RUN = PARENT_PLANNING + CHILD_RUN + CHILD_RUN + VALIDATOR_RUN
WORKFLOW_STATES = {
    "ready",
    "specify",
    "clarify",
    "confirm",
    "plan",
    "tasks",
    "implement",
    "converge",
    "critic",
    "tester",
    "uat",
    "pr-review",
    "publish",
}


def _children_of(orchestrator, parent_id: str = "123"):
    return [
        item for item in orchestrator.task_board.list() if item.parent_id == parent_id
    ]


def _journal_entries(orchestrator) -> list[dict[str, object]]:
    path = orchestrator.overlay_dir / "decisions.jsonl"
    if not path.exists():
        return []
    return [
        json.loads(line)
        for line in path.read_text(encoding="utf-8").splitlines()
        if line
    ]


def test_children_reference_their_parent_feature_card(tmp_path: Path) -> None:
    """FR-023: the parent is identifiable from any child."""
    orchestrator, _runtime, _workspace_root = environment(tmp_path)

    record = orchestrator.run_workflow("fixture", "123")

    children = _children_of(orchestrator)
    assert children
    assert record.task_id == "123"
    for child in children:
        assert child.parent_id == "123"
        assert orchestrator.task_board.get(child.id).parent_id == "123"
        assert child.profile == "executor"


def test_dangling_or_self_parent_fails_card_creation(tmp_path: Path) -> None:
    """FR-023: a dangling or self parent fails card creation fail-closed."""
    del tmp_path

    with pytest.raises(Exception, match="exactly one task id"):
        child_card_args("- [ ] thing\n", parent_id="", priority="P1", native_id="p")
    with pytest.raises(Exception, match="must not reference the card itself"):
        child_card_args("- [ ] 123\n", parent_id="123", priority="P1", native_id="p")


def test_child_cards_appear_independently_claimable(tmp_path: Path) -> None:
    """FR-011/016/025: children land on the same board and claim one at a time."""
    orchestrator, runtime, _workspace_root = environment(tmp_path)

    orchestrator.run_workflow("fixture", "123")
    children = _children_of(orchestrator)
    assert [child.card_path for child in children] == ["change", "change"]
    assert runtime.order[: len(PARENT_PLANNING)] == list(PARENT_PLANNING)

    # Each run_next_workflow claims exactly one child card (single slot).
    first = orchestrator.run_next_workflow("fixture")
    assert first.task_id in {child.id for child in children}
    assert first.state == "COMPLETED"
    assert orchestrator._record.task_id == "123"
    assert orchestrator._record.state == "AWAITING_CHILDREN"


def test_parent_completes_only_when_all_children_complete(tmp_path: Path) -> None:
    """FR-012 (with FR-029): completion = all non-deleted children + validator."""
    orchestrator, runtime, _workspace_root = environment(tmp_path)

    orchestrator.run_workflow("fixture", "123")
    children = _children_of(orchestrator)

    first = orchestrator.run_next_workflow("fixture")

    # One child executed and completed; the parent never completes early.
    assert first.task_id in {child.id for child in children}
    assert first.state == "COMPLETED"
    assert orchestrator.task_board.get("123").complete is False

    finished = orchestrator.run_next_workflow("fixture")

    assert finished.state == "COMPLETED"
    assert finished.task_id == "123"
    assert tuple(runtime.order) == FULL_RUN


def test_validator_belongs_to_the_feature_card_not_children(tmp_path: Path) -> None:
    """FR-026/FR-028: one feature-level validator; zero operator actions."""
    orchestrator, runtime, _workspace_root = environment(tmp_path)

    orchestrator.run_workflow("fixture", "123")
    orchestrator.run_next_workflow("fixture")
    finished = orchestrator.run_next_workflow("fixture")

    assert finished.state == "COMPLETED"
    # The validator sessions ran against the parent, after both children.
    assert runtime.order[-2:] == ["critic", "tester"]
    assert finished.task_id == "123"
    assert finished.validation_status == "pass"


def test_raised_gate_parks_with_a_visible_board_marker(tmp_path: Path) -> None:
    """FR-017/SC-006: gate marker on the parked card, resolved on the board."""
    gate_notes: list[tuple[str, str]] = []
    runtime = _runtime_class()(tester_acceptance_flag=True)
    orchestrator, _runtime, _workspace_root = environment(
        tmp_path, runtime=runtime, gate_notes=gate_notes
    )

    orchestrator.run_workflow("fixture", "123")
    orchestrator.run_next_workflow("fixture")
    parked = orchestrator.run_next_workflow("fixture")

    assert parked.state == "HUMAN_DECISION_REQUIRED"
    assert parked.current_phase == "uat"
    assert gate_notes, "the parked card must show a gate marker"
    card_id, text = gate_notes[-1]
    assert card_id == "123"
    assert "HERMES GATE — uat" in text
    assert "Decision needed" in text
    assert "A)" in text
    assert "--resume fixture 123" in text

    resolved = orchestrator.resume_workflow("fixture", "123", "A")

    assert resolved.state == "COMPLETED"
    closing = gate_notes[-1]
    assert closing[0] == "123"
    assert "GATE CLOSED" in closing[1]
    kinds = {entry["kind"] for entry in _journal_entries(orchestrator)}
    assert {"gate-raised", "gate-resolved"} <= kinds


def test_gate_marker_failure_surfaces_and_leaves_the_park_unchanged(
    tmp_path: Path,
) -> None:
    """FR-017: a marker CLI failure surfaces; the park state is unchanged."""
    gate_notes: list[tuple[str, str]] = []
    runtime = _runtime_class()(tester_acceptance_flag=True)

    def failing_note(card_id: str, text: str) -> None:
        gate_notes.append((card_id, text))
        raise OnboardError(f"kanban comment failed for {card_id}")

    orchestrator, _runtime, _workspace_root = environment(
        tmp_path, runtime=runtime, gate_notes=gate_notes
    )
    orchestrator.card_note_fn = failing_note

    orchestrator.run_workflow("fixture", "123")
    orchestrator.run_next_workflow("fixture")

    with pytest.raises(OnboardError, match="kanban comment failed"):
        orchestrator.run_next_workflow("fixture")

    record = orchestrator._record
    assert record is not None
    assert record.state == "HUMAN_DECISION_REQUIRED"
    assert record.current_phase == "uat"
    # No silent bypass: the gate was never recorded as resolved.
    kinds = {entry["kind"] for entry in _journal_entries(orchestrator)}
    assert "gate-resolved" not in kinds


def test_blocked_gate_parks_durably_with_a_marker(tmp_path: Path) -> None:
    """FR-017: stable blocked states park and are surfaced on the board."""
    gate_notes: list[tuple[str, str]] = []
    runtime = _runtime_class()(ready_blocked=True)
    orchestrator, _runtime, _workspace_root = environment(
        tmp_path, runtime=runtime, gate_notes=gate_notes
    )

    record = orchestrator.run_workflow("fixture", "123")

    assert record.state == "BLOCKED"
    assert gate_notes
    card_id, text = gate_notes[-1]
    assert card_id == "123"
    assert "HERMES GATE" in text
    assert "--resume fixture 123" in text


def test_zero_children_leaves_the_parent_open(tmp_path: Path) -> None:
    """Edge case (a): no children produced = no empty completion."""
    runtime = _runtime_class()(empty_tasks=True)
    orchestrator, runtime, _workspace_root = environment(tmp_path, runtime=runtime)

    blocked = orchestrator.run_workflow("fixture", "123")

    assert blocked.state == "BLOCKED"
    assert "no child cards" in (blocked.error or "")
    assert orchestrator.task_board.get("123").complete is False
    assert _children_of(orchestrator) == []


def test_child_failure_never_completes_the_parent(tmp_path: Path) -> None:
    """Edge case (b): a failed child parks/retries alone; the parent stays open."""
    gate_notes: list[tuple[str, str]] = []
    orchestrator, _runtime, _workspace_root = environment(tmp_path, gate_notes=gate_notes)

    orchestrator.run_workflow("fixture", "123")
    children = _children_of(orchestrator)
    orchestrator.task_board.set_column(children[0].id, "done")
    # The second child is parked for review (a manual park on the board).
    orchestrator.task_board.set_column(children[1].id, "review")

    with pytest.raises(Exception):
        orchestrator.run_next_workflow("fixture")

    assert orchestrator.task_board.get("123").complete is False
    assert orchestrator.task_board.get(children[0].id).complete is True


def test_manual_edits_are_journaled_with_board_evidence(tmp_path: Path) -> None:
    """FR-029/SC-007: manual completions and deletions are recorded durably."""
    orchestrator, _runtime, _workspace_root = environment(tmp_path)

    orchestrator.run_workflow("fixture", "123")
    children = _children_of(orchestrator)
    orchestrator.task_board.set_column(children[0].id, "done")
    orchestrator.task_board.remove(children[1].id)

    finished = orchestrator.run_next_workflow("fixture")

    assert finished.state == "COMPLETED"
    entries = _journal_entries(orchestrator)
    kinds = [entry["kind"] for entry in entries]
    assert kinds.count("child-completed") == 1
    assert kinds.count("child-deleted") == 1
    assert kinds.count("parent-completed") == 1
    deleted = next(entry for entry in entries if entry["kind"] == "child-deleted")
    assert deleted["child_id"] == children[1].id
    assert deleted["parent_id"] == "123"
    assert deleted["evidence"]


def test_journal_failure_halts_evaluation_fail_closed(
    tmp_path: Path,
    monkeypatch,
) -> None:
    """A1: one journal-failure behavior — halt and retry, never complete."""

    def failing_append(directory, entry):
        raise PersistError(f"cannot append decision journal: {directory}")

    monkeypatch.setattr("hermes_kanban.orchestrator.append_decision", failing_append)
    orchestrator, _runtime, _workspace_root = environment(tmp_path)

    orchestrator.run_workflow("fixture", "123")
    children = _children_of(orchestrator)
    for child in children:
        orchestrator.task_board.set_column(child.id, "done")

    with pytest.raises(OrchestratorError, match="decision journal"):
        orchestrator.run_next_workflow("fixture")

    # The evaluation halted: the parent is not completed and no decision was
    # lost silently; the next scan retries the evaluation.
    assert orchestrator.task_board.get("123").complete is False
    assert not (orchestrator.overlay_dir / "decisions.jsonl").exists()


def test_confirm_and_uat_stay_silent_absent_a_raise(tmp_path: Path) -> None:
    """T021/FR-028: no confirm/uat park when nothing is raised."""
    orchestrator, runtime, _workspace_root = environment(tmp_path)

    finished = orchestrator.run_next_workflow("fixture")
    final = orchestrator.run_next_workflow("fixture")
    del finished, final

    assert "confirm" not in runtime.order
    assert "uat" not in runtime.order


def test_skip_flag_still_confirms_before_plan(tmp_path: Path) -> None:
    """Existing skip behavior unchanged (T021)."""
    runtime = _runtime_class()(question=True)
    gate_notes: list[tuple[str, str]] = []
    orchestrator, runtime, _workspace_root = environment(
        tmp_path, runtime=runtime, gate_notes=gate_notes
    )

    parked = orchestrator.run_workflow("fixture", "123", operator_flags=("skip",))

    assert parked.state == "HUMAN_DECISION_REQUIRED"
    assert parked.current_phase == "confirm"
    assert gate_notes
    text = gate_notes[-1][1]
    assert "HERMES GATE" in text
    assert "Continue to planning" in text
    assert "--resume fixture 123" in text

    finished = orchestrator.resume_workflow("fixture", "123", "A")

    assert finished.state == "AWAITING_CHILDREN"


def test_mid_feature_board_shows_only_work_cards(tmp_path: Path) -> None:
    """FR-027/SC-002: mid-feature, only Feature and Task Cards exist."""
    orchestrator, _runtime, _workspace_root = environment(tmp_path)

    orchestrator.run_workflow("fixture", "123")
    orchestrator.run_next_workflow("fixture")

    for item in orchestrator.task_board.list():
        assert item.card_path in {"feature", "change", "job"}
        assert item.card_path.casefold() not in WORKFLOW_STATES
        assert (item.profile or "").casefold() not in WORKFLOW_STATES
        assert item.id not in WORKFLOW_STATES


def test_restart_resumes_from_board_and_overlay_at_decomposition(
    tmp_path: Path,
) -> None:
    """SC-004 (a): interrupted right after decomposition."""
    orchestrator, runtime, _workspace_root = environment(tmp_path)

    awaiting = orchestrator.run_workflow("fixture", "123")
    assert awaiting.state == "AWAITING_CHILDREN"

    restarted = _restart(orchestrator)
    resumed = restarted.become_ready()

    assert resumed is not None
    assert resumed.state == "AWAITING_CHILDREN"
    assert resumed.task_id == "123"
    assert runtime.order.count("ready") == 1  # no conversation reconstruction
    restarted.run_next_workflow("fixture")
    final = restarted.run_next_workflow("fixture")
    assert final.state == "COMPLETED"
    assert final.task_id == "123"


def test_restart_resumes_an_interrupted_child_execution(tmp_path: Path) -> None:
    """SC-004 (b): interrupted during child execution."""
    orchestrator, runtime, _workspace_root = environment(tmp_path)

    orchestrator.run_workflow("fixture", "123")
    child = _children_of(orchestrator)[0]
    child_running = replace(
        orchestrator.run_next_workflow("fixture"),
        state="RUNNING",
        current_phase="change",
        next_action="run the change step",
        steps=orchestrator._record.steps[:-1],
    )
    write_overlay(orchestrator.overlay_dir, OverlaySnapshot(child_running, "occupied"))
    (orchestrator.overlay_dir / "alive").unlink(missing_ok=True)

    restarted = _restart(orchestrator)
    reclaimed = restarted.become_ready()

    assert reclaimed is not None
    assert reclaimed.run_id == child_running.run_id
    # The child completed its interrupted step; the parent is re-evaluated.
    assert restarted.task_board.get(child.id).complete is True


def test_restart_resumes_the_validator(tmp_path: Path) -> None:
    """SC-004 (c): interrupted at the validator."""
    orchestrator, runtime, _workspace_root = environment(tmp_path)

    orchestrator.run_workflow("fixture", "123")
    for child in _children_of(orchestrator):
        orchestrator.task_board.set_column(child.id, "done")
    validator_running = replace(
        orchestrator.run_next_workflow("fixture"),
        state="RUNNING",
        current_phase="critic",
        next_action="run the critic step",
        steps=orchestrator._record.steps[:-1],
    )
    write_overlay(
        orchestrator.overlay_dir, OverlaySnapshot(validator_running, "occupied")
    )
    (orchestrator.overlay_dir / "alive").unlink(missing_ok=True)

    restarted = _restart(orchestrator)
    reclaimed = restarted.become_ready()

    assert reclaimed is not None
    assert reclaimed.task_id == "123"
    assert reclaimed.state == "COMPLETED"


def test_restart_resumes_parked_gates_from_board_and_overlay(tmp_path: Path) -> None:
    """SC-004 (d): interrupted at a park point."""
    runtime = _runtime_class()(question=True)
    orchestrator, runtime, _workspace_root = environment(tmp_path, runtime=runtime)

    parked = orchestrator.run_workflow("fixture", "123")
    assert parked.state == "HUMAN_DECISION_REQUIRED"

    restarted = _restart(orchestrator)
    resumed = restarted.become_ready()

    assert resumed is not None
    assert resumed.state == "HUMAN_DECISION_REQUIRED"
    assert resumed.current_phase == "clarify"
    finished = restarted.resume_workflow("fixture", "123", "A")
    assert finished.state == "AWAITING_CHILDREN"


def _restart(orchestrator) -> PivOrchestrator:
    """Re-instantiate the orchestrator on the same overlay (restart)."""
    (orchestrator.overlay_dir / "alive").unlink(missing_ok=True)
    return PivOrchestrator(
        orchestrator.executor,
        orchestrator.workspaces,
        orchestrator.registry,
        orchestrator.task_board,
        orchestrator.git_host,
        overlay_dir=orchestrator.overlay_dir,
        harness_adapter=orchestrator.harness_adapter,
        card_creator=orchestrator.card_creator,
        card_note_fn=orchestrator.card_note_fn,
        card_complete_fn=orchestrator.card_complete_fn,
    )


def test_single_executor_holds_the_workflow_slot(tmp_path: Path) -> None:
    """FR-025: one card, one executor at a time (single workflow slot)."""
    orchestrator, _runtime, _workspace_root = environment(tmp_path)

    orchestrator.run_workflow("fixture", "123")
    orchestrator.run_next_workflow("fixture")
    # An in-flight executor occupies the single workflow slot.
    busy = replace(
        orchestrator._require_record(),
        state="RUNNING",
        current_phase="change",
    )
    orchestrator._record = busy
    write_overlay(orchestrator.overlay_dir, OverlaySnapshot(busy, "occupied"))

    with pytest.raises(WorkflowBusyError):
        orchestrator.run_next_workflow("fixture")

    assert orchestrator.task_board.get("123").complete is False


def test_deleted_children_are_never_restored_or_demoted(tmp_path: Path) -> None:
    """FR-029 manual-edit rule: deletion is accepted, never reverted."""
    orchestrator, _runtime, _workspace_root = environment(tmp_path)

    record = orchestrator.run_workflow("fixture", "123")
    children = _children_of(orchestrator)
    orchestrator.task_board.set_column(children[0].id, "done")
    orchestrator.task_board.remove(children[1].id)
    orchestrator.run_next_workflow("fixture")

    # A deleted child is not recreated; a completed child is not demoted.
    board_ids = {item.id for item in orchestrator.task_board.list()}
    assert children[1].id not in board_ids
    assert orchestrator.task_board.get(children[0].id).complete is True
    assert orchestrator.task_board.get("123").complete is True
    assert record is not None



def test_workflow_record_fields_round_trip_children(tmp_path: Path) -> None:
    """D7/persist: parent_task_id/children round-trip through the overlay."""
    orchestrator, _runtime, _workspace_root = environment(tmp_path)

    record = orchestrator.run_workflow("fixture", "123")
    write_overlay(orchestrator.overlay_dir, OverlaySnapshot(record, "free"))

    restored = read_overlay(orchestrator.overlay_dir)
    assert restored is not None and restored.record is not None
    assert restored.record.state == "AWAITING_CHILDREN"
    assert restored.record.children == ("card-002", "card-003")
    assert restored.record.parent_task_id is None
