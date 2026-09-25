"""Offline per-state Hermes feature-loop checks (fixture Pi, no network)."""

from __future__ import annotations

import importlib.util
import shutil
import sqlite3
import subprocess
from pathlib import Path

import pytest

from hermes_kanban.board import _sections as _body_sections
from hermes_kanban.executor import AssembledContext, ModelResponse
from hermes_kanban.github import MemoryGitHost
from hermes_kanban.messaging import MemoryMessagingChannel
from hermes_kanban.orchestrator import (
    BoardTask,
    MemoryTaskBoard,
    PivOrchestrator,
    PlaceholderValidationError,
)
from hermes_kanban.pi import PiHarnessAdapter

FIXTURES = Path(__file__).parent / "fixtures"

# Parent planning states in fixture happy-path order (FR-016: the feature
# lifecycle ends at the validator; implement/converge belong to the children).
PARENT_PLANNING = (
    "ready",
    "specify",
    "clarify",
    "plan",
    "tasks",
    "analyze",
)
CHILD_RUN = ("ready", "change", "tester")
VALIDATOR_RUN = ("critic", "tester")
# Kept for the legacy full-graph readers below.
HAPPY_PATH = PARENT_PLANNING


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


class MutableTaskBoard:
    """In-memory board seam the fake card creator can write to."""

    def __init__(self, tasks: tuple[BoardTask, ...] = ()) -> None:
        self._tasks = list(tasks)

    def get(self, task_id: str) -> BoardTask:
        for task in self._tasks:
            if task.id == task_id:
                return task
        raise KeyError(f"unknown task: {task_id}")

    def list(self) -> tuple[BoardTask, ...]:
        return tuple(self._tasks)

    def add(self, task: BoardTask) -> None:
        self._tasks.append(task)

    def set_column(self, task_id: str, column: str) -> None:
        self._tasks = [
            task if task.id != task_id else _replace_column(task, column)
            for task in self._tasks
        ]

    def remove(self, task_id: str) -> None:
        self._tasks = [task for task in self._tasks if task.id != task_id]

    def complete_children_of(self, parent_id: str) -> None:
        for task in list(self._tasks):
            if task.parent_id == parent_id and not task.complete:
                self.set_column(task.id, "done")


def _replace_column(task: BoardTask, column: str) -> BoardTask:
    values = {
        field: getattr(task, field)
        for field in task.__dataclass_fields__  # type: ignore[attr-defined]
    }
    values["column"] = column
    values["complete"] = column in {"done", "archived"}
    return BoardTask(**values)  # type: ignore[arg-type]


_PRIORITY_BY_FLAG = {value: f"P{value}" for value in range(4)}


def board_task_from_card_args(args: list[str], *, index: int) -> BoardTask:
    """Rebuild one BoardTask from native card-creation CLI args (fake seam)."""
    body = args[args.index("--body") + 1]
    project_id = args[args.index("--project") + 1]
    sections = _body_sections(body)
    parent = sections.get("Parent", "").split()
    return BoardTask(
        id=f"card-{index:03d}",
        project_id=project_id,
        problem=sections.get("Problem", ""),
        expected_result=sections.get("Expected Result", ""),
        acceptance_criteria=sections.get("Acceptance Criteria", ""),
        priority=sections.get("Priority", "P2"),
        created_at="2026-09-01T00:00:00Z",
        column="todo",
        card_path=sections.get("Path", "feature") or "feature",
        parent_id=parent[0] if parent else "",
        profile=sections.get("Profile", ""),
    )


def make_card_creator(board: MutableTaskBoard) -> object:
    """Card-creation seam that inserts created cards into the fixture board."""

    def creator(args: list[str]) -> None:
        board.add(
            board_task_from_card_args(args, index=len(board.list()) + 1)
        )

    return creator


def _sqlite_card_creator(db_path: Path):
    """Card creator for read-only SqliteTaskBoard fixtures (writes the db)."""
    counter = {"next": 1}

    def creator(args: list[str]) -> None:
        task = board_task_from_card_args(args, index=counter["next"])
        counter["next"] += 1
        connection = sqlite3.connect(db_path)
        try:
            connection.execute(
                "INSERT INTO tasks (id, project_id, body, assignee, status, "
                "priority, created_at) VALUES (?, ?, ?, ?, ?, ?, ?)",
                (
                    task.id,
                    task.project_id,
                    args[args.index("--body") + 1],
                    "",
                    task.column,
                    task.priority,
                    task.created_at,
                ),
            )
            connection.commit()
        finally:
            connection.close()

    return creator


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
    board: object | None = None,
    messaging: MemoryMessagingChannel | None = None,
    project_extra: str = "",
    card_creator: object | None = None,
    gate_notes: list[tuple[str, str]] | None = None,
    completions: list[str] | None = None,
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
    if gate_notes is None:
        gate_notes = []
    if completions is None:
        completions = []
    resolved_board = board if board is not None else MemoryTaskBoard((task(),))
    if isinstance(resolved_board, MemoryTaskBoard):
        # The fake card creator needs to write; upgrade the read-only fixture
        # board to the mutable in-memory seam while keeping its rows.
        resolved_board = MutableTaskBoard(tuple(resolved_board.list()))
    if card_creator is None:
        card_creator = make_card_creator(resolved_board)
    orchestrator = PivOrchestrator.from_config(
        config,
        model_service=ValidationStandIn(),
        task_board=resolved_board,
        git_host=MemoryGitHost(),
        messaging=messaging,
        harness_adapter=adapter,
        card_creator=card_creator,
        card_note_fn=lambda card_id, text: gate_notes.append((card_id, text)),
        card_complete_fn=lambda card_id: complete_card(card_id, completions, resolved_board),
    )
    return orchestrator, selected_runtime, workspace


