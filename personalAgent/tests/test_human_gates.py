"""US2: human gates park in Hermes; Pi never owns skip/confirm/UAT policy."""

from __future__ import annotations

from test_piv_orchestrator import (
    PARENT_PLANNING,
    _runtime_class,
    environment,
)


def test_clarify_questions_park_without_further_stages(tmp_path) -> None:
    runtime = _runtime_class()(question=True)
    orchestrator, runtime, _workspace_root = environment(tmp_path, runtime=runtime)

    parked = orchestrator.run_workflow("fixture", "123")

    assert parked.state == "HUMAN_DECISION_REQUIRED"
    assert parked.current_phase == "clarify"
    assert parked.question_queue == ("Choose the fixture scope.",)
    assert runtime.order == ["ready", "specify", "clarify"]
    assert len(runtime.calls) == 3


def test_recorded_answers_resume_into_a_new_encode_session(tmp_path) -> None:
    runtime = _runtime_class()(question=True)
    orchestrator, runtime, _workspace_root = environment(tmp_path, runtime=runtime)

    orchestrator.run_workflow("fixture", "123")
    encoded = orchestrator.resume_workflow("fixture", "123", "A")

    # The answers are encoded by a NEW clarify session, then planning
    # continues to the decomposition park without another human gate.
    assert encoded.state == "AWAITING_CHILDREN"
    assert runtime.order.count("clarify") == 2
    assert len(runtime.calls) == len(PARENT_PLANNING) + 1
    answers = runtime.calls[3].resume_context.answers
    assert answers == ("Choose the fixture scope.",)
    assert len(set(runtime.sessions)) == len(runtime.sessions)


def test_confirm_parks_only_on_unresolved_clarify_questions(tmp_path) -> None:
    runtime = _runtime_class()(clarify_unresolved=True)
    orchestrator, runtime, _workspace_root = environment(tmp_path, runtime=runtime)

    parked = orchestrator.run_workflow("fixture", "123")
    assert parked.state == "HUMAN_DECISION_REQUIRED"
    assert parked.current_phase == "confirm"
    assert runtime.order == ["ready", "specify", "clarify"]
    assert len(runtime.calls) == 3

    finished = orchestrator.resume_workflow("fixture", "123", "A")
    assert finished.state == "AWAITING_CHILDREN"
    assert tuple(runtime.order) == (
        "ready",
        "specify",
        "clarify",
        "plan",
        "tasks",
        "analyze",
    )


def test_skip_self_answers_but_confirm_still_runs(tmp_path) -> None:
    runtime = _runtime_class()(question=True)
    orchestrator, runtime, _workspace_root = environment(tmp_path, runtime=runtime)

    parked = orchestrator.run_workflow("fixture", "123", operator_flags=("skip",))

    assert parked.current_phase == "confirm"
    assert len(runtime.calls) == 3

    finished = orchestrator.resume_workflow("fixture", "123", "A")
    assert finished.state == "AWAITING_CHILDREN"
    assert tuple(runtime.order) == PARENT_PLANNING


def test_uat_parks_only_on_flagged_acceptance_items(tmp_path) -> None:
    runtime = _runtime_class()(tester_acceptance_flag=True)
    orchestrator, runtime, _workspace_root = environment(tmp_path, runtime=runtime)

    orchestrator.run_workflow("fixture", "123")
    calls_before_uat = len(runtime.calls)
    finished = orchestrator.run_next_workflow("fixture")
    parked = orchestrator.run_next_workflow("fixture")

    assert parked.state == "HUMAN_DECISION_REQUIRED"
    assert parked.current_phase == "uat"
    assert parked.uat_checklist
    assert parked.decision.options[0].text.startswith("Pass")
    assert "uat" not in runtime.order
    del finished, calls_before_uat


def test_after_pr_review_the_record_parks_and_never_auto_loops(tmp_path) -> None:
    """Job-path pr-review machinery is unchanged: the operator decides publish."""
    from hermes_kanban.orchestrator import MemoryTaskBoard
    from test_piv_orchestrator import task

    board = MemoryTaskBoard((task(card_path="job", card_skill="prd-writer"),))
    orchestrator, runtime, _workspace_root = environment(tmp_path, board=board)

    parked = orchestrator.run_workflow("fixture", "123")
    assert parked.workspace_path is not None
    (parked.workspace_path / "prd.md").write_text("# PRD\n", encoding="utf-8")

    assert parked.state == "HUMAN_DECISION_REQUIRED"
    assert parked.current_phase == "job"
    letters = [option.letter for option in parked.decision.options]
    assert letters == ["A", "B"]
    calls_at_park = len(runtime.calls)
    finished = orchestrator.resume_workflow("fixture", "123", "A")
    assert finished.state == "PR_CREATED"
    # job itself was the last Pi session; publish started no Pi.
    assert len(runtime.calls) == calls_at_park


def test_operator_choices_never_start_pi_for_human_states(tmp_path) -> None:
    runtime = _runtime_class()(tester_acceptance_flag=True)
    orchestrator, runtime, _workspace_root = environment(tmp_path, runtime=runtime)

    orchestrator.run_workflow("fixture", "123")
    orchestrator.run_next_workflow("fixture")
    parked = orchestrator.run_next_workflow("fixture")

    assert parked.current_phase == "uat"
    for human_state in ("confirm", "uat", "publish"):
        assert human_state not in runtime.order
