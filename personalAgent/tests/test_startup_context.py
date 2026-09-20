"""Focused checks for exact Hermes startup context loading."""

from __future__ import annotations

import json
import os
from pathlib import Path

import pytest

from hermes_kanban.startup_context import (
    CONTEXT_ROLES,
    PRECEDENCE_ORDER,
    StartupContextError,
    StartupDiagnostic,
    load_startup_context,
    resolve_precedence,
)


def _config(tmp_path: Path, paths: dict[str, str]) -> Path:
    config = tmp_path / "config.yaml"
    config.write_text(
        "context:\n"
        + "".join(f"  {role}: {path}\n" for role, path in paths.items()),
        encoding="utf-8",
    )
    return config


def _files(tmp_path: Path) -> dict[str, str]:
    paths: dict[str, str] = {}
    for role in CONTEXT_ROLES:
        path = tmp_path / f"{role}.md"
        path.write_text(f"sentinel-{role}\n", encoding="utf-8")
        paths[role] = str(path)
    return paths


def test_loads_all_roles_in_fixed_order_and_hashes_bytes(tmp_path: Path) -> None:
    paths = _files(tmp_path)

    snapshot = load_startup_context(_config(tmp_path, paths))

    assert tuple(snapshot.files) == CONTEXT_ROLES
    assert tuple(item.role for item in snapshot.registrations) == CONTEXT_ROLES
    assert snapshot.text_for("system") == "sentinel-system\n"
    assert snapshot.registrations[0].configured_path == Path(paths["hermes_instructions"])
    assert len(snapshot.registrations[0].revision) == 64


@pytest.mark.parametrize(
    ("role", "value", "reason"),
    (
        ("system", "/Users/emad/SYSTEM.md", "host-only path"),
        ("system", "relative/SYSTEM.md", "not absolute"),
    ),
)
def test_rejects_non_container_paths_without_fallback(
    tmp_path: Path, role: str, value: str, reason: str
) -> None:
    paths = _files(tmp_path)
    paths[role] = value
    config = _config(tmp_path, paths)

    with pytest.raises(StartupContextError, match=rf"{role}.*{reason}"):
        load_startup_context(config)


@pytest.mark.parametrize(
    ("role", "setup", "reason"),
    (
        ("system", lambda _path: None, "missing"),
        ("system", lambda path: path.mkdir(), "directory or not a regular file"),
        ("system", lambda path: path.write_text(" \n", encoding="utf-8"), "empty"),
        ("system", lambda path: path.write_bytes(b"\xff"), "invalid UTF-8"),
    ),
)
def test_invalid_files_fail_closed_and_name_role_and_path(
    tmp_path: Path, role: str, setup, reason: str
) -> None:
    paths = _files(tmp_path)
    path = Path(paths[role])
    path.unlink()
    setup(path)
    config = _config(tmp_path, paths)

    with pytest.raises(StartupContextError) as raised:
        load_startup_context(config)

    assert role in str(raised.value)
    assert str(path) in str(raised.value)
    assert reason in str(raised.value)


def test_unreadable_file_fails_without_printing_contents(tmp_path: Path) -> None:
    paths = _files(tmp_path)
    path = Path(paths["system"])
    path.chmod(0)
    try:
        with pytest.raises(StartupContextError, match="system.*not readable"):
            load_startup_context(_config(tmp_path, paths))
    finally:
        path.chmod(0o644)


def test_duplicate_resolved_registration_is_rejected(tmp_path: Path) -> None:
    paths = _files(tmp_path)
    paths["user"] = paths["system"]

    with pytest.raises(StartupContextError, match="user.*duplicate registration"):
        load_startup_context(_config(tmp_path, paths))


def test_missing_file_is_not_created(tmp_path: Path) -> None:
    paths = _files(tmp_path)
    missing = Path(paths["user"])
    missing.unlink()

    with pytest.raises(StartupContextError):
        load_startup_context(_config(tmp_path, paths))

    assert not missing.exists()


def test_revision_changes_when_source_bytes_change(tmp_path: Path) -> None:
    paths = _files(tmp_path)
    config = _config(tmp_path, paths)
    first = load_startup_context(config).registrations[1]

    Path(paths["system"]).write_text("changed-system\n", encoding="utf-8")
    second = load_startup_context(config).registrations[1]

    assert first.configured_path == second.configured_path
    assert first.revision != second.revision


def test_metadata_view_contains_no_registered_file_body(tmp_path: Path) -> None:
    paths = _files(tmp_path)
    snapshot = load_startup_context(_config(tmp_path, paths))
    metadata = repr(snapshot.registrations)

    assert "sentinel-" not in metadata
    assert all(item.revision for item in snapshot.registrations)


def test_precedence_returns_highest_authority_candidate() -> None:
    candidates = {layer: f"value-{layer}" for layer in PRECEDENCE_ORDER}

    assert resolve_precedence(candidates) == "value-platform_safety"
    assert resolve_precedence({"system": "system", "user": "user"}) == "system"
    assert resolve_precedence({}) is None


def test_diagnostic_renders_metadata_only(tmp_path: Path) -> None:
    paths = _files(tmp_path)
    snapshot = load_startup_context(_config(tmp_path, paths))
    diagnostic = StartupDiagnostic(
        ainative_root=tmp_path / "ainative",
        available_agents=("tester",),
        configured_projects=("fixture",),
        workspace_root=tmp_path / "workspaces",
        active_harness="pi",
        persistent_state_path=tmp_path / "overlay",
        context_registrations=snapshot.registrations,
    )

    rendered = diagnostic.render()
    payload = json.loads(rendered)
    assert payload["context_registrations"][1]["path"] == paths["system"]
    assert "sentinel-" not in rendered
    assert "secret-value" not in rendered


def test_diagnostic_does_not_depend_on_environment_secret_values(tmp_path: Path) -> None:
    paths = _files(tmp_path)
    snapshot = load_startup_context(_config(tmp_path, paths))
    os.environ["HERMES_TEST_SECRET"] = "secret-value"
    try:
        diagnostic = StartupDiagnostic(
            tmp_path,
            (),
            (),
            tmp_path,
            "pi",
            tmp_path,
            snapshot.registrations,
        )
        assert "secret-value" not in diagnostic.render()
    finally:
        os.environ.pop("HERMES_TEST_SECRET", None)