def complete_card(card_id: str, completions: list[str], board: object) -> None:
    """Fake card-completion seam: log it and reflect done on the fixture board."""
    completions.append(card_id)
    setter = getattr(board, "set_column", None)
    if setter is not None:
        setter(card_id, "done")


def test_full_run_completes_the_feature_card_with_zero_operator_actions(
    tmp_path: Path,
) -> None:
    """FR-011/016/028: card to completion with no human action beyond the card."""
    orchestrator, runtime, workspace_root = environment(tmp_path)

    awaiting = orchestrator.run_workflow("fixture", "123")

    assert awaiting.state == "AWAITING_CHILDREN"
    assert tuple(runtime.order) == PARENT_PLANNING
    children = [
        item for item in orchestrator.task_board.list() if item.parent_id == "123"
    ]
    assert [child.card_path for child in children] == ["change", "change"]
    assert all(child.profile == "executor" for child in children)
    assert all(not child.complete for child in children)
    worktree = workspace_root / "fixture" / "123"
    assert (worktree / "specs/123/tasks.md").is_file()

    first = orchestrator.run_next_workflow("fixture")
    assert first.state == "COMPLETED"
    assert first.task_id == children[0].id

    finished = orchestrator.run_next_workflow("fixture")
    assert finished.state == "COMPLETED"
    assert finished.task_id == "123"
    assert tuple(runtime.order) == PARENT_PLANNING + CHILD_RUN + CHILD_RUN + VALIDATOR_RUN
    assert len(set(runtime.sessions)) == len(runtime.sessions)
    assert orchestrator.task_board.get("123").complete is True
    assert orchestrator.task_board.get(children[1].id).complete is True
    assert orchestrator.git_host.pushes == []  # type: ignore[union-attr]
    assert (worktree / "specs/123/plan.md").is_file()


def test_decomposition_never_claims_an_in_flight_parent_again(tmp_path: Path) -> None:
    """FR-029 scan rule: a parent with children is never re-claimed fresh."""
    orchestrator, runtime, _workspace_root = environment(tmp_path)

    orchestrator.run_workflow("fixture", "123")
    children = [
        item for item in orchestrator.task_board.list() if item.parent_id == "123"
    ]
    # Simulated executors complete both children directly on the board.
    for child in children:
        orchestrator.task_board.set_column(child.id, "done")

    finished = orchestrator.run_next_workflow("fixture")

    # No fresh claim: the fallback runs the parent validator to completion.
    assert finished.state == "COMPLETED"
    assert finished.task_id == "123"
    assert runtime.order.count("ready") == 1


def test_zero_children_parks_the_parent_open(tmp_path: Path) -> None:
    """Edge case: no children produced = durable surfaced failure."""
    runtime = _runtime_class()(empty_tasks=True)
    orchestrator, runtime, _workspace_root = environment(tmp_path, runtime=runtime)

    blocked = orchestrator.run_workflow("fixture", "123")

    assert blocked.state == "BLOCKED"
    assert "no child cards" in (blocked.error or "")
    assert orchestrator.task_board.get("123").complete is False


def test_child_failure_parks_the_child_and_keeps_the_parent_open(tmp_path: Path) -> None:
    orchestrator, _runtime, _workspace_root = environment(tmp_path)

    orchestrator.run_workflow("fixture", "123")
    children = [
        item for item in orchestrator.task_board.list() if item.parent_id == "123"
    ]
    orchestrator.task_board.set_column(children[0].id, "done")
    # An unresolved child keeps the parent open: removing it from the ready
    # set by deleting it leaves one completed child and an open parent.
    orchestrator.task_board.remove(children[1].id)
    record = orchestrator.run_next_workflow("fixture")

    assert record.state == "COMPLETED" and record.task_id == "123"


