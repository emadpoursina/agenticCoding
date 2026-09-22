"""Offline per-state Hermes feature-loop checks (fixture Pi, no network)."""

from __future__ import annotations

import importlib.util
import shutil
import subprocess
from pathlib import Path

from hermes_kanban.executor import AssembledContext, ModelResponse
from hermes_kanban.github import MemoryGitHost
from hermes_kanban.messaging import MemoryMessagingChannel
from hermes_kanban.orchestrator import (
    BoardTask,
    MemoryTaskBoard,
    PivOrchestrator,
)
from hermes_kanban.pi import PiHarnessAdapter
from hermes_kanban.startup_context import StartupContextSnapshot

FIXTURES = Path(__file__).parent / "fixtures"

# Agent-kind graph states in fixture happy-path order.
HAPPY_PATH = (
    "ready",
    "specify",
    "clarify",
    "plan",
    "tasks",
    "analyze",
    "implement",
    "converge",
    "critic",
    "tester",
    "pr-review",
)


def _git(*args: str, cwd: Path) -> str:
    return subprocess.run(
        ["git", *args],
        cwd=cwd,
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()


def _runtime_class():
    path = FIXTURES / "pi-runtime" / "runtime.py"
    spec = importlib.util.spec_from_file_location("pi_fixture_runtime_test", path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module.PiFixtureRuntime


def task(**changes: object) -> BoardTask:
    values: dict[str, object] = {
        "id": "123",
        "project_id": "fixture",
        "problem": "Add an isolated note",
        "expected_result": "A note exists",
        "acceptance_criteria": "note exists",
        "priority": "P1",
        "created_at": "2026-08-31T00:00:00Z",
    }
    values.update(changes)
    return BoardTask(**values)  # type: ignore[arg-type]


class ValidationStandIn:
    def __init__(self, responses: list[ModelResponse] | None = None) -> None:
        self.responses = responses or [ModelResponse(summary="validated", status="success")]
        self.calls: list[object] = []

    def complete(self, *, assignment: str, context: object) -> ModelResponse:
        del assignment
        self.calls.append(context)
        if isinstance(context, AssembledContext):
            return (
                self.responses.pop(0)
                if self.responses
                else ModelResponse(summary="validation failed", status="failure")
            )
        return ModelResponse(summary="validated", status="success")


def _initialized_copy(source: Path, target: Path) -> Path:
    shutil.copytree(source, target)
    _git("init", "-b", "main", cwd=target)
    _git("config", "user.email", "tests@example.com", cwd=target)
    _git("config", "user.name", "Tests", cwd=target)
    _git("add", ".", cwd=target)
    _git("commit", "-m", "fixture", cwd=target)
    return target


def environment(
    tmp_path: Path,
    *,
    runtime=None,
    validation_command: str = "true",
    board: MemoryTaskBoard | None = None,
    messaging: MemoryMessagingChannel | None = None,
    project_extra: str = "",
) -> tuple[PivOrchestrator, object, Path]:
    enrolled = _initialized_copy(FIXTURES / "projects" / "standard", tmp_path / "enrolled")
    (enrolled / ".ainative" / "project.yaml").write_text(
        f"""name: fixture-project
repository: github.com/example/fixture
default_branch: main
validation:
  commands:
    - "{validation_command}"
""",
        encoding="utf-8",
    )
    workspace = tmp_path / "workspaces"
    workspace.mkdir()
    overlay = tmp_path / "overlay"
    overlay.mkdir()
    methodology = _initialized_copy(FIXTURES / "ainative-full", tmp_path / "ainative")
    config = tmp_path / "config.yaml"
    config.write_text(
        f"""ainative:
  path: {methodology}
  read_only: true
workspace:
  root: {workspace}
projects:
  - id: fixture
    name: Fixture
    repository: github.com/example/fixture
    location: {enrolled}
    default_branch: main
{project_extra}execution:
  overlay_dir: {overlay}
model:
  roles:
    validation: test-validation-model
""",
        encoding="utf-8",
    )
    selected_runtime = runtime or _runtime_class()()
    adapter = PiHarnessAdapter(selected_runtime)
    orchestrator = PivOrchestrator.from_config(
        config,
        model_service=ValidationStandIn(),
        task_board=board or MemoryTaskBoard((task(),)),
        git_host=MemoryGitHost(),
        messaging=messaging,
        harness_adapter=adapter,
    )
    return orchestrator, selected_runtime, workspace


def test_full_run_records_one_new_session_per_agent_state(tmp_path: Path) -> None:
    orchestrator, runtime, workspace_root = environment(tmp_path)

    parked = orchestrator.run_workflow("fixture", "123")

    worktree = workspace_root / "fixture" / "123"
    assert parked.state == "HUMAN_DECISION_REQUIRED"
    assert parked.current_phase == "confirm"
    assert runtime.order[:3] == ["ready", "specify", "clarify"]
    assert len(set(runtime.sessions)) == len(runtime.sessions)
    assert (worktree / "specs/123/spec.md").is_file()

    orchestrator.resume_workflow("fixture", "123", "A")
    orchestrator.resume_workflow("fixture", "123", "A")
    finished = orchestrator.resume_workflow("fixture", "123", "A")

    assert finished.state == "PR_CREATED"
    assert tuple(runtime.order) == HAPPY_PATH
    assert len(runtime.calls) == len(HAPPY_PATH)
    assert runtime.validation_command_observes[-1] == ("true",)
    assert (worktree / "specs/123/plan.md").is_file()
    assert (worktree / "specs/123/tasks.md").is_file()
    assert len(orchestrator.git_host.pushes) == 1  # type: ignore[union-attr]


def test_human_gates_never_start_pi(tmp_path: Path) -> None:
    orchestrator, runtime, _workspace_root = environment(tmp_path)

    orchestrator.run_workflow("fixture", "123")
    orchestrator.resume_workflow("fixture", "123", "A")
    orchestrator.resume_workflow("fixture", "123", "A")
    parked = orchestrator.resume_workflow("fixture", "123", "A")

    assert parked.state == "PR_CREATED"
    assert tuple(runtime.order) == HAPPY_PATH
    assert "confirm" not in runtime.order
    assert "uat" not in runtime.order
    assert "publish" not in runtime.order


def test_clarify_parks_relays_and_encodes_with_a_new_session(tmp_path: Path) -> None:
    runtime = _runtime_class()(question=True)
    orchestrator, runtime, _workspace_root = environment(tmp_path, runtime=runtime)

    parked = orchestrator.run_workflow("fixture", "123")
    assert parked.state == "HUMAN_DECISION_REQUIRED"
    assert parked.current_phase == "clarify"
    assert parked.question_queue == ("Choose the fixture scope.",)
    assert runtime.order[-1] == "clarify"
    assert len(runtime.calls) == 3

    encoded = orchestrator.resume_workflow("fixture", "123", "A")
    assert encoded.state == "HUMAN_DECISION_REQUIRED"
    assert encoded.current_phase == "confirm"
    assert runtime.calls[-1].resume_context is not None
    assert runtime.calls[-1].resume_context.answers == ("Choose the fixture scope.",)

    orchestrator.resume_workflow("fixture", "123", "A")
    orchestrator.resume_workflow("fixture", "123", "A")
    finished = orchestrator.resume_workflow("fixture", "123", "A")
    assert finished.state == "PR_CREATED"
    assert runtime.order.count("clarify") == 2


def test_skip_self_answers_clarify_but_confirm_still_runs(tmp_path: Path) -> None:
    runtime = _runtime_class()(question=True)
    orchestrator, runtime, _workspace_root = environment(tmp_path, runtime=runtime)

    parked = orchestrator.run_workflow("fixture", "123", operator_flags=("skip",))
    assert parked.state == "HUMAN_DECISION_REQUIRED"
    assert parked.current_phase == "confirm"
    assert len(runtime.calls) == 3

    orchestrator.resume_workflow("fixture", "123", "A")
    orchestrator.resume_workflow("fixture", "123", "A")
    finished = orchestrator.resume_workflow("fixture", "123", "A")
    assert finished.state == "PR_CREATED"


def test_converge_tasks_appended_starts_a_new_implement_session(tmp_path: Path) -> None:
    runtime = _runtime_class()(repeat_convergence=True)
    orchestrator, runtime, _workspace_root = environment(tmp_path, runtime=runtime)

    orchestrator.run_workflow("fixture", "123")
    orchestrator.resume_workflow("fixture", "123", "A")
    orchestrator.resume_workflow("fixture", "123", "A")
    finished = orchestrator.resume_workflow("fixture", "123", "A")

    assert finished.state == "PR_CREATED"
    assert runtime.order.count("implement") == 2
    assert runtime.order.count("converge") == 2


def test_converge_blocked_parks(tmp_path: Path) -> None:
    runtime = _runtime_class()(converge_blocked=True)
    orchestrator, runtime, _workspace_root = environment(tmp_path, runtime=runtime)

    orchestrator.run_workflow("fixture", "123")
    record = orchestrator.resume_workflow("fixture", "123", "A")

    assert record.state == "BLOCKED"
    assert record.current_phase == "converge"
    assert orchestrator.git_host.pushes == []  # type: ignore[union-attr]


def test_converge_fingerprint_stuck_parks(tmp_path: Path) -> None:
    runtime = _runtime_class()(converge_stuck=True)
    orchestrator, runtime, _workspace_root = environment(tmp_path, runtime=runtime)

    orchestrator.run_workflow("fixture", "123")
    record = orchestrator.resume_workflow("fixture", "123", "A")

    assert record.state == "BLOCKED"
    assert record.current_phase == "converge"
    assert runtime.order.count("converge") == 2
    assert orchestrator.git_host.pushes == []  # type: ignore[union-attr]


def test_analyze_skipped_when_plan_says_no(tmp_path: Path) -> None:
    runtime = _runtime_class()(needs_analysis=False)
    orchestrator, runtime, _workspace_root = environment(tmp_path, runtime=runtime)

    orchestrator.run_workflow("fixture", "123")
    orchestrator.resume_workflow("fixture", "123", "A")
    orchestrator.resume_workflow("fixture", "123", "A")
    finished = orchestrator.resume_workflow("fixture", "123", "A")

    assert finished.state == "PR_CREATED"
    assert "analyze" not in runtime.order


def test_ready_blocked_parks_and_is_never_retried(tmp_path: Path) -> None:
    runtime = _runtime_class()(ready_blocked=True)
    orchestrator, runtime, _workspace_root = environment(tmp_path, runtime=runtime)

    record = orchestrator.run_workflow("fixture", "123")

    assert record.state == "BLOCKED"
    assert record.current_phase == "ready"
    assert len(runtime.calls) == 1
    assert orchestrator.git_host.pushes == []  # type: ignore[union-attr]


def test_step_stuck_retries_three_attempts_then_parks(tmp_path: Path) -> None:
    runtime = _runtime_class()(stuck=True)
    orchestrator, runtime, _workspace_root = environment(tmp_path, runtime=runtime)

    record = orchestrator.run_workflow("fixture", "123")

    assert record.state == "HUMAN_DECISION_REQUIRED"
    assert record.state_attempts["ready"] == 3
    assert len(runtime.calls) == 3
    assert orchestrator.git_host.pushes == []  # type: ignore[union-attr]


def test_timeout_failure_parks_without_validating_or_publishing(tmp_path: Path) -> None:
    runtime = _runtime_class()(timeout=True)
    orchestrator, runtime, _workspace_root = environment(tmp_path, runtime=runtime)

    record = orchestrator.run_workflow("fixture", "123")

    assert record.state == "BLOCKED"
    assert len(runtime.calls) == 1
    assert orchestrator.git_host.pushes == []  # type: ignore[union-attr]


def test_missing_artifact_parks_without_retry(tmp_path: Path) -> None:
    runtime = _runtime_class()(missing_artifact=True)
    orchestrator, runtime, _workspace_root = environment(tmp_path, runtime=runtime)

    record = orchestrator.run_workflow("fixture", "123")

    assert record.state == "BLOCKED"
    assert record.current_phase == "specify"
    assert "missing native artifact" in (record.error or "")
    assert len(runtime.calls) == 2
    assert orchestrator.git_host.pushes == []  # type: ignore[union-attr]


def test_critic_retryable_fail_never_skips_to_publish(tmp_path: Path) -> None:
    runtime = _runtime_class()(critic_retryable_fail=True)
    orchestrator, runtime, _workspace_root = environment(tmp_path, runtime=runtime)

    orchestrator.run_workflow("fixture", "123")
    record = orchestrator.resume_workflow("fixture", "123", "A")

    assert record.state == "HUMAN_DECISION_REQUIRED"
    assert record.current_phase == "critic"
    assert record.state_attempts["critic"] == 3
    assert "tester" not in runtime.order
    assert orchestrator.git_host.pushes == []  # type: ignore[union-attr]


def test_tester_fail_blocks_uat_and_publish(tmp_path: Path) -> None:
    runtime = _runtime_class()(tester_fail=True)
    orchestrator, runtime, _workspace_root = environment(tmp_path, runtime=runtime)

    orchestrator.run_workflow("fixture", "123")
    record = orchestrator.resume_workflow("fixture", "123", "A")

    assert record.state == "BLOCKED"
    assert record.current_phase == "tester"
    assert "uat" not in runtime.order
    assert orchestrator.git_host.pushes == []  # type: ignore[union-attr]


def test_pr_review_fail_parks_without_publish(tmp_path: Path) -> None:
    runtime = _runtime_class()(pr_review_fail=True)
    orchestrator, runtime, _workspace_root = environment(tmp_path, runtime=runtime)

    orchestrator.run_workflow("fixture", "123")
    orchestrator.resume_workflow("fixture", "123", "A")
    parked = orchestrator.resume_workflow("fixture", "123", "A")

    assert parked.state == "BLOCKED"
    assert parked.current_phase == "pr-review"
    assert orchestrator.git_host.pushes == []  # type: ignore[union-attr]


def test_pr_review_pass_requires_operator_publish_decision(tmp_path: Path) -> None:
    orchestrator, runtime, _workspace_root = environment(tmp_path)

    orchestrator.run_workflow("fixture", "123")
    orchestrator.resume_workflow("fixture", "123", "A")
    parked = orchestrator.resume_workflow("fixture", "123", "A")

    assert parked.state == "HUMAN_DECISION_REQUIRED"
    assert parked.current_phase == "pr-review"
    assert orchestrator.git_host.pushes == []  # type: ignore[union-attr]
    letters = [option.letter for option in parked.decision.options]
    assert letters == ["A", "B"]

    finished = orchestrator.resume_workflow("fixture", "123", "A")
    assert finished.state == "PR_CREATED"
    assert len(orchestrator.git_host.pushes) == 1  # type: ignore[union-attr]


def test_uat_presents_checklist_and_starts_no_pi(tmp_path: Path) -> None:
    orchestrator, runtime, _workspace_root = environment(tmp_path)

    orchestrator.run_workflow("fixture", "123")
    parked = orchestrator.resume_workflow("fixture", "123", "A")

    assert parked.current_phase == "uat"
    assert parked.uat_checklist
    assert "Verify: note exists" in parked.uat_checklist
    assert parked.decision.options[0].text.startswith("Pass")
    assert "uat" not in runtime.order


def test_harness_isolation_snapshots_forbidden_roots(
    tmp_path: Path,
    snapshot_files,
) -> None:
    orchestrator, _runtime, workspace_root = environment(tmp_path)
    enrolled = tmp_path / "enrolled"
    ainative = tmp_path / "ainative"
    overlay = tmp_path / "overlay"
    sibling = workspace_root / "fixture" / "sibling"
    sibling.mkdir(parents=True)
    (sibling / "sentinel.txt").write_text("sibling\n", encoding="utf-8")
    (overlay / "control-state.json").write_text("control\n", encoding="utf-8")

    enrolled_before = snapshot_files(enrolled)
    ainative_before = snapshot_files(ainative)
    overlay_before = snapshot_files(overlay, exclude={"overlay.json", "alive"})
    sibling_before = snapshot_files(sibling)

    orchestrator.run_workflow("fixture", "123")
    orchestrator.resume_workflow("fixture", "123", "A")
    orchestrator.resume_workflow("fixture", "123", "A")
    finished = orchestrator.resume_workflow("fixture", "123", "A")

    assert finished.state == "PR_CREATED"
    assert snapshot_files(enrolled) == enrolled_before
    assert snapshot_files(ainative) == ainative_before
    assert snapshot_files(overlay, exclude={"overlay.json", "alive"}) == overlay_before
    assert snapshot_files(sibling) == sibling_before


def test_registered_context_stays_out_of_harness_and_overlay_payloads(
    tmp_path: Path,
) -> None:
    orchestrator, runtime, workspace_root = environment(tmp_path)
    sentinel = "registered-hermes-context-secret"
    orchestrator.startup_context = StartupContextSnapshot(
        files={
            "hermes_instructions": sentinel,
            "system": sentinel,
            "user": sentinel,
        },
        registrations=(),
    )

    orchestrator.run_workflow("fixture", "123")

    assert sentinel not in repr(runtime.calls[0])
    assert sentinel not in (orchestrator.overlay_dir / "overlay.json").read_text()
    assert sentinel not in "\n".join(
        path.read_text(encoding="utf-8")
        for path in (workspace_root / "fixture" / "123").rglob("*")
        if path.is_file() and ".git" not in path.parts
    )
