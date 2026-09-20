"""Overlay restart and resume-context checks."""

from __future__ import annotations

import json
from dataclasses import replace
from pathlib import Path

from hermes_kanban import OverlaySnapshot, read_overlay, write_overlay
from hermes_kanban.external_framework import HarnessResult, ResumeContext
from hermes_kanban.orchestrator import PivOrchestrator
from test_piv_orchestrator import environment


def test_harness_result_and_resume_context_round_trip(tmp_path: Path) -> None:
    orchestrator, _runtime, _workspace_root = environment(tmp_path)
    finished = orchestrator.run_workflow("fixture", "123")
    record = replace(
        finished,
        state="HUMAN_DECISION_REQUIRED",
        current_phase="human",
        decision=None,
        harness_result=HarnessResult(
            "needs_human",
            "answer required",
            next_action="reply",
            questions=("Choose",),
            resume_context=ResumeContext(
                answers=("A",),
                assumptions=("Use current scope",),
                continue_confirmed=False,
                prior_reason="answer required",
            ),
            harness_id="pi",
        ),
        resume_context=ResumeContext(
            answers=("A",),
            assumptions=("Use current scope",),
            continue_confirmed=False,
            prior_reason="answer required",
        ),
        legacy_acknowledged=True,
    )
    write_overlay(orchestrator.overlay_dir, OverlaySnapshot(record, "occupied"))

    restored = read_overlay(orchestrator.overlay_dir)

    assert restored is not None and restored.record is not None
    assert restored.record.harness_result is not None
    assert restored.record.harness_result.status == "needs_human"
    assert restored.record.resume_context is not None
    assert restored.record.resume_context.assumptions == ("Use current scope",)
    assert restored.record.legacy_acknowledged is True


def test_overlay_never_reloads_a_temporary_file(tmp_path: Path) -> None:
    orchestrator, _runtime, _workspace_root = environment(tmp_path)
    finished = orchestrator.run_workflow("fixture", "123")
    write_overlay(orchestrator.overlay_dir, OverlaySnapshot(finished, "free"))
    (orchestrator.overlay_dir / "overlay.json.tmp").write_text(
        json.dumps({"schema": "v0", "slot": "occupied", "record": {"run_id": "bad"}}),
        encoding="utf-8",
    )

    restored = read_overlay(orchestrator.overlay_dir)

    assert restored is not None and restored.record is not None
    assert restored.record.run_id == finished.run_id


def test_reclaim_uses_another_whole_harness_run(tmp_path: Path) -> None:
    orchestrator, runtime, _workspace_root = environment(tmp_path)
    finished = orchestrator.run_workflow("fixture", "123")
    interrupted = replace(
        finished,
        state="RUNNING",
        current_phase="execution",
        next_action="run harness",
        pull_request=None,
        steps=finished.steps[:1],
    )
    write_overlay(orchestrator.overlay_dir, OverlaySnapshot(interrupted, "occupied"))
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
    )

    reclaimed = restarted.become_ready()

    assert reclaimed is not None
    assert len(runtime.calls) == 1
    assert reclaimed.run_id == finished.run_id
