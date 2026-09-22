"""US1/FR-004/SC-002: no later-step leakage in prompts; refusals at the boundary."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from hermes_kanban.external_framework import (
    StepStartRequest,
    load_harness_runtime,
    step_skill_path,
    validate_step_request,
)
from hermes_kanban.pi import PiHarnessAdapter
from test_piv_orchestrator import environment

LATER_STATES = ("clarify", "confirm", "plan", "tasks", "implement", "converge", "publish")


def _runtime_marker():
    runtime_path = Path(__file__).parent / "fixtures" / "pi-runtime"
    return load_harness_runtime(
        adapter_id="pi",
        path_env="HERMES_PI_RUNTIME",
        environ={"HERMES_PI_RUNTIME": str(runtime_path)},
    )


def _request(workspace: Path, step_id: str) -> StepStartRequest:
    return StepStartRequest(
        step_id=step_id,
        flow_id="flow-fixture",
        skill_path=step_skill_path(step_id),
        workspace_path=workspace,
        workspace_branch="feature/task-123",
        model_profile="default",
        timeout_seconds=30.0,
        inputs={"task_id": "123", "task_problem": "Build the fixture"},
    )


def test_specify_prompt_names_only_specify(tmp_path, monkeypatch) -> None:
    workspace = tmp_path / "worktree"
    workspace.mkdir()
    record_path = tmp_path / "process-record.json"
    monkeypatch.setenv("PI_FIXTURE_RECORD", str(record_path))
    monkeypatch.setenv("PI_FIXTURE_MODE", "still-running-after-result")

    result = PiHarnessAdapter.from_runtime(_runtime_marker()).start(
        _request(workspace, "specify")
    )

    assert result.status == "completed"
    details = json.loads(record_path.read_text(encoding="utf-8"))
    message = details["command"]["message"]
    job = details["job"]
    assert job["step_id"] == "specify"
    assert job["skill"] == step_skill_path("specify")
    assert "specify" in message
    for later in LATER_STATES:
        assert f"speckit-{later}" not in message
    assert "then run" not in message.lower()


@pytest.mark.parametrize(
    "step_id", ["speckit-orchestrate", "confirm", "uat", "publish", "unknown-step"]
)
def test_playbook_and_non_agent_requests_are_refused(tmp_path, step_id: str) -> None:
    workspace = tmp_path / "worktree"
    workspace.mkdir()
    with pytest.raises(Exception):
        validate_step_request(_request(workspace, step_id))


def test_prompt_includes_the_fixed_safety_constraints(tmp_path, monkeypatch) -> None:
    workspace = tmp_path / "worktree"
    workspace.mkdir()
    record_path = tmp_path / "process-record.json"
    monkeypatch.setenv("PI_FIXTURE_RECORD", str(record_path))
    monkeypatch.setenv("PI_FIXTURE_MODE", "still-running-after-result")

    PiHarnessAdapter.from_runtime(_runtime_marker()).start(_request(workspace, "specify"))

    details = json.loads(record_path.read_text(encoding="utf-8"))
    constraints = details["job"]["constraints"]
    assert constraints == {
        "write_root": ".",
        "feature_branch_only": True,
        "allow_publish": False,
        "allow_protected_branch": False,
        "allow_external_writes": False,
        "reject_secrets": True,
    }


def test_live_dispatcher_refuses_a_whole_playbook_job(tmp_path) -> None:
    orchestrator, runtime, _workspace_root = environment(tmp_path)
    task = orchestrator.task_board.get("123")
    workspace = orchestrator.workspaces.workspace_root / "fixture" / "123"
    request = StepStartRequest(
        step_id="speckit-orchestrate",
        flow_id="flow-fixture",
        skill_path=".cursor/skills/speckit-specify/SKILL.md",
        workspace_path=workspace,
        workspace_branch="feature/task-123",
        model_profile="default",
        timeout_seconds=30.0,
        inputs={"task_id": "123", "task_problem": "Build the fixture"},
    )
    with pytest.raises(Exception):
        orchestrator.executor.start_step(
            "speckit-orchestrate",
            "fixture",
            "123",
            task=task,
            flow_id="flow-fixture",
        )
    with pytest.raises(Exception):
        validate_step_request(request)
    assert runtime.calls == []
