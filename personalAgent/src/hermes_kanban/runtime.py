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
from .onboard import (
    ImportPrdRequest,
    OnboardRequest,
    OnboardResult,
    run_import_prd,
    run_onboard,
)
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
    ProjectRegistryError,
    UnknownProjectError,
    _parse_document,
    is_placeholder_validation,
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
        placeholder_validation_projects=tuple(
            project.id
            for project in orchestrator.registry.list_projects()
            if _project_has_placeholder_validation(project.id, orchestrator.registry)
        ),
    )


def _project_has_placeholder_validation(
    project_id: str, registry: ProjectRegistry
) -> bool:
    """Check one enrolled project's manifest for placeholder validation."""
    try:
        context = registry.load_project_context(project_id)
    except ProjectRegistryError:
        return False
    return is_placeholder_validation(context.validation_commands)


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


def _native_board_path(hermes_home: Path, registry: ProjectRegistry) -> Path:
    """Resolve the native Kanban database for the enrolled project set."""
    candidates = [
        hermes_home / "kanban" / "boards" / project.id / "kanban.db"
        for project in registry.list_projects()
    ]
    candidates.append(hermes_home / "kanban.db")
    for candidate in candidates:
        if candidate.is_file():
            return candidate
    return candidates[-1]


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
    registry = ProjectRegistry.from_config(config_path)
    resolver = _project_resolver(registry)
    kanban_db = os.environ.get("HERMES_KANBAN_DB", "").strip()
    if kanban_db:
        board = SqliteTaskBoard(Path(kanban_db), resolve_project_id=resolver)
    else:
        hermes_home = os.environ.get("HERMES_HOME", "").strip()
        if not hermes_home:
            raise MissingTaskBoardError("HERMES_HOME is required for the live Kanban board")
        board = SqliteTaskBoard(
            _native_board_path(Path(hermes_home), registry),
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
    parser.add_argument("--onboard", metavar="OWNER/NAME")
    parser.add_argument("--import-prd", metavar="OWNER/NAME", dest="import_prd")
    parser.add_argument("--branch", default="main")
    parser.add_argument("--project-id")
    parser.add_argument("--prd", type=Path)
    parser.add_argument("--drafts-out", type=Path)
    parser.add_argument("--default-priority", default="P2")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--create-cards", action="store_true")
    parser.add_argument("--allow-todo", action="store_true")
    parser.add_argument("--push-scaffold", action="store_true", dest="push_scaffold")
    return parser


def _print_onboard_result(result: OnboardResult, *, dry_run: bool) -> None:
    """Print a short operator summary for one onboarding run."""
    print(f"onboard target: {result.repository}")
    print(f"project_id: {result.project_id}")
    print(f"native_id: {result.native_id}")
    print(f"location: {result.location}")
    print(f"default_branch: {result.default_branch}")
    print(f"cloned: {'yes' if result.cloned else 'no'}")
    print(f"pushed: {'yes' if result.pushed else 'no'}")
    scaffolded = ", ".join(result.scaffolded) if result.scaffolded else "(nothing new)"
    print(f"scaffolded: {scaffolded}")
    if result.already_enrolled:
        print("status: already enrolled and ready")
    if result.drafts:
        for path in result.drafts:
            print(f"draft: {path}")
        if result.incomplete_drafts:
            print(
                f"incomplete drafts: {result.incomplete_drafts} "
                "(fill TODO sections before grooming)"
            )
    if result.created_cards:
        for title in result.created_cards:
            print(f"card: {title}")
        if result.triaged_cards:
            print(f"triaged cards: {result.triaged_cards} (incomplete drafts parked in triage)")
    elif result.drafts and not dry_run:
        print("cards: not created (pass --create-cards to publish drafts to the board)")
    if dry_run:
        print("status: dry run — no changes were written")


def _print_import_result(result: OnboardResult, *, dry_run: bool) -> None:
    """Print a short operator summary for one PRD import run."""
    print(f"import target: {result.repository}")
    print(f"project_id: {result.project_id}")
    print(f"native_id: {result.native_id}")
    if result.incomplete_drafts:
        print(
            f"incomplete drafts: {result.incomplete_drafts} "
            "(fill TODO sections before grooming)"
        )
    if result.created_cards:
        for title in result.created_cards:
            print(f"card: {title}")
        if result.triaged_cards:
            print(f"triaged cards: {result.triaged_cards} (incomplete drafts parked in triage)")
    elif not dry_run:
        print("cards: not created (pass --create-cards to publish drafts to the board)")
    if dry_run:
        print("status: dry run — the PRD parsed; no drafts or cards were written")


def _bare_invocation(args: argparse.Namespace, selectors: int) -> bool:
    """Return whether the process was started with only --config."""
    return (
        selectors == 0
        and not args.onboard
        and not args.import_prd
        and not args.doctor
        and not args.smoke
        and not args.skip
        and not args.repo
        and args.branch == "main"
        and args.default_priority == "P2"
        and not args.dry_run
        and not args.create_cards
        and not args.allow_todo
        and not args.push_scaffold
        and args.prd is None
        and args.drafts_out is None
        and args.project_id is None
    )


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
    onboard_only = (
        any(value is not None for value in (args.drafts_out, args.project_id))
        or args.default_priority != "P2"
        or args.dry_run
        or args.create_cards
        or args.allow_todo
        or args.push_scaffold
    )
    if args.onboard and (selectors or args.doctor or args.smoke or args.skip or args.import_prd):
        print("--onboard cannot be combined with other workflow selectors", file=sys.stderr)
        return 2
    if args.import_prd and (selectors or args.doctor or args.smoke or args.skip or args.onboard):
        print("--import-prd cannot be combined with other workflow selectors", file=sys.stderr)
        return 2
    if args.import_prd and args.prd is None:
        print("--import-prd requires --prd", file=sys.stderr)
        return 2
    if onboard_only and not args.onboard and not args.import_prd:
        print(
            "--prd/--drafts-out/--project-id/--default-priority/--dry-run/"
            "--create-cards/--allow-todo require --onboard or --import-prd",
            file=sys.stderr,
        )
        return 2
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
    if _bare_invocation(args, selectors):
        if sys.stdin.isatty():
            from .guide import run_guide

            return run_guide(args.config)
        print("choose exactly one task, next-ready, resume, or smoke mode", file=sys.stderr)
        return 2
    if (
        not args.onboard
        and not args.import_prd
        and not args.doctor
        and not args.smoke
        and selectors != 1
    ):
        print("choose exactly one task, next-ready, resume, or smoke mode", file=sys.stderr)
        return 2
    try:
        if args.import_prd:
            result = run_import_prd(
                ImportPrdRequest(
                    repository=args.import_prd,
                    prd=args.prd,
                    drafts_out=args.drafts_out,
                    default_priority=args.default_priority,
                    dry_run=args.dry_run,
                    create_cards=args.create_cards,
                    allow_todo=args.allow_todo,
                ),
                args.config,
            )
            _print_import_result(result, dry_run=args.dry_run)
            return 0
        if args.onboard:
            result = run_onboard(
                OnboardRequest(
                    repository=args.onboard,
                    branch=args.branch,
                    project_id=args.project_id,
                    prd=args.prd,
                    drafts_out=args.drafts_out,
                    default_priority=args.default_priority,
                    dry_run=args.dry_run,
                    create_cards=args.create_cards,
                    allow_todo=args.allow_todo,
                    push_scaffold=args.push_scaffold,
                ),
                args.config,
            )
            _print_onboard_result(result, dry_run=args.dry_run)
            return 0
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
