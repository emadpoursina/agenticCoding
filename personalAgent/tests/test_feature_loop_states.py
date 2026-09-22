"""US1: Hermes dispatches one Pi session per agent state (fixture Pi)."""

from __future__ import annotations

import pytest

from hermes_kanban.orchestrator import (
    InvalidCardPathError,
    InvalidJobSkillError,
    MemoryTaskBoard,
)
from test_piv_orchestrator import (
    HAPPY_PATH,
    _runtime_class,
    environment,
    task,
)


def test_full_successful_run_starts_one_session_per_agent_state(tmp_path) -> None:
    orchestrator, runtime, _workspace_root = environment(tmp_path)

    orchestrator.run_workflow("fixture", "123")
    orchestrator.resume_workflow("fixture", "123", "A")
    orchestrator.resume_workflow("fixture", "123", "A")
    orchestrator.resume_workflow("fixture", "123", "A")

    assert tuple(runtime.order) == HAPPY_PATH
    assert runtime.order.count("ready") == 1
    assert len(set(runtime.sessions)) == len(runtime.sessions)


def test_sessions_are_distinct_across_all_states(tmp_path) -> None:
    orchestrator, runtime, _workspace_root = environment(tmp_path)

    orchestrator.run_workflow("fixture", "123")
    orchestrator.resume_workflow("fixture", "123", "A")
    orchestrator.resume_workflow("fixture", "123", "A")
    orchestrator.resume_workflow("fixture", "123", "A")

    assert len(runtime.calls) == len(HAPPY_PATH)
    assert len(set(runtime.sessions)) == len(runtime.calls)


def test_zero_starts_for_confirm_uat_and_publish(tmp_path) -> None:
    orchestrator, runtime, _workspace_root = environment(tmp_path)

    orchestrator.run_workflow("fixture", "123")
    orchestrator.resume_workflow("fixture", "123", "A")
    orchestrator.resume_workflow("fixture", "123", "A")
    orchestrator.resume_workflow("fixture", "123", "A")

    for human_state in ("confirm", "uat", "publish"):
        assert human_state not in runtime.order


def test_state_order_matches_the_canonical_graph(tmp_path) -> None:
    orchestrator, runtime, _workspace_root = environment(tmp_path)

    orchestrator.run_workflow("fixture", "123")
    orchestrator.resume_workflow("fixture", "123", "A")
    orchestrator.resume_workflow("fixture", "123", "A")
    orchestrator.resume_workflow("fixture", "123", "A")

    assert runtime.order == list(HAPPY_PATH)


def test_analyze_runs_only_when_plan_says_yes(tmp_path) -> None:
    runtime = _runtime_class()(needs_analysis=True)
    orchestrator, runtime, _workspace_root = environment(tmp_path, runtime=runtime)

    orchestrator.run_workflow("fixture", "123")
    orchestrator.resume_workflow("fixture", "123", "A")
    orchestrator.resume_workflow("fixture", "123", "A")
    orchestrator.resume_workflow("fixture", "123", "A")

    assert "analyze" in runtime.order
    assert runtime.order.index("tasks") < runtime.order.index("analyze")
    assert runtime.order.index("analyze") < runtime.order.index("implement")


def test_analyze_skipped_when_plan_says_no(tmp_path) -> None:
    runtime = _runtime_class()(needs_analysis=False)
    orchestrator, runtime, _workspace_root = environment(tmp_path, runtime=runtime)

    orchestrator.run_workflow("fixture", "123")
    orchestrator.resume_workflow("fixture", "123", "A")
    orchestrator.resume_workflow("fixture", "123", "A")
    orchestrator.resume_workflow("fixture", "123", "A")

    assert "analyze" not in runtime.order


def test_implement_converge_loop_starts_a_fresh_implement_session(tmp_path) -> None:
    runtime = _runtime_class()(repeat_convergence=True)
    orchestrator, runtime, _workspace_root = environment(tmp_path, runtime=runtime)

    orchestrator.run_workflow("fixture", "123")
    orchestrator.resume_workflow("fixture", "123", "A")
    orchestrator.resume_workflow("fixture", "123", "A")
    orchestrator.resume_workflow("fixture", "123", "A")

    assert runtime.order.count("implement") == 2
    assert runtime.order.count("converge") == 2
    assert len(set(runtime.sessions)) == len(runtime.sessions)


def test_missing_path_walks_feature_graph_with_no_short_sessions(tmp_path) -> None:
    orchestrator, runtime, _workspace_root = environment(tmp_path)

    orchestrator.run_workflow("fixture", "123")
    orchestrator.resume_workflow("fixture", "123", "A")
    orchestrator.resume_workflow("fixture", "123", "A")
    orchestrator.resume_workflow("fixture", "123", "A")

    assert tuple(runtime.order) == HAPPY_PATH
    assert "change" not in runtime.order
    assert "job" not in runtime.order


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


def test_job_path_runs_ready_and_one_named_skill(tmp_path) -> None:
    board = MemoryTaskBoard((task(card_path="job", card_skill="prd-writer"),))
    orchestrator, runtime, _workspace_root = environment(tmp_path, board=board)

    finished = orchestrator.run_workflow("fixture", "123")

    assert tuple(runtime.order) == ("ready", "job")
    assert finished.state == "COMPLETED"
    assert finished.current_phase == "job"
    assert "prd-writer" in runtime.calls[-1].skill_path
    assert orchestrator.git_host.pushes == []  # type: ignore[union-attr]


def test_job_second_skill_name_uses_that_skill(tmp_path) -> None:
    board = MemoryTaskBoard((task(card_path="job", card_skill="project-bootstrapper"),))
    orchestrator, runtime, _workspace_root = environment(tmp_path, board=board)

    finished = orchestrator.run_workflow("fixture", "123")

    assert tuple(runtime.order) == ("ready", "job")
    assert finished.state == "COMPLETED"
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

    finished = orchestrator.resume_workflow("fixture", "123", "A")
    assert finished.state == "COMPLETED"
    assert runtime.order == ["ready", "job", "job"]
    assert len(set(runtime.sessions)) == len(runtime.sessions)
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
