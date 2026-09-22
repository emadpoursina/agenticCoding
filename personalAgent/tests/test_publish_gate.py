"""US3: validation is critic then tester then UAT then pr-review before publish."""

from __future__ import annotations

import pytest

from hermes_kanban.github import MemoryGitHost, assert_publish_gate
from hermes_kanban.orchestrator import StepRecord
from test_piv_orchestrator import _runtime_class, environment


def test_converged_flow_runs_critic_before_tester_before_uat(tmp_path) -> None:
    orchestrator, runtime, _workspace_root = environment(tmp_path)

    orchestrator.run_workflow("fixture", "123")
    orchestrator.resume_workflow("fixture", "123", "A")

    order = runtime.order[runtime.order.index("converge") :]
    assert order == ["converge", "critic", "tester"]


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


def test_publish_happens_only_after_all_gates_pass(tmp_path) -> None:
    host = MemoryGitHost()
    orchestrator, runtime, _workspace_root = environment(tmp_path)
    orchestrator.git_host = host

    orchestrator.run_workflow("fixture", "123")
    orchestrator.resume_workflow("fixture", "123", "A")
    orchestrator.resume_workflow("fixture", "123", "A")
    assert host.pushes == []  # pr-review park: no publish yet
    finished = orchestrator.resume_workflow("fixture", "123", "A")

    assert finished.state == "PR_CREATED"
    assert len(host.pushes) == 1
    assert len(host.upserts) == 1


def test_publish_is_feature_branch_only(tmp_path) -> None:
    orchestrator, runtime, workspace_root = environment(tmp_path)
    host = MemoryGitHost()
    orchestrator.git_host = host

    orchestrator.run_workflow("fixture", "123")
    orchestrator.resume_workflow("fixture", "123", "A")
    orchestrator.resume_workflow("fixture", "123", "A")
    orchestrator.resume_workflow("fixture", "123", "A")

    assert host.pushes == [(workspace_root / "fixture" / "123", "feature/task-123", None)]


def test_tester_inputs_carry_declared_validation_commands(tmp_path) -> None:
    orchestrator, runtime, _workspace_root = environment(tmp_path)

    orchestrator.run_workflow("fixture", "123")
    orchestrator.resume_workflow("fixture", "123", "A")

    tester_call = runtime.calls[runtime.order.index("tester")]
    assert tester_call.inputs.get("validation_commands") == ("true",)


def test_critic_retryable_fail_never_skips_to_publish(tmp_path) -> None:
    runtime = _runtime_class()(critic_retryable_fail=True)
    orchestrator, runtime, _workspace_root = environment(tmp_path, runtime=runtime)
    host = MemoryGitHost()
    orchestrator.git_host = host

    orchestrator.run_workflow("fixture", "123")
    record = orchestrator.resume_workflow("fixture", "123", "A")

    assert record.current_phase == "critic"
    assert record.state_attempts["critic"] == 3
    assert "tester" not in runtime.order
    assert host.pushes == []


def test_pr_review_pass_unlocks_only_the_publish_park(tmp_path) -> None:
    orchestrator, runtime, _workspace_root = environment(tmp_path)
    host = MemoryGitHost()
    orchestrator.git_host = host

    orchestrator.run_workflow("fixture", "123")
    orchestrator.resume_workflow("fixture", "123", "A")
    parked = orchestrator.resume_workflow("fixture", "123", "A")

    assert parked.current_phase == "pr-review"
    assert parked.decision.options[0].text.startswith("Publish")
    assert host.pushes == []
