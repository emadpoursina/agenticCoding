"""Live-style fixture checks for the new generic harness path."""

from __future__ import annotations

from pathlib import Path

import pytest

import hermes_kanban.runtime as runtime
from hermes_kanban.github import MemoryGitHost
from hermes_kanban.orchestrator import MemoryTaskBoard
from hermes_kanban.startup_context import (
    StartupContextError,
    StartupContextSnapshot,
    StartupDiagnostic,
)
from test_piv_orchestrator import environment, task


def test_validation_failure_keeps_github_untouched(tmp_path: Path) -> None:
    host = MemoryGitHost()
    orchestrator, _runtime, _workspace_root = environment(
        tmp_path,
        validation_command="false",
    )
    orchestrator.git_host = host

    record = orchestrator.run_workflow("fixture", "123")

    assert record.state in {"HUMAN_DECISION_REQUIRED", "FAILED", "BLOCKED"}
    assert host.pushes == []
    assert host.upserts == []


def test_completed_harness_reaches_existing_feature_branch_pr_path(tmp_path: Path) -> None:
    host = MemoryGitHost()
    orchestrator, _runtime, _workspace_root = environment(tmp_path)
    orchestrator.git_host = host

    record = orchestrator.run_workflow("fixture", "123")

    assert record.state == "PR_CREATED"
    assert len(host.pushes) == 1
    assert len(host.upserts) == 1


def test_next_ready_keeps_task_selection_in_hermes(tmp_path: Path) -> None:
    board = MemoryTaskBoard((task(id="ready", column="ready"),))
    orchestrator, _runtime, _workspace_root = environment(tmp_path, board=board)

    record = orchestrator.run_next_workflow()

    assert record.task_id == "ready"


def test_live_entry_prefers_dispatcher_board_path(
    tmp_path: Path,
    monkeypatch,
) -> None:
    selected: list[Path] = []
    sentinel = object()

    class RecordingBoard:
        def __init__(self, path: Path, **_kwargs: object) -> None:
            selected.append(path)

    monkeypatch.setattr(runtime, "load_harness_config", lambda _path: None)
    monkeypatch.setattr(
        runtime,
        "load_startup_context",
        lambda _path: StartupContextSnapshot(files={}, registrations=()),
    )
    monkeypatch.setattr(runtime, "SqliteTaskBoard", RecordingBoard)
    monkeypatch.setattr(
        runtime.PivOrchestrator,
        "from_config",
        staticmethod(lambda _path, **kwargs: sentinel),
    )
    monkeypatch.setenv("HERMES_KANBAN_DB", str(tmp_path / "board.db"))
    monkeypatch.setenv("HERMES_HOME", str(tmp_path / "legacy-home"))
    config = tmp_path / "config.yaml"
    config.write_text("projects: []\n", encoding="utf-8")

    assert runtime.build_live_orchestrator(config) is sentinel
    assert selected == [tmp_path / "board.db"]


def test_live_entry_validates_context_before_board_selection(tmp_path: Path, monkeypatch) -> None:
    events: list[str] = []
    sentinel = object()

    class RecordingBoard:
        def __init__(self, _path: Path, **_kwargs: object) -> None:
            events.append("board")

    monkeypatch.setattr(
        runtime,
        "load_startup_context",
        lambda _path: (
            events.append("context") or StartupContextSnapshot(files={}, registrations=())
        ),
    )
    monkeypatch.setattr(runtime, "load_harness_config", lambda _path: events.append("harness"))
    monkeypatch.setattr(runtime, "SqliteTaskBoard", RecordingBoard)
    monkeypatch.setattr(
        runtime.PivOrchestrator,
        "from_config",
        staticmethod(lambda _path, **kwargs: sentinel),
    )
    monkeypatch.setenv("HERMES_KANBAN_DB", str(tmp_path / "board.db"))
    monkeypatch.setenv("HERMES_HOME", str(tmp_path / "legacy-home"))
    config = tmp_path / "config.yaml"
    config.write_text("projects: []\n", encoding="utf-8")

    runtime.build_live_orchestrator(config)

    assert events[:2] == ["context", "harness"]
    assert events.index("context") < events.index("board")


def test_live_entry_stops_before_board_when_context_is_invalid(
    tmp_path: Path, monkeypatch
) -> None:
    selected: list[Path] = []

    class RecordingBoard:
        def __init__(self, path: Path, **_kwargs: object) -> None:
            selected.append(path)

    def reject(_path: Path) -> StartupContextSnapshot:
        raise StartupContextError("user", "/opt/data/hermes-context/USER.md", "missing")

    monkeypatch.setattr(runtime, "load_startup_context", reject)
    monkeypatch.setattr(runtime, "SqliteTaskBoard", RecordingBoard)
    monkeypatch.setenv("HERMES_KANBAN_DB", str(tmp_path / "board.db"))

    with pytest.raises(StartupContextError, match="user.*USER.md.*missing"):
        runtime.build_live_orchestrator(tmp_path / "config.yaml")

    assert selected == []


def test_doctor_prints_only_the_safe_startup_diagnostic(
    tmp_path: Path, monkeypatch, capsys
) -> None:
    diagnostic = StartupDiagnostic(
        ainative_root=tmp_path / "ainative",
        available_agents=("tester",),
        configured_projects=("fixture",),
        workspace_root=tmp_path / "workspaces",
        active_harness="pi",
        persistent_state_path=tmp_path / "overlay",
        context_registrations=(),
    )
    monkeypatch.setattr(
        runtime,
        "build_live_orchestrator",
        lambda _path: type("DoctorResult", (), {"startup_diagnostic": diagnostic})(),
    )

    assert runtime.main(["--config", str(tmp_path / "config.yaml"), "--doctor"]) == 0

    output = capsys.readouterr().out
    assert '"active_harness": "pi"' in output
    assert "SYSTEM.md" not in output
