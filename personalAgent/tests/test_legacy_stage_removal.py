"""Regression checks proving the removed Hermes stage machine cannot run."""

from __future__ import annotations

from dataclasses import replace
from pathlib import Path

from hermes_kanban import OverlaySnapshot, PivOrchestrator, write_overlay
from hermes_kanban.orchestrator import StepRecord
from test_piv_orchestrator import environment


def test_historical_planning_record_is_parked_without_starting_pi(tmp_path: Path) -> None:
    orchestrator, runtime, _workspace_root = environment(tmp_path)
    finished = orchestrator.run_workflow("fixture", "123")
    legacy = replace(
        finished,
        state="PLANNING_COMPLETE",
        current_phase="planning",
        current_worker="legacy",
        steps=finished.steps + (StepRecord("PLANNING_COMPLETE", "planning", "legacy"),),
    )
    write_overlay(orchestrator.overlay_dir, OverlaySnapshot(legacy, "occupied"))
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
    parked = restarted.become_ready()

    assert parked is not None
    assert parked.state == "HUMAN_DECISION_REQUIRED"
    assert parked.legacy_migration_reason
    assert runtime.calls == []


def test_legacy_acknowledgement_waits_for_restart_then_reclaims_generically(
    tmp_path: Path,
) -> None:
    orchestrator, runtime, _workspace_root = environment(tmp_path)
    finished = orchestrator.run_workflow("fixture", "123")
    legacy = replace(
        finished,
        state="PLANNING_COMPLETE",
        current_phase="planning",
        current_worker="legacy",
        steps=finished.steps + (StepRecord("PLANNING_COMPLETE", "planning", "legacy"),),
    )
    write_overlay(orchestrator.overlay_dir, OverlaySnapshot(legacy, "occupied"))
    (orchestrator.overlay_dir / "alive").unlink(missing_ok=True)
    runtime.calls.clear()

    parked_orchestrator = PivOrchestrator(
        orchestrator.executor,
        orchestrator.workspaces,
        orchestrator.registry,
        orchestrator.task_board,
        orchestrator.git_host,
        overlay_dir=orchestrator.overlay_dir,
        harness_adapter=orchestrator.harness_adapter,
    )
    parked = parked_orchestrator.become_ready()
    assert parked is not None

    acknowledged = parked_orchestrator.resume_workflow("fixture", "123", "A")
    assert acknowledged.state == "QUEUED"
    assert acknowledged.legacy_migration_reason is None
    assert acknowledged.legacy_acknowledged is True
    assert acknowledged.decision is None
    assert runtime.calls == []
    assert parked_orchestrator.resume_workflow("fixture", "123", "A") == acknowledged

    (orchestrator.overlay_dir / "alive").unlink(missing_ok=True)
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
    assert reclaimed.legacy_acknowledged is True
