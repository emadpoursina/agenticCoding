"""US1: Hermes dispatches one Pi session per agent state (fixture Pi)."""

from __future__ import annotations

import pytest

from hermes_kanban.orchestrator import (
    InvalidCardPathError,
    InvalidJobSkillError,
    MemoryTaskBoard,
)
from test_piv_orchestrator import (
    CHILD_RUN,
    PARENT_PLANNING,
    VALIDATOR_RUN,
    _runtime_class,
    environment,
    task,
)

FULL_RUN = PARENT_PLANNING + CHILD_RUN + CHILD_RUN + VALIDATOR_RUN


def _drive_feature(orchestrator, project_id="fixture", task_id="123"):
    """Run the full card-to-completion flow and return every record."""
    awaiting = orchestrator.run_workflow(project_id, task_id)
    first = orchestrator.run_next_workflow(project_id)
    finished = orchestrator.run_next_workflow(project_id)
    return awaiting, first, finished


def test_full_successful_run_starts_one_session_per_agent_state(tmp_path) -> None:
    orchestrator, runtime, _workspace_root = environment(tmp_path)

    _awaiting, _first, finished = _drive(orchestrator)

    assert finished.state == "COMPLETED"
    assert tuple(runtime.order) == FULL_RUN
    assert runtime.order.count("ready") == 3
    assert len(set(runtime.sessions)) == len(runtime.sessions)


def test_sessions_are_distinct_across_all_states(tmp_path) -> None:
    orchestrator, runtime, _workspace_root = environment(tmp_path)

    _awaiting, _first, finished = _drive(orchestrator)

    assert finished.state == "COMPLETED"
    assert len(runtime.calls) == len(FULL_RUN)
    assert len(set(runtime.sessions)) == len(runtime.calls)


def test_zero_starts_for_confirm_uat_and_publish(tmp_path) -> None:
    orchestrator, runtime, _workspace_root = environment(tmp_path)

    _awaiting, _first, finished = _drive(orchestrator)

    assert finished.state == "COMPLETED"
    for human_state in ("confirm", "uat", "publish"):
        assert human_state not in runtime.order


def test_state_order_matches_the_canonical_graph(tmp_path) -> None:
    orchestrator, runtime, _workspace_root = environment(tmp_path)

    _awaiting, _first, finished = _drive(orchestrator)

    assert finished.state == "COMPLETED"
    assert runtime.order == list(FULL_RUN)


def test_analyze_runs_only_when_plan_says_yes(tmp_path) -> None:
    runtime = _runtime_class()(needs_analysis=True)
    orchestrator, runtime, _workspace_root = environment(tmp_path, runtime=runtime)

    _awaiting, _first, finished = _drive(orchestrator)

    assert "analyze" in runtime.order
    assert runtime.order.index("tasks") < runtime.order.index("analyze")
    assert runtime.order.index("analyze") < runtime.order.index("critic")


def test_analyze_skipped_when_plan_says_no(tmp_path) -> None:
    runtime = _runtime_class()(needs_analysis=False)
    orchestrator, runtime, _workspace_root = environment(tmp_path, runtime=runtime)

    _awaiting, _first, finished = _drive(orchestrator)

    assert finished.state == "COMPLETED"
    assert "analyze" not in runtime.order


def test_missing_path_walks_feature_graph_with_no_short_parent_sessions(
    tmp_path,
) -> None:
    orchestrator, runtime, workspace_root = environment(tmp_path)

    awaiting, first, finished = _drive(orchestrator)

    assert finished.state == "COMPLETED"
    # The parent planning runs the feature graph; only the child cards
    # execute the short executor path.
    assert tuple(runtime.order[: len(PARENT_PLANNING)]) == PARENT_PLANNING
    assert awaiting.parent_task_id is None
    assert awaiting.children == ("card-002", "card-003")
    assert first.task_id == "card-002"
    assert finished.task_id == "123"
    del workspace_root


def test_change_path_runs_ready_change_tester_then_completed(tmp_path) -> None:
    board = MemoryTaskBoard((task(card_path="change"),))
    orchestrator, runtime, _workspace_root = environment(tmp_path, board=board)

    finished = orchestrator.run_workflow("fixture", "123")

    assert tuple(runtime.order) == ("ready", "change", "tester")
    assert finished.state == "COMPLETED"
    assert finished.current_phase == "tester"
    assert orchestrator.git_host.pushes == []  # type: ignore[union-attr]


def test_ready_receives_card_path(tmp_path) -> None:
    board = MemoryTaskBoard((task(card_path="change"),))
    orchestrator, runtime, _workspace_root = environment(tmp_path, board=board)

    orchestrator.run_workflow("fixture", "123")

    assert runtime.calls[0].inputs["card_path"] == "change"


def test_job_path_parks_for_publish_decision(tmp_path) -> None:
    board = MemoryTaskBoard((task(card_path="job", card_skill="prd-writer"),))
    orchestrator, runtime, _workspace_root = environment(tmp_path, board=board)

    parked = orchestrator.run_workflow("fixture", "123")

    assert tuple(runtime.order) == ("ready", "job")
    assert parked.state == "HUMAN_DECISION_REQUIRED"
    assert parked.current_phase == "job"
    assert parked.decision is not None
    assert {choice.letter for choice in parked.decision.options} == {"A", "B"}
    assert "prd-writer" in runtime.calls[-1].skill_path
    assert orchestrator.git_host.pushes == []  # type: ignore[union-attr]

    completed = orchestrator.resume_workflow("fixture", "123", "B")
    assert completed.state == "COMPLETED"
    assert orchestrator.git_host.pushes == []  # type: ignore[union-attr]


