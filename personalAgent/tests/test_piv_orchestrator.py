"""Offline one-run Hermes orchestration checks."""

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
roles:
  validation: tester
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


def test_one_harness_request_writes_native_artifacts_and_publishes_after_validation(
    tmp_path: Path,
) -> None:
    orchestrator, runtime, workspace_root = environment(tmp_path)

    record = orchestrator.run_workflow("fixture", "123")

    worktree = workspace_root / "fixture" / "123"
    assert record.state == "PR_CREATED"
    assert len(runtime.calls) == 1
    assert runtime.order == [
        "specify",
        "clarify/continue",
        "plan",
        "tasks",
        "analyze",
        "implement",
        "converge",
    ]
    assert (worktree / "specs/123/spec.md").is_file()
    assert (worktree / "specs/123/plan.md").is_file()
    assert (worktree / "specs/123/tasks.md").is_file()
    assert record.harness_result is not None
    assert record.harness_result.status == "completed"
    assert len(orchestrator.git_host.pushes) == 1  # type: ignore[union-attr]


def test_clarify_requires_answer_then_one_continue_confirmation(tmp_path: Path) -> None:
    runtime = _runtime_class()(question=True)
    orchestrator, runtime, _workspace_root = environment(tmp_path, runtime=runtime)

    parked = orchestrator.run_workflow("fixture", "123")
    assert parked.state == "HUMAN_DECISION_REQUIRED"
    assert len(runtime.calls) == 1
    confirmed = orchestrator.resume_workflow("fixture", "123", "A")
    assert confirmed.state == "HUMAN_DECISION_REQUIRED"
    assert len(runtime.calls) == 1
    finished = orchestrator.resume_workflow("fixture", "123", "A")
    assert finished.state == "PR_CREATED"
    assert len(runtime.calls) == 2


def test_skip_records_assumptions_and_continue_report(tmp_path: Path) -> None:
    runtime = _runtime_class()(question=True)
    messaging = MemoryMessagingChannel()
    orchestrator, runtime, _workspace_root = environment(
        tmp_path,
        runtime=runtime,
        messaging=messaging,
    )

    report = orchestrator.run_workflow("fixture", "123", operator_flags=("skip",))
    assert report.state == "HUMAN_DECISION_REQUIRED"
    assert report.resume_context is not None
    assert report.resume_context.assumptions
    assert report.decision is not None
    assert len(report.decision.options) == 1
    assert report.decision.options[0].text == "Continue the Spec Kit playbook"
    choice_reports = [
        delivery for delivery in messaging.deliveries if delivery[0] == "choice_report"
    ]
    assert len(choice_reports) == 1
    assert choice_reports[0][1]["assumptions"] == report.resume_context.assumptions
    assert len(runtime.calls) == 1
    finished = orchestrator.resume_workflow("fixture", "123", "A")
    assert finished.state == "PR_CREATED"
    assert len(runtime.calls) == 2


def test_implementation_question_parks_before_convergence(tmp_path: Path) -> None:
    runtime = _runtime_class()(implementation_question=True)
    orchestrator, runtime, _workspace_root = environment(tmp_path, runtime=runtime)

    parked = orchestrator.run_workflow("fixture", "123")

    assert parked.state == "HUMAN_DECISION_REQUIRED"
    assert parked.decision is not None
    assert parked.decision.options[0].text == "Keep the fixture change?"
    assert "implement" in runtime.order
    assert "converge" not in runtime.order
    assert len(runtime.calls) == 1

    finished = orchestrator.resume_workflow("fixture", "123", "A")

    assert finished.state == "PR_CREATED"
    assert len(runtime.calls) == 2


def test_second_question_batch_parks_before_later_playbook_work(tmp_path: Path) -> None:
    runtime = _runtime_class()(question=True, second_question=True)
    orchestrator, runtime, _workspace_root = environment(tmp_path, runtime=runtime)

    first = orchestrator.run_workflow("fixture", "123")
    continuation = orchestrator.resume_workflow("fixture", "123", "A")
    second = orchestrator.resume_workflow("fixture", "123", "A")

    assert first.state == "HUMAN_DECISION_REQUIRED"
    assert continuation.state == "HUMAN_DECISION_REQUIRED"
    assert second.state == "HUMAN_DECISION_REQUIRED"
    assert second.decision is not None
    assert second.decision.options[0].text == "Choose the fixture implementation mode."
    assert runtime.order[-1] == "tasks"
    assert "implement" not in runtime.order
    assert len(runtime.calls) == 2

    finished = orchestrator.resume_workflow("fixture", "123", "A")

    assert finished.state == "PR_CREATED"
    assert len(runtime.calls) == 3


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

    record = orchestrator.run_workflow("fixture", "123")

    assert record.state == "PR_CREATED"
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

    record = orchestrator.run_workflow("fixture", "123")

    assert sentinel not in repr(runtime.calls[0])
    assert sentinel not in repr(record)
    assert sentinel not in (orchestrator.overlay_dir / "overlay.json").read_text()
    assert sentinel not in "\n".join(
        path.read_text(encoding="utf-8")
        for path in (workspace_root / "fixture" / "123").rglob("*")
        if path.is_file() and ".git" not in path.parts
    )


def test_third_stuck_attempt_parks_without_a_fourth_run(tmp_path: Path) -> None:
    runtime = _runtime_class()(stuck=True)
    orchestrator, runtime, _workspace_root = environment(tmp_path, runtime=runtime)

    record = orchestrator.run_workflow("fixture", "123")

    assert record.state == "HUMAN_DECISION_REQUIRED"
    assert record.attempt == 3
    assert len(runtime.calls) == 3
    assert orchestrator.git_host.pushes == []  # type: ignore[union-attr]


def test_timeout_failure_does_not_validate_or_publish(tmp_path: Path) -> None:
    runtime = _runtime_class()(timeout=True)
    orchestrator, runtime, _workspace_root = environment(tmp_path, runtime=runtime)

    record = orchestrator.run_workflow("fixture", "123")

    assert record.state == "FAILED"
    assert len(runtime.calls) == 1
    assert orchestrator.git_host.pushes == []  # type: ignore[union-attr]
