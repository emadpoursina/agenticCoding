"""Regression checks proving the removed whole-playbook path cannot run."""

from __future__ import annotations

from dataclasses import replace
from pathlib import Path

import pytest

from hermes_kanban import OverlaySnapshot, PivOrchestrator, write_overlay
from hermes_kanban.executor import ExecutionSettings
from hermes_kanban.external_framework import StepStartRequest, validate_step_request
from hermes_kanban.github import MemoryGitHost
from hermes_kanban.orchestrator import StepRecord
from test_piv_orchestrator import environment


def _superseded_record(finished, *, phase: str = "execution"):
    return replace(
        finished,
        state="RUNNING",
        current_phase=phase,
        current_worker="legacy",
        steps=finished.steps + (StepRecord("LEGACY", phase, "legacy"),),
    )


def test_legacy_execution_record_parks_without_starting_pi(tmp_path: Path) -> None:
    orchestrator, runtime, _workspace_root = environment(tmp_path)
    finished = orchestrator.run_workflow("fixture", "123")
    legacy = _superseded_record(finished, phase="execution")
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
    assert parked.legacy_migration_reason == "superseded by 018 — whole-playbook run"
    assert runtime.calls == []


@pytest.mark.parametrize("phase", ["execution", "validation", "github", "human"])
def test_whole_playbook_overlay_phases_all_park(tmp_path: Path, phase: str) -> None:
    orchestrator, runtime, _workspace_root = environment(tmp_path)
    finished = orchestrator.run_workflow("fixture", "123")
    legacy = _superseded_record(finished, phase=phase)
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


def test_legacy_acknowledgement_stays_parked_for_a_human(tmp_path: Path) -> None:
    orchestrator, runtime, _workspace_root = environment(tmp_path)
    finished = orchestrator.run_workflow("fixture", "123")
    legacy = _superseded_record(finished, phase="validation")
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

    acknowledged = restarted.resume_workflow("fixture", "123", "A")
    assert acknowledged.state == "HUMAN_DECISION_REQUIRED"
    assert acknowledged.legacy_acknowledged is True
    # Acknowledgement never migrates the record onto the 018 graph: the
    # loop cannot be resumed without a human choosing a fresh action.
    final = restarted.resume_workflow("fixture", "123", "A")
    assert final.state in {"FAILED", "HUMAN_DECISION_REQUIRED"}
    assert runtime.calls == []


def test_config_no_longer_defines_harness_playbook() -> None:
    settings = ExecutionSettings.from_config(Path(__file__).parents[1] / "config" / "default.yaml")
    assert not hasattr(settings, "harness_playbook")
    text = (Path(__file__).parents[1] / "config" / "default.yaml").read_text(encoding="utf-8")
    assert "playbook:" not in text
    assert "speckit-orchestrate" not in text


def test_every_live_entry_refuses_a_whole_playbook_request(tmp_path: Path) -> None:
    orchestrator, runtime, _workspace_root = environment(tmp_path)
    workspace = orchestrator.workspaces.workspace_root / "fixture" / "123"
    for step_id in ("speckit-orchestrate", "confirm", "uat", "publish", "unknown"):
        request = StepStartRequest(
            step_id=step_id,
            flow_id="flow-fixture",
            skill_path="docs/agents/ready/",
            workspace_path=workspace,
            workspace_branch="feature/task-123",
            model_profile="default",
            timeout_seconds=30.0,
            inputs={"task_id": "123", "task_problem": "p"},
        )
        with pytest.raises(Exception):
            orchestrator.executor.start_step(
                step_id,
                "fixture",
                "123",
                task=orchestrator.task_board.get("123"),
                flow_id="flow-fixture",
            )
        with pytest.raises(Exception):
            validate_step_request(request)
    assert runtime.calls == []
    assert isinstance(orchestrator.git_host, MemoryGitHost)
