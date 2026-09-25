"""Hermetic contract checks for the 019 onboarding extension (FR-021..FR-029).

No network, no live board, no live model: fixture databases and seam
injection only, mirroring `tests/test_onboarding.py` patterns.
"""

from __future__ import annotations

import sqlite3
import subprocess
from pathlib import Path

import pytest

from hermes_kanban.executor import ExecutionSettings, profile_for_card
from hermes_kanban.onboard import (
    ImportPrdRequest,
    OnboardError,
    OnboardRequest,
    PrdDraftError,
    run_import_prd,
    run_onboard,
    validate_card_draft,
)
from hermes_kanban.orchestrator import BoardTask, WorkflowRecord
from test_piv_orchestrator import PARENT_PLANNING  # noqa: F401  (shared order)

REPOSITORY = "owner/new-project"
NATIVE_ID = "p_1234567"

_CARD_BODY_HEADINGS = ("Path", "Profile", "Parent", "Dependencies")


def write_projects_db(tmp_path: Path, rows: list[tuple[str, str]]) -> Path:
    database = tmp_path / "projects.db"
    connection = sqlite3.connect(database)
    connection.execute("create table projects (id text, slug text)")
    connection.executemany("insert into projects values (?, ?)", rows)
    connection.commit()
    connection.close()
    return database


def write_config(tmp_path: Path, workspace_root: Path, entries: str = "") -> Path:
    workspace_root.mkdir(parents=True, exist_ok=True)
    config = tmp_path / "config.yaml"
    config.write_text(
        f"workspace:\n  root: {workspace_root}\nprojects:\n{entries}",
        encoding="utf-8",
    )
    return config


def write_kanban_db(tmp_path: Path) -> Path:
    """A minimal native board the read-only adapter can read."""
    database = tmp_path / "hermes-home" / "kanban.db"
    database.parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(database)
    connection.execute(
        "create table tasks ("
        "id text primary key, project_id text, body text, assignee text, "
        "status text, priority text, created_at text)"
    )
    connection.execute("create table task_links (parent_id text, child_id text)")
    connection.execute(
        "insert into tasks values ('seed', 'p_1234567', "
        "'## Priority\nP1\n\n## Problem\nseed\n\n## Expected Result\nseed\n', "
        "'', 'todo', 'P1', '2026-09-01T00:00:00Z')"
    )
    connection.commit()
    connection.close()
    return database


def _git(*args: str, cwd: Path | None = None) -> None:
    subprocess.run(["git", *args], cwd=cwd, check=True, capture_output=True)


def fake_cloner(url: str, location: Path, branch: str) -> None:
    location.mkdir(parents=True)
    _git("init", "-b", branch, cwd=location)
    _git("remote", "add", "origin", url, cwd=location)
    _git("commit", "--allow-empty", "-m", "seed", cwd=location)


def request(**overrides: object) -> OnboardRequest:
    values: dict[str, object] = {"repository": REPOSITORY}
    values.update(overrides)
    return OnboardRequest(**values)  # type: ignore[arg-type]


def test_onboarding_records_a_readable_primary_board(tmp_path: Path, monkeypatch) -> None:
    """FR-021: after onboarding the primary board exists and is discoverable."""
    board = write_kanban_db(tmp_path)
    monkeypatch.setenv("HERMES_HOME", str(board.parent))
    workspace = tmp_path / "workspaces"
    config = write_config(tmp_path, workspace)
    projects_db = write_projects_db(tmp_path, [(NATIVE_ID, "owner/new-project")])

    result = run_onboard(request(), config, cloner=fake_cloner, projects_db=projects_db)

    assert result.board_path == board
    assert board.is_file()


def test_onboard_fails_closed_without_a_native_board(tmp_path: Path, monkeypatch) -> None:
    """FR-008/FR-021: a missing board fails closed with no partial enrollment."""
    monkeypatch.setenv("HERMES_HOME", str(tmp_path / "hermes-home"))
    workspace = tmp_path / "workspaces"
    config = write_config(tmp_path, workspace)
    projects_db = write_projects_db(tmp_path, [(NATIVE_ID, "owner/new-project")])
    before = config.read_text(encoding="utf-8")

    with pytest.raises(OnboardError, match="missing or unreadable"):
        run_onboard(request(), config, cloner=fake_cloner, projects_db=projects_db)

    assert config.read_text(encoding="utf-8") == before
    assert not (workspace / "new-project").exists()