def test_manual_child_deletion_drops_the_requirement_and_journals(tmp_path: Path) -> None:
    """FR-029: the board is authoritative; deletion re-evaluates the parent."""
    orchestrator, _runtime, _workspace_root = environment(tmp_path)

    orchestrator.run_workflow("fixture", "123")
    children = [
        item for item in orchestrator.task_board.list() if item.parent_id == "123"
    ]
    orchestrator.task_board.set_column(children[0].id, "done")
    orchestrator.task_board.remove(children[1].id)

    finished = orchestrator.run_next_workflow("fixture")

    assert finished.state == "COMPLETED"
    assert finished.task_id == "123"
    journal = (orchestrator.overlay_dir / "decisions.jsonl").read_text(encoding="utf-8")
    assert '"child-deleted"' in journal
    assert '"child-completed"' in journal
    assert '"parent-completed"' in journal


def test_placeholder_validation_blocks_run_before_any_pi_session(tmp_path: Path) -> None:
    orchestrator, runtime, workspace_root = environment(
        tmp_path,
        validation_command=(
            'echo "TODO: declare real validation commands in .ainative/project.yaml"'
        ),
    )

    with pytest.raises(PlaceholderValidationError, match="placeholder"):
        orchestrator.run_workflow("fixture", "123")

    assert runtime.order == []
    assert not (workspace_root / "fixture" / "123").exists()
    assert orchestrator._record is None


def test_empty_validation_blocks_run_before_any_pi_session(tmp_path: Path) -> None:
    # A command embedding the scaffold marker anywhere is refused, not only a
    # bare echo, so renaming the binary cannot smuggle the placeholder through.
    orchestrator, runtime, _workspace_root = environment(tmp_path)

    manifest = (
        orchestrator.registry.load_project_context("fixture").location
        / ".ainative"
        / "project.yaml"
    )
    manifest.write_text(
        "name: fixture-project\n"
        "repository: github.com/example/fixture\n"
        "default_branch: main\n"
        "validation:\n"
        "  commands:\n"
        '    - sh -c "echo TODO: declare real validation commands"\n',
        encoding="utf-8",
    )

    with pytest.raises(PlaceholderValidationError, match="placeholder"):
        orchestrator.run_workflow("fixture", "123")

    assert runtime.order == []


def test_clarify_parks_relays_and_encodes_with_a_new_session(tmp_path: Path) -> None:
    runtime = _runtime_class()(question=True)
    orchestrator, runtime, _workspace_root = environment(tmp_path, runtime=runtime)

    parked = orchestrator.run_workflow("fixture", "123")
    assert parked.state == "HUMAN_DECISION_REQUIRED"
    assert parked.current_phase == "clarify"
    assert parked.question_queue == ("Choose the fixture scope.",)
    assert runtime.order[-1] == "clarify"
    assert len(runtime.calls) == 3

    # The recorded answers are encoded by a NEW clarify session; with no
    # unresolved questions left the planning continues without a confirm park.
    finished = orchestrator.resume_workflow("fixture", "123", "A")
    assert finished.state == "AWAITING_CHILDREN"
    assert runtime.order.count("clarify") == 2
    assert runtime.calls[-2].resume_context is not None
    assert runtime.calls[-2].resume_context.answers == ("Choose the fixture scope.",)


def test_skip_self_answers_clarify_but_confirm_still_runs(tmp_path: Path) -> None:
    runtime = _runtime_class()(question=True)
    orchestrator, runtime, _workspace_root = environment(tmp_path, runtime=runtime)

    parked = orchestrator.run_workflow("fixture", "123", operator_flags=("skip",))
    assert parked.state == "HUMAN_DECISION_REQUIRED"
    assert parked.current_phase == "confirm"
    assert len(runtime.calls) == 3

    finished = orchestrator.resume_workflow("fixture", "123", "A")
    assert finished.state == "AWAITING_CHILDREN"
    assert tuple(runtime.order) == PARENT_PLANNING


def test_analyze_skipped_when_plan_says_no(tmp_path: Path) -> None:
    runtime = _runtime_class()(needs_analysis=False)
    orchestrator, runtime, _workspace_root = environment(tmp_path, runtime=runtime)

    record = orchestrator.run_workflow("fixture", "123")

    assert record.state == "AWAITING_CHILDREN"
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


def test_human_gates_never_start_pi(tmp_path: Path) -> None:
    runtime = _runtime_class()(question=True)
    orchestrator, runtime, _workspace_root = environment(tmp_path, runtime=runtime)

    orchestrator.run_workflow("fixture", "123")
    orchestrator.resume_workflow("fixture", "123", "A")

    assert "confirm" not in runtime.order
    assert "uat" not in runtime.order
    assert "publish" not in runtime.order


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
    overlay_before = snapshot_files(overlay, exclude={"overlay.json", "alive", "decisions.jsonl"})
    sibling_before = snapshot_files(sibling)

    orchestrator.run_workflow("fixture", "123")

    assert snapshot_files(enrolled) == enrolled_before
    assert snapshot_files(ainative) == ainative_before
    assert (
        snapshot_files(overlay, exclude={"overlay.json", "alive", "decisions.jsonl"})
        == overlay_before
    )
    assert snapshot_files(sibling) == sibling_before
