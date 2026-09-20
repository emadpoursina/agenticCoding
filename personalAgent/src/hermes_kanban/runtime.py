"""The single Hermes worker and command-line start surface."""

from __future__ import annotations

import argparse
import os
import re
import subprocess
import sys
from collections.abc import Callable
from pathlib import Path
from urllib.parse import urlparse

from .board import SqliteTaskBoard
from .executor import ModelService
from .external_framework import load_harness_config
from .github import GitHost, LiveGitHost
from .messaging import HermesTelegramChannel, MessagingChannel
from .orchestrator import (
    MemoryTaskBoard,
    MissingTaskBoardError,
    OrchestratorError,
    PivOrchestrator,
    TaskBoard,
)
from .projects import (
    ProjectRecord,
    ProjectRegistry,
    UnknownProjectError,
    _parse_document,
)
from .startup_context import (
    StartupContextSnapshot,
    StartupDiagnostic,
    load_startup_context,
)


class SmokeTargetError(OrchestratorError):
    """Raised when a smoke target is absent or does not identify one repo."""


def _project_resolver(registry: ProjectRegistry) -> Callable[[str], str]:
    """Return a native-id resolver that leaves unmapped ids unchanged."""

    def resolve(project_id: str) -> str:
        try:
            return registry.canonical_id(project_id)
        except UnknownProjectError:
            return project_id

    return resolve


def build_startup_diagnostic(
    orchestrator: PivOrchestrator,
    snapshot: StartupContextSnapshot,
) -> StartupDiagnostic:
    """Build a metadata-only diagnostic from the live Hermes objects."""
    return StartupDiagnostic(
        ainative_root=orchestrator.executor.adapter.settings.path,
        available_agents=tuple(orchestrator.executor.adapter.list_agents()),
        configured_projects=tuple(
            project.name for project in orchestrator.registry.list_projects()
        ),
        workspace_root=orchestrator.workspaces.workspace_root,
        active_harness=(
            orchestrator.harness_adapter.identity
            if orchestrator.harness_adapter is not None
            else ""
        ),
        persistent_state_path=orchestrator.overlay_dir,
        context_registrations=snapshot.registrations,
        project_kanban_ids={
            project.id: project.kanban_project_ids
            for project in orchestrator.registry.list_projects()
            if project.kanban_project_ids
        },
    )


def _telegram_enabled(config_path: Path) -> bool:
    try:
        document = _parse_document(config_path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, ValueError):
        return False
    notifications = document.get("notifications")
    if not isinstance(notifications, dict):
        return False
    telegram = notifications.get("telegram")
    return isinstance(telegram, dict) and telegram.get("enabled") is True


def _github_identity(remote: str | None) -> str | None:
    value = (remote or "").strip()
    if value.startswith("git@github.com:"):
        value = value.removeprefix("git@github.com:")
    elif value.startswith("ssh://git@github.com/"):
        value = value.removeprefix("ssh://git@github.com/")
    else:
        parsed = urlparse(value)
        if parsed.hostname != "github.com":
            return None
        value = parsed.path.lstrip("/")
    value = value.removesuffix(".git").strip("/")
    if re.fullmatch(r"[^/\s]+/[^/\s]+", value):
        return value
    return None


def _project_remote(project: ProjectRecord) -> str | None:
    try:
        result = subprocess.run(
            ["git", "-C", str(project.location), "remote", "get-url", "origin"],
            check=True,
            capture_output=True,
            text=True,
        )
    except (OSError, subprocess.CalledProcessError):
        return None
    return _github_identity(result.stdout)


def validate_smoke_target(orchestrator: PivOrchestrator, requested: str | None) -> ProjectRecord:
    """Validate the named repo before the workflow can publish anything."""
    target = (requested or "").strip()
    if not re.fullmatch(r"[^/\s]+/[^/\s]+", target):
        raise SmokeTargetError("smoke requires an explicit disposable owner/name")
    matches = [
        project for project in orchestrator.registry.list_projects() if project.name == target
    ]
    if len(matches) != 1:
        raise SmokeTargetError("smoke target must match exactly one enrolled project name")
    project = orchestrator.registry.resolve_eligible_project(matches[0].id)
    remote = _project_remote(project)
    if remote != target or project.name != target:
        raise SmokeTargetError(
            "smoke target must match both the GitHub remote and enrolled project name"
        )
    return project


