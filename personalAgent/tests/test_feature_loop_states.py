"""US1: Hermes dispatches one Pi session per agent state (fixture Pi)."""

from __future__ import annotations

from test_piv_orchestrator import (
    HAPPY_PATH,
    _runtime_class,
    environment,
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
