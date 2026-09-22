"""US2: human gates park in Hermes; Pi never owns skip/confirm/UAT policy."""

from __future__ import annotations

from test_piv_orchestrator import _runtime_class, environment


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

    assert encoded.current_phase == "confirm"
    assert runtime.order.count("clarify") == 2
    assert len(runtime.calls) == 4
    answers = runtime.calls[-1].resume_context.answers
    assert answers == ("Choose the fixture scope.",)
    assert len(set(runtime.sessions)) == len(runtime.sessions)


def test_confirm_precedes_plan(tmp_path) -> None:
    runtime = _runtime_class()(question=True)
    orchestrator, runtime, _workspace_root = environment(tmp_path, runtime=runtime)

    orchestrator.run_workflow("fixture", "123")
    orchestrator.resume_workflow("fixture", "123", "A")
    resumed = orchestrator.resume_workflow("fixture", "123", "A")

    assert resumed.current_phase == "uat"
    assert tuple(runtime.order) == (
        "ready",
        "specify",
        "clarify",
        "clarify",
        "plan",
        "tasks",
        "analyze",
        "implement",
        "converge",
        "critic",
        "tester",
    )


def test_skip_self_answers_but_confirm_still_runs(tmp_path) -> None:
    runtime = _runtime_class()(question=True)
    orchestrator, runtime, _workspace_root = environment(tmp_path, runtime=runtime)

    parked = orchestrator.run_workflow("fixture", "123", operator_flags=("skip",))

    assert parked.current_phase == "confirm"
    assert len(runtime.calls) == 3
    orchestrator.resume_workflow("fixture", "123", "A")
    orchestrator.resume_workflow("fixture", "123", "A")
    finished = orchestrator.resume_workflow("fixture", "123", "A")
    assert finished.state == "PR_CREATED"


def test_uat_starts_no_pi_and_presents_a_feature_checklist(tmp_path) -> None:
    orchestrator, runtime, _workspace_root = environment(tmp_path)

    orchestrator.run_workflow("fixture", "123")
    calls_before_uat = len(runtime.calls)
    parked = orchestrator.resume_workflow("fixture", "123", "A")

    assert parked.current_phase == "uat"
    assert parked.uat_checklist
    assert parked.decision.options[0].text.startswith("Pass")
    # Reaching the UAT park started only the pipeline sessions; no Pi for UAT itself.
    assert len(runtime.calls) == calls_before_uat + 7
    assert "uat" not in runtime.order


def test_after_pr_review_the_record_parks_and_never_auto_loops(tmp_path) -> None:
    orchestrator, runtime, _workspace_root = environment(tmp_path)

    orchestrator.run_workflow("fixture", "123")
    orchestrator.resume_workflow("fixture", "123", "A")
    parked = orchestrator.resume_workflow("fixture", "123", "A")

    assert parked.state == "HUMAN_DECISION_REQUIRED"
    assert parked.current_phase == "pr-review"
    letters = [option.letter for option in parked.decision.options]
    assert letters == ["A", "B"]
    calls_at_park = len(runtime.calls)
    finished = orchestrator.resume_workflow("fixture", "123", "A")
    assert finished.state == "PR_CREATED"
    # pr-review itself was the last Pi session; publish started no Pi.
    assert len(runtime.calls) == calls_at_park


def test_operator_choices_never_start_pi_for_human_states(tmp_path) -> None:
    runtime = _runtime_class()(question=True)
    orchestrator, runtime, _workspace_root = environment(tmp_path, runtime=runtime)

    orchestrator.run_workflow("fixture", "123")
    for _ in range(3):
        orchestrator.resume_workflow("fixture", "123", "A")
    finished = orchestrator.resume_workflow("fixture", "123", "A")

    assert finished.state == "PR_CREATED"
    for human_state in ("confirm", "uat", "publish"):
        assert human_state not in runtime.order
