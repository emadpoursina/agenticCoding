"""Shared disposable fixtures for the harness boundary."""

from __future__ import annotations

import importlib.util
import os
import shutil
import subprocess
from pathlib import Path

import pytest


@pytest.fixture
def pi_runtime():
    path = Path(__file__).parent / "fixtures" / "pi-runtime" / "runtime.py"
    spec = importlib.util.spec_from_file_location("pi_fixture_runtime", path)
    if spec is None or spec.loader is None:
        raise RuntimeError("Pi fixture runtime cannot be loaded")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module.PiFixtureRuntime()


@pytest.fixture
def standard_project_fixture(tmp_path: Path) -> Path:
    source = Path(__file__).parent / "fixtures" / "projects" / "standard"
    target = tmp_path / "project"
    shutil.copytree(source, target)
    return target


@pytest.fixture
def disposable_worktree(tmp_path: Path) -> Path:
    worktree = tmp_path / "worktree"
    worktree.mkdir()
    return worktree


@pytest.fixture
def fake_pi(pi_runtime):
    return pi_runtime


@pytest.fixture
def child_process_cleanup():
    processes: list[subprocess.Popen[bytes]] = []
    yield processes
    for process in processes:
        if process.poll() is None:
            process.terminate()
            try:
                process.wait(timeout=1)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait(timeout=1)


@pytest.fixture
def snapshot_files():
    def snapshot(
        root: Path,
        *,
        exclude: set[str] | frozenset[str] = frozenset(),
    ) -> dict[str, bytes]:
        files: dict[str, bytes] = {}
        for path in root.rglob("*"):
            relative = path.relative_to(root)
            if (
                path.is_file()
                and ".git" not in relative.parts
                and relative.as_posix() not in exclude
            ):
                files[relative.as_posix()] = path.read_bytes()
        return files

    return snapshot


@pytest.fixture
def protected_paths_snapshot(snapshot_files):
    return snapshot_files


@pytest.fixture
def no_secret():
    def assert_safe(value: object) -> None:
        text = repr(value).lower()
        assert "bearer " not in text
        assert "-----begin " not in text
        for name, secret in os.environ.items():
            if secret and len(secret) >= 4 and any(
                token in name.upper() for token in ("KEY", "TOKEN", "SECRET", "PASSWORD")
            ):
                assert secret not in repr(value)

    return assert_safe