def test_board_check_is_read_only_in_dry_run(tmp_path: Path, monkeypatch, capsys) -> None:
    """Guarantee 13 + FR-021: the projected board result is in the plan."""
    board = write_kanban_db(tmp_path)
    monkeypatch.setenv("HERMES_HOME", str(board.parent))
    workspace = tmp_path / "workspaces"
    config = write_config(tmp_path, workspace)
    projects_db = write_projects_db(tmp_path, [(NATIVE_ID, "owner/new-project")])
    before = config.read_text(encoding="utf-8")

    result = run_onboard(
        request(dry_run=True), config, cloner=fake_cloner, projects_db=projects_db
    )

    assert result.board_path == board
    assert result.scaffolded == ()
    assert config.read_text(encoding="utf-8") == before
    assert not (workspace / "new-project").exists()

    from hermes_kanban.runtime import _print_onboard_result

    _print_onboard_result(result, dry_run=True)
    assert f"board: {board}" in capsys.readouterr().out


def test_re_enrollment_returns_the_same_board_zero_diffs(
    tmp_path: Path,
    monkeypatch,
) -> None:
    """SC-003: idempotent re-run = identical identity and board, zero diffs."""
    board = write_kanban_db(tmp_path)
    monkeypatch.setenv("HERMES_HOME", str(board.parent))
    workspace = tmp_path / "workspaces"
    config = write_config(tmp_path, workspace)
    projects_db = write_projects_db(tmp_path, [(NATIVE_ID, "owner/new-project")])

    first = run_onboard(request(), config, cloner=fake_cloner, projects_db=projects_db)
    snapshot = (
        config.read_bytes(),
        tuple(
            row
            for row in sqlite3.connect(board).execute("select * from tasks").fetchall()
        ),
        tuple(
            (path.name, path.read_bytes())
            for path in sorted(first.location.rglob("*"))
            if path.is_file()
        ),
    )

    second = run_onboard(request(), config, cloner=fake_cloner, projects_db=projects_db)

    assert second.already_enrolled is True
    assert second.board_path == first.board_path
    assert second.native_id == first.native_id
    assert second.scaffolded == ()
    connection = sqlite3.connect(board)
    after_rows = tuple(connection.execute("select * from tasks").fetchall())
    connection.close()
    assert after_rows == snapshot[1]
    assert config.read_bytes() == snapshot[0]
    assert (
        tuple(
            (path.name, path.read_bytes())
            for path in sorted(first.location.rglob("*"))
            if path.is_file()
        )
        == snapshot[2]
    )


def test_created_cards_belong_to_the_enrolled_project(tmp_path: Path) -> None:
    """FR-022: a Feature Card on the primary board carries the native project."""
    prd = tmp_path / "prd.md"
    prd.write_text(
        "## Ship login\n\nPriority: P1\n\nUsers cannot sign in.\n\n"
        "Expected result: users can sign in.\n",
        encoding="utf-8",
    )
    created: list[list[str]] = []

    def creator(args: list[str]) -> None:
        created.append(args)

    result = run_import_prd(
        ImportPrdRequest(
            repository=REPOSITORY,
            prd=prd,
            drafts_out=tmp_path / "drafts",
            create_cards=True,
        ),
        _config_for(tmp_path),
        card_creator=creator,
    )

    assert result.created_cards == ("Ship login",)
    assert created
    args = created[0]
    assert args[args.index("--project") + 1] == NATIVE_ID
    body = args[args.index("--body") + 1]
    assert "## Path\nfeature" in body
    assert "## Profile\ntask-generator" in body
    assert "## Parent" not in body


def _config_for(tmp_path: Path) -> Path:
    workspace = tmp_path / "workspaces"
    entries = (
        "  - id: new-project\n"
        f"    name: {REPOSITORY}\n"
        f"    repository: {REPOSITORY}\n"
        f"    location: {workspace / 'new-project'}\n"
        "    kanban_project_ids:\n"
        f"      - {NATIVE_ID}\n"
    )
    return write_config(tmp_path, workspace, entries=entries)


VALID_BODY = (
    "# Example\n\n## Priority\nP1\n\n## Problem\nBody.\n\n"
    "## Expected Result\nDone.\n"
)


def test_card_draft_rejects_workflow_state_paths(tmp_path: Path) -> None:
    """FR-027: no card path accepts a workflow-state Path or Profile value."""
    for state in ("ready", "specify", "clarify", "confirm", "plan", "tasks",
                  "implement", "converge", "critic", "tester", "uat",
                  "pr-review", "publish"):
        with pytest.raises(PrdDraftError, match="workflow state"):
            validate_card_draft(VALID_BODY + f"\n## Path\n{state}\n")
        with pytest.raises(PrdDraftError):
            validate_card_draft(VALID_BODY + f"\n## Profile\n{state}\n")


