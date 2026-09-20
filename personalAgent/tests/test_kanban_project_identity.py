"""Native Kanban project-id translation and one-identity checks."""

from __future__ import annotations

import sqlite3
from dataclasses import replace
from pathlib import Path

import pytest

from hermes_kanban.board import SqliteTaskBoard
from hermes_kanban.orchestrator import NoReadyTaskError
from hermes_kanban.projects import ProjectRegistry
from hermes_kanban.runtime import _native_board_path
from test_piv_orchestrator import _runtime_class, environment

_ALIAS = "    kanban_project_ids:\n      - p_fixture\n"


def _write_board(
    db_path: Path,
    *,
    project_id: str,
    task_id: str = "123",
    status: str = "ready",
    priority: str = "P1",
) -> None:
    connection = sqlite3.connect(db_path)
    try:
        connection.execute(
            "CREATE TABLE tasks ("
            "id TEXT PRIMARY KEY, project_id TEXT, body TEXT, assignee TEXT, "
            "status TEXT, priority TEXT, created_at TEXT)"
        )
        connection.execute("CREATE TABLE task_links (parent_id TEXT, child_id TEXT)")
        body = (
            "## Problem\nAdd an isolated note\n\n"
            "## Expected Result\nA note exists\n\n"
            "## Acceptance Criteria\nnote exists\n\n"
            f"## Priority\n{priority}\n"
        )
        connection.execute(
            "INSERT INTO tasks (id, project_id, body, assignee, status, priority, created_at) "
            "VALUES (?, ?, ?, ?, ?, ?, ?)",
            (task_id, project_id, body, "owner", status, priority, "2026-09-01T00:00:00Z"),
        )
        connection.commit()
    finally:
        connection.close()


def _resolver(mapping: dict[str, str]):
    return lambda project_id: mapping.get(project_id, project_id)


def test_board_translates_a_declared_native_id(tmp_path: Path) -> None:
    db_path = tmp_path / "board.db"
    _write_board(db_path, project_id="p_fixture")
    board = SqliteTaskBoard(db_path, resolve_project_id=_resolver({"p_fixture": "fixture"}))

    assert board.get("123").project_id == "fixture"
    assert board.list()[0].project_id == "fixture"


def test_board_leaves_an_undeclared_native_id_unchanged(tmp_path: Path) -> None:
    db_path = tmp_path / "board.db"
    _write_board(db_path, project_id="p_other")
    board = SqliteTaskBoard(db_path, resolve_project_id=_resolver({"p_fixture": "fixture"}))

    assert board.get("123").project_id == "p_other"


def test_board_without_a_resolver_keeps_the_row_value(tmp_path: Path) -> None:
    db_path = tmp_path / "board.db"
    _write_board(db_path, project_id="p_fixture")
    board = SqliteTaskBoard(db_path)

    assert board.get("123").project_id == "p_fixture"


def _registry_for(tmp_path: Path) -> ProjectRegistry:
    config = tmp_path / "config.yaml"
    config.write_text(
        "projects:\n"
        "  - id: fixture\n"
        "    name: Fixture\n"
        "    repository: repo\n"
        f"    location: {tmp_path / 'missing'}\n",
        encoding="utf-8",
    )
    return ProjectRegistry.from_config(config)


def test_board_path_prefers_the_per_board_database(tmp_path: Path) -> None:
    registry = _registry_for(tmp_path)
    board_db = tmp_path / "kanban" / "boards" / "fixture" / "kanban.db"
    board_db.parent.mkdir(parents=True)
    board_db.write_bytes(b"stub")

    assert _native_board_path(tmp_path, registry) == board_db


def test_board_path_falls_back_to_the_legacy_single_database(tmp_path: Path) -> None:
    registry = _registry_for(tmp_path)
    legacy = tmp_path / "kanban.db"
    legacy.write_bytes(b"stub")

    assert _native_board_path(tmp_path, registry) == legacy


def test_board_path_defaults_to_the_legacy_layout_when_no_file_exists(
    tmp_path: Path,
) -> None:
    registry = _registry_for(tmp_path)

    assert _native_board_path(tmp_path, registry) == tmp_path / "kanban.db"


def test_next_ready_runs_a_native_id_card_under_the_operational_id(tmp_path: Path) -> None:
    db_path = tmp_path / "board.db"
    _write_board(db_path, project_id="p_fixture")
    board = SqliteTaskBoard(db_path, resolve_project_id=_resolver({"p_fixture": "fixture"}))
    orchestrator, _runtime, workspace_root = environment(
        tmp_path,
        board=board,
        project_extra=_ALIAS,
    )

    record = orchestrator.run_next_workflow()

    assert record.project_id == "fixture"
    assert record.task.project_id == "fixture"
    assert record.state == "PR_CREATED"
    assert (workspace_root / "fixture" / "123").is_dir()
    assert not (workspace_root / "p_fixture").exists()


def test_next_ready_names_an_unmapped_native_id(tmp_path: Path) -> None:
    db_path = tmp_path / "board.db"
    _write_board(db_path, project_id="p_other")
    board = SqliteTaskBoard(db_path, resolve_project_id=_resolver({"p_fixture": "fixture"}))
    orchestrator, _runtime, _workspace_root = environment(
        tmp_path,
        board=board,
        project_extra=_ALIAS,
    )

    with pytest.raises(NoReadyTaskError, match="p_other"):
        orchestrator.run_next_workflow()


def test_resume_accepts_a_declared_alias(tmp_path: Path) -> None:
    runtime = _runtime_class()(question=True)
    orchestrator, _runtime, _workspace_root = environment(
        tmp_path,
        runtime=runtime,
        project_extra=_ALIAS,
    )

    parked = orchestrator.run_workflow("fixture", "123")
    assert parked.state == "HUMAN_DECISION_REQUIRED"
    confirmed = orchestrator.resume_workflow("p_fixture", "123", "A")
    assert confirmed.state == "HUMAN_DECISION_REQUIRED"
    finished = orchestrator.resume_workflow("p_fixture", "123", "A")
    assert finished.state == "PR_CREATED"
    assert finished.project_id == "fixture"


def test_board_record_canonicalizes_a_legacy_alias_record(tmp_path: Path) -> None:
    orchestrator, _runtime, _workspace_root = environment(tmp_path, project_extra=_ALIAS)
    record = orchestrator.run_workflow("fixture", "123")
    legacy = replace(
        record,
        project_id="p_fixture",
        task=replace(record.task, project_id="p_fixture"),
    )

    canonical = orchestrator._board_record(legacy)

    assert canonical.project_id == "fixture"
    assert canonical.task.project_id == "fixture"