def test_job_publish_approval_creates_pull_request(tmp_path) -> None:
    board = MemoryTaskBoard((task(card_path="job", card_skill="prd-writer"),))
    orchestrator, runtime, _workspace_root = environment(tmp_path, board=board)

    parked = orchestrator.run_workflow("fixture", "123")
    assert parked.workspace_path is not None
    (parked.workspace_path / "prd.md").write_text("# PRD\n", encoding="utf-8")
    published = orchestrator.resume_workflow("fixture", "123", "A")

    assert tuple(runtime.order) == ("ready", "job")
    assert parked.state == "HUMAN_DECISION_REQUIRED"
    assert published.state == "PR_CREATED", published.error
    assert published.pull_request is not None
    assert len(orchestrator.git_host.pushes) == 1  # type: ignore[union-attr]
    assert len(orchestrator.git_host.upserts) == 1  # type: ignore[union-attr]


def test_job_second_skill_name_uses_that_skill(tmp_path) -> None:
    board = MemoryTaskBoard((task(card_path="job", card_skill="project-bootstrapper"),))
    orchestrator, runtime, _workspace_root = environment(tmp_path, board=board)

    parked = orchestrator.run_workflow("fixture", "123")
    orchestrator.resume_workflow("fixture", "123", "B")

    assert tuple(runtime.order) == ("ready", "job")
    assert parked.decision is not None
    assert "project-bootstrapper" in runtime.calls[-1].skill_path


def test_job_needs_human_parks_and_resume_starts_new_session(tmp_path) -> None:
    fixture_runtime = _runtime_class()(job_question=True)
    board = MemoryTaskBoard((task(card_path="job", card_skill="prd-writer"),))
    orchestrator, runtime, _workspace_root = environment(
        tmp_path, runtime=fixture_runtime, board=board
    )

    parked = orchestrator.run_workflow("fixture", "123")
    assert parked.state == "HUMAN_DECISION_REQUIRED"
    assert parked.current_phase == "job"
    assert runtime.order == ["ready", "job"]

    # First resume answers the worker question in a NEW session; the second
    # parks for the publish decision; the third completes without publishing.
    answered = orchestrator.resume_workflow("fixture", "123", "A")
    assert answered.state == "HUMAN_DECISION_REQUIRED"
    assert runtime.order == ["ready", "job", "job"]
    assert len(set(runtime.sessions)) == len(runtime.sessions)

    completed = orchestrator.resume_workflow("fixture", "123", "B")
    assert completed.state == "COMPLETED"
    assert orchestrator.git_host.pushes == []  # type: ignore[union-attr]


def test_change_scope_feature_parks_blocked_without_tester(tmp_path) -> None:
    fixture_runtime = _runtime_class()(change_scope_feature=True)
    board = MemoryTaskBoard((task(card_path="change"),))
    orchestrator, runtime, _workspace_root = environment(
        tmp_path, runtime=fixture_runtime, board=board
    )

    record = orchestrator.run_workflow("fixture", "123")

    assert record.state == "BLOCKED"
    assert record.current_phase == "change"
    assert tuple(runtime.order) == ("ready", "change")
    assert orchestrator.git_host.pushes == []  # type: ignore[union-attr]


def test_job_scope_feature_parks_blocked(tmp_path) -> None:
    fixture_runtime = _runtime_class()(job_scope_feature=True)
    board = MemoryTaskBoard((task(card_path="job", card_skill="prd-writer"),))
    orchestrator, runtime, _workspace_root = environment(
        tmp_path, runtime=fixture_runtime, board=board
    )

    record = orchestrator.run_workflow("fixture", "123")

    assert record.state == "BLOCKED"
    assert record.current_phase == "job"
    assert tuple(runtime.order) == ("ready", "job")
    assert orchestrator.git_host.pushes == []  # type: ignore[union-attr]


def test_unknown_path_never_starts_pi(tmp_path) -> None:
    fixture_runtime = _runtime_class()()
    board = MemoryTaskBoard((task(card_path="epic"),))
    orchestrator, runtime, _workspace_root = environment(
        tmp_path, runtime=fixture_runtime, board=board
    )

    with pytest.raises(InvalidCardPathError):
        orchestrator.run_workflow("fixture", "123")
    assert runtime.calls == []


def test_unknown_job_skill_never_starts_pi(tmp_path) -> None:
    fixture_runtime = _runtime_class()()
    board = MemoryTaskBoard((task(card_path="job", card_skill="spec-writer"),))
    orchestrator, runtime, _workspace_root = environment(
        tmp_path, runtime=fixture_runtime, board=board
    )

    with pytest.raises(InvalidJobSkillError):
        orchestrator.run_workflow("fixture", "123")
    assert runtime.calls == []


def _drive(orchestrator):
    awaiting = orchestrator.run_workflow("fixture", "123")
    first = orchestrator.run_next_workflow("fixture")
    finished = orchestrator.run_next_workflow("fixture")
    return awaiting, first, finished