def test_card_draft_rejects_invalid_card_paths(tmp_path: Path) -> None:
    with pytest.raises(PrdDraftError, match="card path must be one of"):
        validate_card_draft(VALID_BODY + "\n## Path\nepic\n")


def test_profile_rejects_provider_and_vendor_names(tmp_path: Path) -> None:
    """FR-014: profiles express strategy, never a provider or vendor."""
    for value in ("openai", "gpt-4", "anthropic", "claude-3"):
        with pytest.raises(PrdDraftError, match="provider"):
            validate_card_draft(VALID_BODY + f"\n## Profile\n{value}\n")
    with pytest.raises(PrdDraftError, match="named reference"):
        validate_card_draft(VALID_BODY + "\n## Profile\nsome/provider\n")


def test_profile_accepts_execution_roles_and_named_strategies(tmp_path: Path) -> None:
    """FR-013: the three roles (optionally role:strategy) are recognized."""
    for value in (
        "task-generator",
        "executor",
        "validator",
        "executor:fast-lane",
        "validator:strict",
    ):
        validate_card_draft(VALID_BODY + f"\n## Profile\n{value}\n")


def test_task_generator_is_a_profile_role_never_a_card(tmp_path: Path) -> None:
    """FR-024: task-generator is a role, never a workflow state or card."""
    validate_card_draft(VALID_BODY + "\n## Profile\ntask-generator\n")
    # `task-generator` is never a Path value (it is not a card path).
    with pytest.raises(PrdDraftError, match="card path must be one of"):
        validate_card_draft(VALID_BODY + "\n## Path\ntask-generator\n")


def test_feature_card_without_profile_gets_the_path_default() -> None:
    """FR-014a: feature → task-generator; change/job → executor defaults."""
    feature = BoardTask(
        id="1",
        project_id="p",
        problem="p",
        expected_result="e",
        acceptance_criteria="a",
        priority="P1",
        created_at="2026-09-01T00:00:00Z",
        card_path="feature",
    )
    change = BoardTask(
        id="2",
        project_id="p",
        problem="p",
        expected_result="e",
        acceptance_criteria="a",
        priority="P1",
        created_at="2026-09-01T00:00:00Z",
        card_path="change",
    )
    job = BoardTask(
        id="3",
        project_id="p",
        problem="p",
        expected_result="e",
        acceptance_criteria="a",
        priority="P1",
        created_at="2026-09-01T00:00:00Z",
        card_path="job",
        card_skill="prd-writer",
    )

    assert profile_for_card(feature) == "task-generator"
    assert profile_for_card(change) == "executor"
    assert profile_for_card(job) == "executor"


def test_profile_defaults_are_configurable_per_path(tmp_path: Path) -> None:
    config = tmp_path / "config.yaml"
    config.write_text(
        "profiles:\n  defaults:\n    change: validator\n",
        encoding="utf-8",
    )
    settings = ExecutionSettings.from_config(config)
    change = BoardTask(
        id="2",
        project_id="p",
        problem="p",
        expected_result="e",
        acceptance_criteria="a",
        priority="P1",
        created_at="2026-09-01T00:00:00Z",
        card_path="change",
    )

    assert settings.path_profile_defaults == {"change": "validator"}
    assert profile_for_card(change, path_defaults=settings.path_profile_defaults) == (
        "validator"
    )


def test_profile_defaults_reject_provider_names(tmp_path: Path) -> None:
    config = tmp_path / "config.yaml"
    config.write_text(
        "profiles:\n  defaults:\n    feature: openai\n",
        encoding="utf-8",
    )

    with pytest.raises(Exception, match="profiles.defaults.feature"):
        ExecutionSettings.from_config(config)


def test_operator_profile_override_is_honored_and_validated() -> None:
    """FR-014a: an operator override wins; a provider override is rejected."""
    overridden = BoardTask(
        id="1",
        project_id="p",
        problem="p",
        expected_result="e",
        acceptance_criteria="a",
        priority="P1",
        created_at="2026-09-01T00:00:00Z",
        card_path="feature",
        profile="executor:nightly",
    )
    leaked = BoardTask(
        id="2",
        project_id="p",
        problem="p",
        expected_result="e",
        acceptance_criteria="a",
        priority="P1",
        created_at="2026-09-01T00:00:00Z",
        card_path="feature",
        profile="openai",
    )

    assert profile_for_card(overridden) == "executor:nightly"
    with pytest.raises(Exception, match="provider"):
        profile_for_card(leaked)


