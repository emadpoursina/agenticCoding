"""Overlay restart and resume-context checks."""

from __future__ import annotations

import json
from dataclasses import replace
from pathlib import Path

from hermes_kanban import OverlaySnapshot, read_overlay, write_overlay
from hermes_kanban.external_framework import ResumeContext
from hermes_kanban.orchestrator import PivOrchestrator
from test_piv_orchestrator import environment


def test_resume_context_round_trip(tmp_path: Path) -> None:
    orchestrator, _runtime, _workspace_root = environment(tmp_path)
    parked = orchestrator.run_workflow("fixture", "123")
    record = replace(
        parked,
        resume_context=ResumeContext(
            answers=("A",),
            assumptions=("Use current scope",),
            continue_confirmed=False,
            prior_reason="answer required",
        ),
    )
    write_overlay(orchestrator.overlay_dir, OverlaySnapshot(record, "occupied"))

    restored = read_overlay(orchestrator.overlay_dir)

    assert restored is not None and restored.record is not None
    assert restored.record.resume_context is not None
    assert restored.record.resume_context.assumptions == ("Use current scope",)


def test_overlay_never_reloads_a_temporary_file(tmp_path: Path) -> None:
    orchestrator, _runtime, _workspace_root = environment(tmp_path)
    parked = orchestrator.run_workflow("fixture", "123")
    write_overlay(orchestrator.overlay_dir, OverlaySnapshot(parked, "free"))
    (orchestrator.overlay_dir / "overlay.json.tmp").write_text(
        json.dumps({"schema": "v0", "slot": "occupied", "record": {"run_id": "bad"}}),
        encoding="utf-8",
    )

    restored = read_overlay(orchestrator.overlay_dir)

    assert restored is not None and restored.record is not None
    assert restored.record.run_id == parked.run_id


def test_reclaim_resumes_the_interrupted_step(tmp_path: Path) -> None:
    orchestrator, runtime, _workspace_root = environment(tmp_path)
    orchestrator.run_workflow("fixture", "123")
    # A child card interrupted during its tester step re-enters that step.
    children = [
        item for item in orchestrator.task_board.list() if item.parent_id == "123"
    ]
    child_running = replace(
        orchestrator.run_next_workflow("fixture"),
        state="RUNNING",
        current_phase="tester",
        next_action="run the tester step",
        steps=orchestrator._record.steps[:-1],
    )
    write_overlay(orchestrator.overlay_dir, OverlaySnapshot(child_running, "occupied"))
    (orchestrator.overlay_dir / "alive").unlink(missing_ok=True)
    runtime.calls.clear()
    restarted = PivOrchestrator(
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

    reclaimed = restarted.become_ready()

    assert reclaimed is not None
    assert len(runtime.calls) == 1
    assert reclaimed.run_id == child_running.run_id
    del children