def build_live_orchestrator(
    config_path: Path,
    *,
    model_service: ModelService | None = None,
    git_host: GitHost | None = None,
    messaging: MessagingChannel | None = None,
    clock: Callable[[], float] | None = None,
    allow_running_task_id: str | None = None,
    task_board: TaskBoard | None = None,
    telegram_adapter: object | None = None,
    gateway_adapter: object | None = None,
    home_chat_id: str | None = None,
) -> PivOrchestrator:
    """Build the production orchestrator against Hermes' one native board."""
    startup_context = load_startup_context(config_path)
    if isinstance(task_board, MemoryTaskBoard):
        raise MissingTaskBoardError("MemoryTaskBoard is only available to checks")
    if task_board is not None:
        raise MissingTaskBoardError("live entry owns the native Kanban board")
    load_harness_config(config_path)
    resolver = _project_resolver(ProjectRegistry.from_config(config_path))
    kanban_db = os.environ.get("HERMES_KANBAN_DB", "").strip()
    if kanban_db:
        board = SqliteTaskBoard(Path(kanban_db), resolve_project_id=resolver)
    else:
        hermes_home = os.environ.get("HERMES_HOME", "").strip()
        if not hermes_home:
            raise MissingTaskBoardError("HERMES_HOME is required for the live Kanban board")
        board = SqliteTaskBoard(
            Path(hermes_home) / "kanban.db",
            resolve_project_id=resolver,
        )
    worker_task = allow_running_task_id
    if worker_task is None:
        worker_task = os.environ.get("HERMES_KANBAN_TASK", "").strip() or None
    live_messaging = messaging
    if live_messaging is None and _telegram_enabled(config_path):
        chat_id = (home_chat_id or os.environ.get("TELEGRAM_HOME_CHANNEL", "")).strip()
        adapter = telegram_adapter if telegram_adapter is not None else gateway_adapter
        if chat_id and adapter is not None:
            live_messaging = HermesTelegramChannel(adapter, chat_id)
    orchestrator = PivOrchestrator.from_config(
        config_path,
        model_service=model_service,
        task_board=board,
        git_host=git_host if git_host is not None else LiveGitHost(),
        messaging=live_messaging,
        clock=clock,
        allow_running_task_id=worker_task,
        startup_context=startup_context,
    )
    if isinstance(orchestrator, PivOrchestrator):
        orchestrator.startup_diagnostic = build_startup_diagnostic(orchestrator, startup_context)
    return orchestrator


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="hermes_kanban")
    parser.add_argument("--config", type=Path, required=True)
    parser.add_argument("--task")
    parser.add_argument("--next-ready", action="store_true")
    parser.add_argument("--resume", nargs=3, metavar=("PROJECT", "TASK", "OPTION"))
    parser.add_argument("--smoke", action="store_true")
    parser.add_argument("--repo")
    parser.add_argument("--skip", action="store_true")
    parser.add_argument("--doctor", action="store_true")
    return parser


def main(argv: list[str] | None = None) -> int:
    """Run one named, next-ready, resume, or guarded smoke operation."""
    args = _parser().parse_args(argv)
    worker_task = os.environ.get("HERMES_KANBAN_TASK", "").strip() or None
    task_id = (
        None
        if args.doctor
        else args.task or (worker_task if not args.next_ready and not args.resume else None)
    )
    selectors = sum(bool(value) for value in (task_id, args.next_ready, args.resume))
    if args.doctor and (selectors or args.smoke):
        print("--doctor cannot be combined with a workflow selector", file=sys.stderr)
        return 2
    if args.smoke and args.resume:
        print("smoke cannot resume a parked workflow", file=sys.stderr)
        return 2
    if args.smoke and task_id and args.next_ready:
        print("smoke cannot select both a task and next-ready", file=sys.stderr)
        return 2
    if args.smoke and selectors != 1:
        print("smoke requires exactly one task or next-ready selector", file=sys.stderr)
        return 2
    if not args.doctor and not args.smoke and selectors != 1:
        print("choose exactly one task, next-ready, resume, or smoke mode", file=sys.stderr)
        return 2
    try:
        orchestrator = build_live_orchestrator(args.config)
        if args.doctor:
            diagnostic = getattr(orchestrator, "startup_diagnostic", None)
            if not isinstance(diagnostic, StartupDiagnostic):
                raise OrchestratorError("startup diagnostic is unavailable")
            print(diagnostic.render())
            return 0
        record = None
        if args.smoke:
            requested = args.repo or os.environ.get("HERMES_SMOKE_REPO", "")
            project = validate_smoke_target(orchestrator, requested)
            print(f"smoke target verified: {project.name}")
            if task_id:
                task = orchestrator.task_board.get(task_id)
                if task.project_id != project.id:
                    raise SmokeTargetError("smoke task belongs to another enrolled project")
                kwargs = {"operator_flags": ("skip",)} if args.skip else {}
                record = orchestrator.run_workflow(project.id, task_id, **kwargs)
            elif args.next_ready:
                kwargs = {"operator_flags": ("skip",)} if args.skip else {}
                record = orchestrator.run_next_workflow(project.id, **kwargs)
        elif args.resume:
            project_id, resume_task, option = args.resume
            record = orchestrator.resume_workflow(project_id, resume_task, option)
        elif args.next_ready:
            kwargs = {"operator_flags": ("skip",)} if args.skip else {}
            record = orchestrator.run_next_workflow(**kwargs)
        else:
            task = orchestrator.task_board.get(task_id or "")
            kwargs = {"operator_flags": ("skip",)} if args.skip else {}
            record = orchestrator.run_workflow(task.project_id, task.id, **kwargs)
        if record is not None and record.state == "PR_CREATED":
            assert record.pull_request is not None
            print(f"PR_CREATED #{record.pull_request.number} {record.pull_request.html_url}")
        elif record is not None and record.state == "HUMAN_DECISION_REQUIRED":
            print(f"workflow waiting for decision: {record.next_action}")
        if record is not None and record.state in {"FAILED", "BLOCKED"}:
            message = record.error or record.next_action
            print(f"workflow {record.state.lower()}: {message}", file=sys.stderr)
            return 1
    except Exception as exc:
        print(str(exc), file=sys.stderr)
        return 1
    return 0