def test_prd_import_lands_top_level_feature_cards(tmp_path: Path) -> None:
    """FR-019: N PRD sections become N top-level Feature Cards."""
    prd = tmp_path / "prd.md"
    prd.write_text(
        "## Ship login\n\nPriority: P1\n\nUsers cannot sign in.\n\n"
        "Expected result: users can sign in.\n\n"
        "## Dark mode toggle\n\nUsers want a dark theme.\n\n"
        "Expected result: a dark theme can be enabled.\n",
        encoding="utf-8",
    )
    created: list[list[str]] = []

    def creator(args: list[str]) -> None:
        created.append(args)

    result = run_import_prd(
        ImportPrdRequest(
            repository=REPOSITORY,
            prd=prd,
            drafts_out=tmp_path / "drafts",
            create_cards=True,
        ),
        _config_for(tmp_path),
        card_creator=creator,
    )

    assert len(created) == 2
    assert result.created_cards == ("Ship login", "Dark mode toggle")
    for args in created:
        body = args[args.index("--body") + 1]
        assert "## Path\nfeature" in body
        assert "## Profile\ntask-generator" in body
        assert "## Parent" not in body


def test_prd_draft_only_import_writes_nothing_to_the_board(tmp_path: Path) -> None:
    """FR-019 preservation: drafts are files; nothing is written to the board."""
    prd = tmp_path / "prd.md"
    prd.write_text("## Dark mode\n\nUsers want a dark theme.\n", encoding="utf-8")
    created: list[list[str]] = []

    result = run_import_prd(
        ImportPrdRequest(
            repository=REPOSITORY,
            prd=prd,
            drafts_out=tmp_path / "drafts",
        ),
        _config_for(tmp_path),
        card_creator=lambda args: created.append(args),
    )

    assert result.drafts
    assert all(path.is_file() for path in result.drafts)
    assert result.created_cards == ()
    assert created == []


def test_malformed_parent_sections_fail_closed_at_the_boundary(tmp_path: Path) -> None:
    """T039/research D9: malformed `## Parent` is rejected fail-closed."""
    self_parent = (
        "# Ship login\n\n## Priority\nP1\n\n## Problem\nBody.\n\n"
        "## Expected Result\nDone.\n\n## Parent\nShip login\n"
    )
    with pytest.raises(PrdDraftError, match="must not reference the card itself"):
        validate_card_draft(self_parent)

    empty_parent = VALID_BODY + "\n## Parent\n\n"
    with pytest.raises(PrdDraftError, match="exactly one task id"):
        validate_card_draft(empty_parent)

    multi = VALID_BODY + "\n## Parent\n123\n456\n"
    with pytest.raises(PrdDraftError, match="exactly one task id"):
        validate_card_draft(multi)


def test_top_level_prd_cards_never_carry_a_parent(tmp_path: Path) -> None:
    """Hierarchy invariant: a Feature Card has no `## Parent`."""
    prd = tmp_path / "prd.md"
    prd.write_text(
        "## Feature\n\nPriority: P1\n\nSomething is wanted.\n\n"
        "Expected result: something exists.\n",
        encoding="utf-8",
    )
    created: list[list[str]] = []

    run_import_prd(
        ImportPrdRequest(
            repository=REPOSITORY,
            prd=prd,
            drafts_out=tmp_path / "drafts",
            create_cards=True,
        ),
        _config_for(tmp_path),
        card_creator=lambda args: created.append(args),
    )

    for args in created:
        body = args[args.index("--body") + 1]
        assert "## Parent" not in body


def test_workflow_record_owns_no_lifecycle_columns() -> None:
    """E1/FR-015: the orchestrator record holds no lifecycle columns, and no
    card field encodes an internal workflow state."""
    record_fields = set(WorkflowRecord.__dataclass_fields__)  # type: ignore[attr-defined]
    task_fields = set(BoardTask.__dataclass_fields__)  # type: ignore[attr-defined]
    lifecycle = {"column", "complete", "assignee", "priority"}
    assert not record_fields & lifecycle
    assert {"id", "project_id", "dependencies", "parent_id", "profile"} <= task_fields
    workflow_states = {
        "ready",
        "specify",
        "clarify",
        "confirm",
        "plan",
        "tasks",
        "implement",
        "converge",
        "critic",
        "tester",
        "uat",
        "pr-review",
        "publish",
    }
    assert not task_fields & workflow_states
