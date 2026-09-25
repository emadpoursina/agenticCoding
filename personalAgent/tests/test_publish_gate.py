"""US3: validation is critic then tester (validator) before completion; job
paths keep the unchanged critic/tester/uat/pr-review publish chain."""

from __future__ import annotations

import pytest

from hermes_kanban.github import MemoryGitHost, assert_publish_gate
from hermes_kanban.orchestrator import MemoryTaskBoard, StepRecord
from test_piv_orchestrator import (
    CHILD_RUN,
    PARENT_PLANNING,
    _runtime_class,
    environment,
    task,
)


def _job_environment(tmp_path, **kwargs):
    board = MemoryTaskBoard((task(card_path="job", card_skill="prd-writer"),))
    return environment(tmp_path, board=board, **kwargs)


def test_validator_runs_critic_before_tester(tmp_path) -> None:
    orchestrator, runtime, _workspace_root = environment(tmp_path)

    orchestrator.run_workflow("fixture", "123")
    orchestrator.run_next_workflow("fixture")
    finished = orchestrator.run_next_workflow("fixture")

    assert finished.state == "COMPLETED"
    order = runtime.order[runtime.order.index("critic") :]
    assert order == ["critic", "tester"]
    # The children ran the executor path before the validator.
    assert runtime.order.index("critic") > runtime.order.index("change")


def test_github_publish_gate_helper(tmp_path) -> None:
    steps = (
        StepRecord("CRITIC_PASS", "critic", "critic", "PASS", (), "ok"),
        StepRecord("TESTER_PASS", "tester", "tester", "PASS", (), "ok"),
        StepRecord("UAT_PASSED", "uat", None, "pass", (), "operator confirmed"),
        StepRecord("PR_REVIEW_PASS", "pr-review", "pr-reviewer", "PASS", (), "ok"),
    )
    assert_publish_gate(steps)

    for missing in ("critic", "tester", "uat", "pr-review"):
        incomplete = tuple(step for step in steps if step.phase != missing)
        with pytest.raises(Exception):
            assert_publish_gate(incomplete)


def test_job_publish_happens_only_after_the_operator_approves(tmp_path) -> None:
    host = MemoryGitHost()
    orchestrator, runtime, _workspace_root = _job_publish_env(tmp_path, git_host=host)

    assert host.pushes == []  # job park: no publish yet
    finished = orchestrator.resume_workflow("fixture", "123", "A")

    assert finished.state == "PR_CREATED"
    assert len(host.pushes) == 1
    assert len(host.upserts) == 1


def _job_publish_env(tmp_path, *, git_host: MemoryGitHost | None = None):
    board = MemoryTaskBoard((task(card_path="job", card_skill="prd-writer"),))
    orchestrator, runtime, _workspace_root = environment(tmp_path, board=board)
    if git_host is not None:
        orchestrator.git_host = git_host
    parked = orchestrator.run_workflow("fixture", "123")
    assert parked.workspace_path is not None
    (parked.workspace_path / "prd.md").write_text("# PRD\n", encoding="utf-8")
    return orchestrator, runtime, _workspace_root


def test_job_publish_is_feature_branch_only(tmp_path) -> None:
    host = MemoryGitHost()
    orchestrator, runtime, workspace_root = _job_publish_env(tmp_path, git_host=host)

    orchestrator.resume_workflow("fixture", "123", "A")

    assert host.pushes == [(workspace_root / "fixture" / "123", "feature/task-123", None)]


def test_publish_never_runs_for_a_feature_card_without_operator_approval(
    tmp_path,
) -> None:
    """FR-028: the automated parent path completes without a publish park."""
    host = MemoryGitHost()
    orchestrator, runtime, workspace_root = environment(tmp_path)
    orchestrator.git_host = host

    orchestrator.run_workflow("fixture", "123")
    orchestrator.run_next_workflow("fixture")
    finished = orchestrator.run_next_workflow("fixture")

    assert finished.state == "COMPLETED"
    assert host.pushes == []
    assert host.upserts == []


def test_tester_inputs_carry_declared_validation_commands(tmp_path) -> None:
    orchestrator, runtime, _workspace_root = environment(tmp_path)

    orchestrator.run_workflow("fixture", "123")
    orchestrator.run_next_workflow("fixture")

    tester_call = runtime.calls[runtime.order.index("tester")]
    assert tester_call.inputs.get("validation_commands") == ("true",)


def test_critic_retryable_fail_never_skips_to_completion(tmp_path) -> None:
    runtime = _runtime_class()(critic_retryable_fail=True)
    orchestrator, runtime, _workspace_root = environment(tmp_path, runtime=runtime)
    host = MemoryGitHost()
    orchestrator.git_host = host

    orchestrator.run_workflow("fixture", "123")
    orchestrator.run_next_workflow("fixture")
    record = orchestrator.run_next_workflow("fixture")

    assert record.current_phase == "critic"
    assert record.state_attempts["critic"] == 3
    assert "tester" not in runtime.order[runtime.order.index("critic") :]
    assert host.pushes == []


def test_pr_review_pass_unlocks_only_the_publish_park(tmp_path) -> None:
    # Job paths keep the existing park/publish flow; feature cards complete
    # without a publish park (FR-028).
    orchestrator, runtime, _workspace_root = _job_publish_env(tmp_path)

    parked = orchestrator.resume_workflow("fixture", "123", "A")

    assert parked.state == "PR_CREATED"
    del parked


def test_full_feature_flow_order(tmp_path) -> None:
    orchestrator, runtime, _workspace_root = environment(tmp_path)

    orchestrator.run_workflow("fixture", "123")
    orchestrator.run_next_workflow("fixture")
    finished = orchestrator.run_next_workflow("fixture")

    assert tuple(runtime.order) == PARENT_PLANNING + CHILD_RUN + CHILD_RUN + (
        "critic",
        "tester",
    )
    assert finished.state == "COMPLETED"
