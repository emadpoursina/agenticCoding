"""Hermes orchestration over the canonical feature-loop state graph.

Hermes owns the graph overlay: current state, per-step dispatch, compact
report checks, human parks, and publish. Every agent state starts exactly
one new Pi session for that step only; `confirm`, `uat`, and `publish`
never start Pi. The graph itself lives in
`/ainative/docs/systems/feature-loop.md` and is linked, not copied.
"""

from __future__ import annotations

import subprocess
import threading
import time
import uuid
from collections.abc import Callable, Sequence
from dataclasses import dataclass, field, replace
from pathlib import Path
from typing import TYPE_CHECKING, Protocol

from .executor import (
    AgentExecutor,
    ModelService,
    profile_for_card,
)
from .external_framework import (
    AGENT_LOOP_STATES,
    HUMAN_STATES,
    LOOP_STATES,
    PARENT_STATES,
    HarnessAdapter,
    HarnessResult,
    ResumeContext,
    StepReport,
)
from .messaging import MessagingChannel, SendRecord, SendStatus, parse_option_letter
from .onboard import (
    CardCreateFn,
    child_card_args,
    live_add_card_note,
    live_complete_card,
    live_create_card,
)
from .persist import (
    InvalidOverlayDirError,
    OverlaySnapshot,
    PersistError,
    SlotHeldError,
    alive_is_fresh,
    append_decision,
    load_overlay_dir,
    read_decisions,
    read_overlay,
    touch_alive,
    validate_overlay_dir,
    write_overlay,
)
from .projects import (
    DisabledProjectError,
    InvalidProjectLocationError,
    ProjectRegistry,
    UnknownProjectError,
    _path_like_id,
    is_placeholder_validation,
)
from .workspace import (
    InvalidTaskIdError,
    ProtectedBranchError,
    WorkspaceError,
    WorkspaceManager,
)

if TYPE_CHECKING:
    from .github import GitHost, PullRequestIdentity
    from .startup_context import StartupContextSnapshot

_PRIORITIES = {"P0", "P1", "P2", "P3"}
_ACTIVE_STATES = {
    "QUEUED",
    "RUNNING",
    "HUMAN_DECISION_REQUIRED",
    "RETRYABLE_FAILURE",
    "BLOCKED",
}
_TERMINAL_STATES = {"COMPLETED", "FAILED", "PR_CREATED"}
# Parent record parked between decomposition and validation. It is durable in
# the overlay (never a board card, FR-010) but keeps the single workflow slot
# free so child Task Cards stay claimable (FR-025).
_AWAITING_CHILDREN = "AWAITING_CHILDREN"
_RECOVERY_BUDGET = 3
_PUBLISH_BUDGET = 3
# The 013 overlay phase machine and the older removed stage names. Records
# carrying them are superseded by 018 and park for a human (FR-012).
_LEGACY_PHASES = frozenset(
    {
        "execution",
        "human",
        "validation",
        "github",
        "discovery",
        "planning",
        "implementation",
        "diagnosis",
        "debug",
    }
)
_SKIP_ASSUMPTIONS = (
    "Use the task description and acceptance criteria as the specification.",
    "Resolve routine wording from the existing project context.",
)


class LoopState:
    """Canonical graph state ids (plain data; the graph is linked, not copied).

    Source of truth: ``/ainative/docs/systems/feature-loop.md``. Agent-kind
    states start one new Pi session each; ``confirm`` and ``uat`` are human
    gates; ``publish`` is Hermes/GitHub only. ``change`` and ``job`` are
    short card paths; the feature graph itself is unchanged.
    """

    READY = "ready"
    SPECIFY = "specify"
    CLARIFY = "clarify"
    CONFIRM = "confirm"
    PLAN = "plan"
    TASKS = "tasks"
    ANALYZE = "analyze"
    IMPLEMENT = "implement"
    CONVERGE = "converge"
    CRITIC = "critic"
    TESTER = "tester"
    UAT = "uat"
    PR_REVIEW = "pr-review"
    PUBLISH = "publish"
    CHANGE = "change"
    JOB = "job"


class OrchestratorError(Exception):
    """Base error for orchestration boundaries."""


class MissingTaskBoardError(OrchestratorError):
    pass


class IneligibleColumnError(OrchestratorError):
    pass


class IncompleteTaskError(OrchestratorError):
    pass


class UnknownTaskError(OrchestratorError):
    pass


class TaskProjectMismatchError(OrchestratorError):
    pass


class InvalidPriorityError(OrchestratorError):
    pass


class UnmetDependenciesError(OrchestratorError):
    pass


class NoReadyTaskError(OrchestratorError):
    pass


class WorkflowBusyError(OrchestratorError):
    pass


class ResumeNotParkedError(OrchestratorError):
    pass


class InvalidDecisionError(OrchestratorError):
    pass


class InvalidCardPathError(OrchestratorError):
    pass


class InvalidJobSkillError(OrchestratorError):
    pass


class PlaceholderValidationError(OrchestratorError):
    """Raised when a project's declared validation commands cannot prove anything."""


_CARD_PATHS = frozenset({"feature", "change", "job"})
_JOB_SKILLS = frozenset({"prd-writer", "project-bootstrapper"})


@dataclass(frozen=True)
class BoardTask:
    id: str
    project_id: str
    problem: str
    expected_result: str
    acceptance_criteria: str
    priority: str
    created_at: str
    platform: str = ""
    technical_notes: str = ""
    dependencies: tuple[str, ...] = ()
    owner: str = ""
    reviewer: str = ""
    complete: bool = False
    column: str = ""
    card_path: str = "feature"
    card_skill: str = ""
    parent_id: str = ""
    profile: str = ""


@dataclass(frozen=True)
class DecisionOption:
    letter: str
    text: str
    consequence: str | None = None


@dataclass(frozen=True)
class DecisionBrief:
    project_id: str
    task_id: str
    phase: str
    decision: str
    why_it_matters: str
    options: tuple[DecisionOption, ...]
    recommended: str | None = None
    reply_with: str = "option letter"


@dataclass(frozen=True)
class DiagnosticReport:
    task_id: str
    phase: str
    attempt: int
    failure: str
    what_was_attempted: str
    current_state: str
    decision_required: str = ""


@dataclass(frozen=True)
class StepRecord:
    state: str
    phase: str = ""
    worker: str | None = None
    execute_status: str | None = None
    questions: tuple[str, ...] = ()
    summary: str = ""


@dataclass(frozen=True)
class WorkflowRecord:
    run_id: str
    execution_id: str
    state: str
    workflow_name: str
    current_phase: str
    project_id: str
    task_id: str
    task: BoardTask
    next_action: str
    current_worker: str | None = None
    attempt: int = 1
    workspace_path: Path | None = None
    workspace_branch: str | None = None
    workspace_id: str | None = None
    validation_status: str = "pending"
    blockers: tuple[str, ...] = ()
    pull_request: PullRequestIdentity | None = None
    publish_attempt: int = 0
    decision: DecisionBrief | None = None
    chosen_option: str | None = None
    steps: tuple[StepRecord, ...] = ()
    error: str | None = None
    failure_class: str | None = None
    diagnostic: DiagnosticReport | None = None
    sends: tuple[SendRecord, ...] = ()
    resume_context: ResumeContext | None = None
    operator_flags: tuple[str, ...] = ()
    legacy_migration_reason: str | None = None
    legacy_acknowledged: bool = False
    state_attempts: dict[str, int] = field(default_factory=dict)
    converge_fingerprint: str | None = None
    question_queue: tuple[str, ...] = ()
    uat_checklist: tuple[str, ...] = ()
    analyze_requested: bool = False
    card_path: str = "feature"
    parent_task_id: str | None = None
    children: tuple[str, ...] = ()


class TaskBoard(Protocol):
    def get(self, task_id: str) -> BoardTask: ...

    def list(self) -> tuple[BoardTask, ...]: ...


class MemoryTaskBoard:
    """Fixture-only read-only task-board seam."""

    def __init__(self, tasks: Sequence[tuple]) -> None:
        from collections.abc import Sequence as _Sequence

        if not isinstance(tasks, _Sequence):
            raise TypeError("tasks must be a sequence")
        self._tasks = tuple(tasks)
        self._by_id = {task.id: task for task in self._tasks}

    def get(self, task_id: str) -> BoardTask:
        try:
            return self._by_id[task_id]
        except KeyError as exc:
            raise UnknownTaskError(f"unknown task: {task_id}") from exc

    def list(self) -> tuple[BoardTask, ...]:
        return self._tasks


def classify_publish(exc: BaseException) -> str:
    from .github import PublishError

    if isinstance(exc, PublishError):
        return exc.failure_class
    if isinstance(exc, subprocess.TimeoutExpired):
        return "TRANSIENT"
    if isinstance(exc, subprocess.CalledProcessError):
        text = f"{exc.stderr or ''} {exc.stdout or ''} {exc}".lower()
        if any(token in text for token in ("auth", "permission denied", "could not read username")):
            return "NON_RETRYABLE"
        return "TRANSIENT"
    return "NON_RETRYABLE"


def _diagnostic_text(report: DiagnosticReport) -> str:
    return (
        f"task: {report.task_id}\n"
        f"phase: {report.phase}\n"
        f"attempt: {report.attempt}\n"
        f"failure: {report.failure}\n"
        f"what was attempted: {report.what_was_attempted}\n"
        f"current state: {report.current_state}\n"
        f"decision required: {report.decision_required}"
    )


def _worker_for_step(step_id: str) -> str:
    """Return the worker name recorded for one state; human/parent are empty."""
    from .external_framework import AINATIVE_STEP_AGENTS

    if step_id in AINATIVE_STEP_AGENTS:
        return AINATIVE_STEP_AGENTS[step_id]
    return step_id if step_id in AGENT_LOOP_STATES else ""


def _artifact_for_step(step_id: str, task_id: str) -> str | None:
    """Return the native artifact a completed Spec Kit step must have written."""
    if step_id == "specify":
        return f"specs/{task_id}/spec.md"
    if step_id == "plan":
        return f"specs/{task_id}/plan.md"
    if step_id == "tasks":
        return f"specs/{task_id}/tasks.md"
    return None


def _publish_verdicts(steps: tuple) -> dict[str, str]:
    """Return the last recorded verdict per graph phase."""
    verdicts: dict[str, str] = {}
    for step in steps:
        if step.execute_status and step.phase:
            verdicts[step.phase] = step.execute_status
    return verdicts


class PivOrchestrator:
    """Select, run through the feature loop, and publish one task."""

    def __init__(
        self,
        executor: object,
        workspaces: WorkspaceManager,
        registry: ProjectRegistry,
        task_board: TaskBoard,
        git_host: GitHost | None = None,
        messaging: MessagingChannel | None = None,
        overlay_dir: Path | None = None,
        *,
        clock: Callable[[], float] | None = None,
        allow_running_task_id: str | None = None,
        harness_adapter: HarnessAdapter | None = None,
        startup_context: StartupContextSnapshot | None = None,
        card_creator: CardCreateFn | None = None,
        card_note_fn: Callable[[str, str], None] | None = None,
        card_complete_fn: Callable[[str], None] | None = None,
    ) -> None:
        from .executor import AgentExecutor
        from .github import LiveGitHost

        if task_board is None:
            raise MissingTaskBoardError("task board is required")
        if overlay_dir is None:
            raise InvalidOverlayDirError("execution.overlay_dir is required")
        if not isinstance(executor, AgentExecutor):
            raise OrchestratorError("executor must be an AgentExecutor")
        self.executor = executor
        self.workspaces = workspaces
        self.registry = registry
        self.task_board = task_board
        self.git_host = git_host if git_host is not None else LiveGitHost()
        self.messaging = messaging
        self.overlay_dir = validate_overlay_dir(overlay_dir)
        self.clock = clock or time.time
        self.allow_running_task_id = allow_running_task_id
        self.harness_adapter = harness_adapter or executor.harness_adapter
        self.startup_context = startup_context
        self.startup_diagnostic = None
        # Native board write seams (constitution III: writes ride the native
        # CLI; SqliteTaskBoard stays read-only). Injectable for checks.
        self.card_creator = card_creator if card_creator is not None else live_create_card
        self.card_note_fn = card_note_fn if card_note_fn is not None else live_add_card_note
        self.card_complete_fn = (
            card_complete_fn if card_complete_fn is not None else live_complete_card
        )
        self._record: WorkflowRecord | None = None
        self._ready = False
        self._heartbeat_stop: threading.Event | None = None
        self._heartbeat_thread: threading.Thread | None = None

    @classmethod
    def from_config(
        cls,
        config_path: Path,
        *,
        model_service: ModelService | None = None,
        task_board: TaskBoard | None = None,
        git_host: GitHost | None = None,
        messaging: MessagingChannel | None = None,
        clock: Callable[[], float] | None = None,
        allow_running_task_id: str | None = None,
        harness_adapter: HarnessAdapter | None = None,
        startup_context: StartupContextSnapshot | None = None,
        card_creator: CardCreateFn | None = None,
        card_note_fn: Callable[[str, str], None] | None = None,
        card_complete_fn: Callable[[str], None] | None = None,
    ) -> PivOrchestrator:
        from .github import LiveGitHost

        if task_board is None:
            raise MissingTaskBoardError("task board is required")
        executor = AgentExecutor.from_config(
            config_path,
            model_service=model_service,
            harness_adapter=harness_adapter,
        )
        orchestrator = cls(
            executor,
            executor.workspaces,
            executor.registry,
            task_board,
            git_host if git_host is not None else LiveGitHost(),
            messaging,
            load_overlay_dir(config_path),
            clock=clock,
            allow_running_task_id=allow_running_task_id,
            harness_adapter=executor.harness_adapter,
            startup_context=startup_context,
            card_creator=card_creator,
            card_note_fn=card_note_fn,
            card_complete_fn=card_complete_fn,
        )
        orchestrator.become_ready()
        return orchestrator

    def become_ready(self) -> WorkflowRecord | None:
        """Load the durable slot and park superseded whole-playbook records."""
        if self._ready:
            return self._record
        snapshot = read_overlay(self.overlay_dir)
        if snapshot is None:
            if alive_is_fresh(self.overlay_dir, clock=self.clock):
                raise SlotHeldError("another control-plane copy holds the workflow slot")
            self._ready = True
            return None
        record = snapshot.record
        if record is not None:
            record = self._board_record(record)
            if self._is_legacy_record(record):
                record = self._park_legacy(record)
        if record is None or record.state in _TERMINAL_STATES:
            self._record = record
            self._ready = True
            return record
        if alive_is_fresh(self.overlay_dir, clock=self.clock):
            raise SlotHeldError("another control-plane copy holds the workflow slot")
        if record.state == _AWAITING_CHILDREN:
            # Restarted while waiting for children: children truth is
            # re-derived from the board, never from a stored snapshot (D7).
            evaluated, incomplete = self._evaluate_children(record)
            self._set_record(evaluated)
            self._ready = True
            if incomplete:
                return evaluated
            return self.run_validator(evaluated)
        self._set_record(record)
        if record.state in {"HUMAN_DECISION_REQUIRED", "BLOCKED"}:
            self._ready = True
            return record
        try:
            reclaimed = self._reclaim(record)
        except Exception:
            self._stop_heartbeat()
            raise
        self._ready = True
        return reclaimed

    def _is_legacy_record(self, record: WorkflowRecord) -> bool:
        if record.legacy_acknowledged:
            return False
        if record.state == "PLANNING_COMPLETE":
            return True
        if record.current_phase in _LEGACY_PHASES:
            return True
        return any(
            step.phase in _LEGACY_PHASES or step.state == "PLANNING_COMPLETE"
            for step in record.steps
        )

    def _park_legacy(self, record: WorkflowRecord) -> WorkflowRecord:
        reason = "superseded by 018 — whole-playbook run"
        diagnostic = (
            "This in-flight whole-playbook overlay was superseded by the 018 "
            "feature loop; the removed stage machine will not resume it and "
            "Pi will not auto-start. A person decides how to continue."
        )
        brief = DecisionBrief(
            record.project_id,
            record.task_id,
            "human",
            diagnostic,
            "A person must decide how to continue this superseded task.",
            (DecisionOption("A", "Review the retained worktree and choose a new action"),),
        )
        return replace(
            record,
            state="HUMAN_DECISION_REQUIRED",
            current_phase="human",
            next_action="review the superseded task",
            decision=brief,
            legacy_migration_reason=reason,
            error=None,
        )

    def _board_record(self, record: WorkflowRecord) -> WorkflowRecord:
        task = self.task_board.get(record.task_id)
        project_id = self._canonical_project_id(record.project_id)
        if task.project_id != project_id:
            raise TaskProjectMismatchError(f"task {record.task_id} belongs to {task.project_id}")
        return replace(record, task=task, project_id=project_id)

    def _canonical_project_id(self, project_id: str) -> str:
        """Return the operational id for an enrolled id or alias, else the input."""
        try:
            return self.registry.canonical_id(project_id)
        except UnknownProjectError:
            return project_id

    def _reclaim(self, record: WorkflowRecord) -> WorkflowRecord:
        if record.workspace_path is None or not record.workspace_branch:
            return self._block(record.current_worker or "", None)
        expected = self.workspaces.workspace_root / record.project_id / record.task_id
        if record.workspace_path.resolve(strict=False) != expected.resolve(strict=False):
            return self._block(record.current_worker or "", None)
        try:
            recovered = self.workspaces.recover_workspace(
                record.project_id,
                record.task_id,
                workspace_id=record.workspace_id or "",
                execution_id=record.execution_id,
                branch=record.workspace_branch,
            )
        except WorkspaceError as exc:
            self._set_record(replace(record, error=str(exc)))
            return self._block(record.current_worker or "", None)
        current = replace(
            record,
            workspace_path=recovered.path,
            workspace_branch=recovered.branch,
            workspace_id=record.workspace_id or recovered.workspace_id,
            error=None,
        )
        self._set_record(current)
        if current.current_phase == "publish":
            return self._run_github(reclaim=True)
        if current.current_phase in AGENT_LOOP_STATES:
            # An interrupted agent state re-enters its own step; the per-state
            # attempt budget still applies.
            return self._enter_state(current.current_phase)
        return self._block(record.current_worker or "", None)

    def _set_record(self, record: WorkflowRecord | None) -> None:
        self._record = record
        occupied = record is not None and record.state in _ACTIVE_STATES
        write_overlay(
            self.overlay_dir,
            OverlaySnapshot(record=record, slot="occupied" if occupied else "free"),
        )
        if occupied:
            touch_alive(self.overlay_dir, clock=self.clock)
            self._start_heartbeat()
        else:
            self._stop_heartbeat()

    def _start_heartbeat(self) -> None:
        if self._heartbeat_thread is not None and self._heartbeat_thread.is_alive():
            return
        stop = threading.Event()
        self._heartbeat_stop = stop
        thread = threading.Thread(
            target=self._heartbeat_loop,
            args=(stop,),
            name="hermes-kanban-alive",
            daemon=True,
        )
        self._heartbeat_thread = thread
        thread.start()

    def _stop_heartbeat(self) -> None:
        if self._heartbeat_stop is not None:
            self._heartbeat_stop.set()
        thread = self._heartbeat_thread
        if thread is not None and thread is not threading.current_thread():
            thread.join(timeout=0.1)
        self._heartbeat_stop = None
        self._heartbeat_thread = None

    def _heartbeat_loop(self, stop: threading.Event) -> None:
        while not stop.wait(15.0):
            if self._record is None or self._record.state not in _ACTIVE_STATES:
                return
            touch_alive(self.overlay_dir, clock=self.clock)

    def _ensure_ready(self) -> None:
        if not self._ready:
            raise OrchestratorError("orchestrator is not ready")

    def run_workflow(
        self,
        project_id: str,
        task_id: str,
        *,
        operator_flags: tuple[str, ...] = (),
    ) -> WorkflowRecord:
        self._ensure_ready()
        self._assert_slot_free()
        if not isinstance(task_id, str) or _path_like_id(task_id):
            raise InvalidTaskIdError(f"invalid task id: {task_id}")
        self.registry.resolve_eligible_project(project_id)
        context = self.registry.load_project_context(project_id)
        if is_placeholder_validation(context.validation_commands):
            raise PlaceholderValidationError(
                f"project {project_id} declares placeholder or empty "
                "validation_commands; set real validation commands in "
                f"{context.location / '.ainative' / 'project.yaml'} before running work"
            )
        task = self.task_board.get(task_id)
        if task.project_id != project_id:
            raise TaskProjectMismatchError(f"task {task_id} belongs to {project_id}")
        self._validate_runnable(task)
        self._set_record(self._queued(task, operator_flags=operator_flags))
        try:
            prepared = self.workspaces.prepare_workspace(project_id, task_id)
            self._set_record(
                replace(
                    self._require_record(),
                    workspace_path=prepared.path,
                    workspace_branch=prepared.branch,
                    workspace_id=prepared.workspace_id,
                    execution_id=prepared.execution_id,
                )
            )
            return self._enter_state("ready")
        except Exception:
            record = self._record
            if record is not None and record.state in {
                "HUMAN_DECISION_REQUIRED",
                "BLOCKED",
            }:
                # A surfaced post-park failure (e.g. a gate marker CLI error)
                # leaves the park state unchanged for the operator (FR-017).
                self._set_record(record)
            else:
                self._set_record(None)
            raise

    def run_next_workflow(
        self,
        project_id: str | None = None,
        *,
        operator_flags: tuple[str, ...] = (),
    ) -> WorkflowRecord:
        self._ensure_ready()
        self._assert_slot_free()
        if project_id is not None:
            project_id = self._canonical_project_id(project_id)
        # A resident parent record re-derives children truth from the board
        # on every scan (FR-029, D2); manual completion and deletion count.
        resident = self._record
        if resident is not None and resident.state == _AWAITING_CHILDREN:
            evaluated, incomplete = self._evaluate_children(resident)
            self._set_record(evaluated)
            if not incomplete:
                return self.run_validator(evaluated)
        ready: list[BoardTask] = []
        unmapped: list[str] = []
        for task in self.task_board.list():
            if project_id is not None and task.project_id != project_id:
                continue
            if task.column and task.column not in {"todo", "ready"}:
                continue
            if task.priority not in _PRIORITIES or not self._dependencies_met(task):
                continue
            if not self._has_required_fields(task):
                continue
            if task.card_path == "feature" and self._board_children(
                task.id, task.project_id
            ):
                # An in-flight parent is never re-claimed as a fresh
                # workflow; its board observations are journaled instead.
                self._observe_board_children(task)
                continue
            try:
                self.registry.resolve_eligible_project(task.project_id)
            except UnknownProjectError:
                if task.project_id:
                    unmapped.append(task.project_id)
                continue
            except (DisabledProjectError, InvalidProjectLocationError):
                continue
            ready.append(task)
        if not ready:
            parent_task = self._parent_for_validation(project_id)
            if parent_task is not None:
                return self.run_validator(self._awaiting_record(parent_task))
            if unmapped:
                listed = ", ".join(sorted(dict.fromkeys(unmapped)))
                raise NoReadyTaskError(f"no ready task; unmapped project ids: {listed}")
            raise NoReadyTaskError("no ready task")
        priority = min(ready, key=lambda task: ("P0", "P1", "P2", "P3").index(task.priority))
        chosen = min(
            (task for task in ready if task.priority == priority.priority),
            key=lambda task: task.created_at,
        )
        return self.run_workflow(
            chosen.project_id,
            chosen.id,
            operator_flags=operator_flags,
        )

    def resume_workflow(self, project_id: str, task_id: str, option: str) -> WorkflowRecord:
        self._ensure_ready()
        project_id = self._canonical_project_id(project_id)
        record = self._record
        if record is None or record.legacy_migration_reason is not None:
            pass
        if (
            record is None
            or record.project_id != project_id
            or record.task_id != task_id
            or record.decision is None
            or record.state not in {"HUMAN_DECISION_REQUIRED", "BLOCKED"}
        ):
            raise ResumeNotParkedError("workflow is not parked for this task")
        letter = parse_option_letter(option) or ""
        choices = {choice.letter: choice for choice in record.decision.options}
        if letter not in choices:
            raise InvalidDecisionError("option must be a listed letter")
        choice = choices[letter]

        # A resolved gate is recorded durably and the parked card gets a
        # closing note so no stale open gate remains (FR-017, SC-006).
        self._close_gate(record, letter, choice.text)

        if record.children and record.state == "HUMAN_DECISION_REQUIRED":
            # The parent record re-derives children truth from the board
            # before resuming; a child deleted while parked is dropped.
            evaluated, incomplete = self._evaluate_children(record)
            record = evaluated

        if record.legacy_migration_reason is not None:
            # Superseded records park for a human; acknowledgement never
            # migrates them onto the 018 graph (FR-012).
            acknowledged = replace(
                record,
                state="HUMAN_DECISION_REQUIRED",
                next_action="human decides how to continue the superseded task",
                decision=DecisionBrief(
                    record.project_id,
                    record.task_id,
                    "human",
                    "superseded by 018 — whole-playbook run",
                    "The whole-playbook machine is retired. The retained "
                    "worktree stays as-is until a human chooses an action.",
                    (DecisionOption("A", "Review the retained worktree and choose a new action"),),
                ),
                chosen_option=letter,
                legacy_migration_reason=None,
                legacy_acknowledged=True,
            )
            self._set_record(acknowledged)
            return acknowledged

        phase = record.current_phase
        if record.state == "BLOCKED":
            if letter == "A":
                return self._fail(record.current_phase, record.current_worker or "", "abandoned")
            if record.state_attempts.get(record.current_phase, 0) >= _RECOVERY_BUDGET:
                return self._block(record.current_worker or "", None)
            return self._enter_state(record.current_phase)
        if phase == "clarify" and record.question_queue:
            return self._resume_clarify_answer(record, choice)
        if phase == "job" and record.question_queue:
            return self._resume_job_answer(record, choice)
        if phase == "job":
            return self._resume_job_publish(record, letter)
        if phase == "confirm":
            return self._resume_confirm(record, letter)
        if phase == "uat":
            return self._resume_uat(record, letter, choice)
        if phase == "pr-review":
            return self._resume_pr_review(record, letter, choice)
        # Generic human park (stuck, READY: blocked, missing artifacts):
        # the human decides; Hermes never auto-loops.
        if letter == "A":
            return self._fail(record.current_phase, record.current_worker or "", "abandoned")
        if record.state_attempts.get(record.current_phase, 0) >= _RECOVERY_BUDGET:
            return self._block(record.current_worker or "", None)
        return self._enter_state(record.current_phase)

    def _resume_clarify_answer(self, record: WorkflowRecord, choice: DecisionOption):
        context = record.resume_context or ResumeContext()
        context = replace(context, answers=context.answers + (choice.text,))
        queue = record.question_queue[1:]
        if queue:
            parked = replace(
                record,
                resume_context=context,
                question_queue=queue,
                chosen_option=choice.letter,
            )
            return self._park_clarify(parked)
        encoded = replace(
            record,
            state="QUEUED",
            resume_context=context,
            question_queue=(),
            chosen_option=choice.letter,
            next_action="encode clarification answers",
        )
        self._set_record(encoded)
        # The recorded answers are encoded by a NEW clarify Pi session.
        return self._enter_state("clarify")

    def _resume_job_answer(self, record: WorkflowRecord, choice: DecisionOption):
        context = record.resume_context or ResumeContext()
        context = replace(context, answers=context.answers + (choice.text,))
        queue = record.question_queue[1:]
        if queue:
            parked = replace(
                record,
                resume_context=context,
                question_queue=queue,
                chosen_option=choice.letter,
            )
            return self._park_job(parked)
        encoded = replace(
            record,
            state="QUEUED",
            resume_context=context,
            question_queue=(),
            chosen_option=choice.letter,
            next_action="encode job answers",
        )
        self._set_record(encoded)
        # The recorded answers are encoded by a NEW job Pi session.
        return self._enter_state("job")

    def _resume_confirm(self, record: WorkflowRecord, letter: str):
        # One human continuation before plan; `skip` never bypasses confirm.
        self._set_record(
            replace(
                record,
                state="QUEUED",
                current_phase="plan",
                decision=None,
                chosen_option=letter,
                resume_context=ResumeContext(continue_confirmed=True),
                next_action="start the plan step",
            )
        )
        return self._enter_state("plan")

    def _resume_uat(self, record: WorkflowRecord, letter: str, choice: DecisionOption):
        del choice
        if letter == "A":
            passed = replace(
                record,
                decision=None,
                chosen_option="A",
                steps=record.steps
                + (StepRecord("UAT_PASSED", "uat", None, "pass", (), "operator confirmed pass"),),
            )
            self._set_record(passed)
            if record.children:
                # The operator accepted the feature: the parent completes with
                # zero further gates (FR-028); publish stays operator-owned.
                return self._complete_feature(passed)
            return self._enter_state("pr-review")
        problem = replace(record, failure_class="NON_RETRYABLE", error="UAT found a problem")
        self._set_record(problem)
        return self._block(record.current_worker or "", None)

    def _resume_pr_review(self, record: WorkflowRecord, letter: str, choice: DecisionOption):
        verdict = _publish_verdicts(record.steps).get("pr-review")
        if letter == "A" and verdict == "PASS":
            publishing = replace(
                record,
                state="RUNNING",
                current_phase="publish",
                decision=None,
                chosen_option=letter,
                next_action="publish the feature branch",
            )
            self._set_record(publishing)
            return self._run_github()
        if letter == "A" and verdict != "PASS":
            return self._fail("pr-review", record.current_worker or "", "abandoned after FAIL")
        # Stop without publishing: the record stays parked, never auto-loops.
        self._set_record(
            replace(
                record,
                next_action="stopped without publishing",
                decision=DecisionBrief(
                    record.project_id,
                    record.task_id,
                    "human",
                    "The operator stopped the loop after pr-review.",
                    "No publish happened; the retained work remains on the feature branch.",
                    (DecisionOption("A", "Acknowledge and keep the worktree"),),
                ),
                chosen_option=letter,
            )
        )
        return self._require_record()

    def _assert_slot_free(self) -> None:
        if self._record is not None and self._record.state in _ACTIVE_STATES:
            raise WorkflowBusyError("another workflow is active")

    def _validate_runnable(self, task: BoardTask) -> None:
        if (
            task.column
            and task.column not in {"todo", "ready"}
            and not (task.column == "running" and task.id == self.allow_running_task_id)
        ):
            raise IneligibleColumnError(
                f"task {task.id} is not startable from column: {task.column}"
            )
        if task.priority not in _PRIORITIES:
            raise InvalidPriorityError(f"invalid priority: {task.priority}")
        if not self._has_required_fields(task):
            raise IncompleteTaskError(f"task is incomplete: {task.id}")
        if task.card_path not in _CARD_PATHS:
            raise InvalidCardPathError(f"invalid card path: {task.card_path}")
        if task.card_path == "job" and task.card_skill not in _JOB_SKILLS:
            raise InvalidJobSkillError(f"invalid job skill: {task.card_skill}")
        # The card `## Profile` is external input validated at the trust
        # boundary (FR-014); absent profiles take the Path default (FR-014a).
        profile_for_card(task, path_defaults=self.executor.settings.path_profile_defaults)
        if not self._dependencies_met(task):
            raise UnmetDependenciesError(f"unmet dependencies for task: {task.id}")

    @staticmethod
    def _has_required_fields(task: BoardTask) -> bool:
        return all(
            isinstance(value, str) and value.strip()
            for value in (
                task.id,
                task.project_id,
                task.problem,
                task.expected_result,
                task.acceptance_criteria,
                task.priority,
                task.created_at,
            )
        )

    def _dependencies_met(self, task: BoardTask) -> bool:
        try:
            return all(self.task_board.get(dependency).complete for dependency in task.dependencies)
        except UnknownTaskError:
            return False

    def _board_children(self, parent_id: str, project_id: str) -> tuple[BoardTask, ...]:
        """Child Task Cards of one parent, derived from a fresh board read.

        The board is authoritative (D2): children are never taken from a
        stored snapshot, so manual completion and deletion are visible.
        Project ids are compared through the canonical resolver so native
        ids match their operational enrollment.
        """
        return tuple(
            task
            for task in self.task_board.list()
            if task.id != parent_id
            and task.parent_id == parent_id
            and self._canonical_project_id(task.project_id) == project_id
        )

    def _journal(
        self,
        kind: str,
        project_id: str,
        parent_id: str,
        child_id: str | None,
        evidence: str,
    ) -> None:
        """Append one durable decision; fail-closed on a journal failure."""
        try:
            append_decision(
                self.overlay_dir,
                {
                    "ts": self.clock(),
                    "kind": kind,
                    "project_id": project_id,
                    "parent_id": parent_id,
                    "child_id": child_id or "",
                    "evidence": evidence,
                },
            )
        except PersistError as exc:
            raise OrchestratorError(f"decision journal write failed: {exc}") from exc

    def _journaled(
        self,
        kind: str,
        project_id: str,
        parent_id: str,
        child_id: str | None = None,
    ) -> bool:
        """Return whether an identical decision is already journaled."""
        try:
            entries = read_decisions(self.overlay_dir)
        except PersistError as exc:
            raise OrchestratorError(f"decision journal read failed: {exc}") from exc
        for entry in entries:
            if entry.get("kind") != kind:
                continue
            if entry.get("project_id") != project_id or entry.get("parent_id") != parent_id:
                continue
            if child_id is not None and entry.get("child_id") != child_id:
                continue
            return True
        return False

    def _evaluate_children(self, record: WorkflowRecord) -> tuple[WorkflowRecord, tuple[str, ...]]:
        """Re-derive child truth from the board and journal observations (FR-029).

        A child now `done`/`archived` counts toward the parent; a child absent
        from the board was deleted and is dropped from the requirement set.
        The orchestrator never restores a deleted or demotes a completed child.
        """
        children = self._board_children(record.task_id, record.project_id)
        current_ids = {child.id for child in children}
        for child_id in sorted(set(record.children) | current_ids):
            if child_id not in current_ids:
                if not self._journaled(
                    "child-deleted", record.project_id, record.task_id, child_id
                ):
                    self._journal(
                        "child-deleted",
                        record.project_id,
                        record.task_id,
                        child_id,
                        "absent from the board (manual deletion)",
                    )
                continue
            child = self.task_board.get(child_id)
            if child.complete and not self._journaled(
                "child-completed", record.project_id, record.task_id, child_id
            ):
                self._journal(
                    "child-completed",
                    record.project_id,
                    record.task_id,
                    child_id,
                    f"board column {child.column or '(board)'}",
                )
        incomplete = tuple(child.id for child in children if not child.complete)
        return replace(record, children=tuple(sorted(current_ids))), incomplete

    def evaluate_parent(self, parent_id: str) -> WorkflowRecord:
        """Re-read the board and re-evaluate one Feature Card's children."""
        self._ensure_ready()
        record = self._require_record()
        if record.task_id != parent_id or record.state != _AWAITING_CHILDREN:
            raise OrchestratorError(
                f"workflow is not awaiting children for task: {parent_id}"
            )
        evaluated, incomplete = self._evaluate_children(record)
        self._set_record(evaluated)
        if not incomplete:
            return self.run_validator(evaluated)
        return evaluated

    def decompose_children(self, record: WorkflowRecord) -> WorkflowRecord:
        """Create child Task Cards from the tasks artifact; park AWAITING_CHILDREN.

        Zero children is a durable surfaced failure: the parent stays open and
        never completes empty (spec edge case; FR-011).
        """
        artifact = _artifact_for_step("tasks", record.task_id)
        workspace = record.workspace_path
        if workspace is None or artifact is None or not (workspace / artifact).is_file():
            self._set_record(
                replace(record, error=f"missing native artifact: {artifact}")
            )
            return self._block("tasks", None)
        try:
            tasks_text = (workspace / artifact).read_text(encoding="utf-8")
        except (OSError, UnicodeError) as exc:
            raise OrchestratorError(f"cannot read tasks artifact: {artifact}") from exc
        native_id = self._native_card_project(record.project_id)
        args_list = child_card_args(
            tasks_text,
            parent_id=record.task_id,
            priority=record.task.priority,
            native_id=native_id,
        )
        if not args_list:
            self._set_record(
                replace(record, error="task generation produced no child cards")
            )
            return self._block("tasks", None)
        for args in args_list:
            # Fail-closed: a creation failure propagates and no record state
            # advances; the idempotency keys make a re-run safe.
            self.card_creator(args)
        children = self._board_children(record.task_id, record.project_id)
        if not children:
            self._set_record(
                replace(record, error="task generation produced no board children")
            )
            return self._block("tasks", None)
        parked = replace(
            record,
            state=_AWAITING_CHILDREN,
            current_phase="awaiting_children",
            next_action="await child task completion",
            decision=None,
            error=None,
            children=tuple(child.id for child in children),
        )
        self._set_record(parked)
        return parked

    def run_validator(self, record: WorkflowRecord) -> WorkflowRecord:
        """Run the automated validator (critic → tester) on the parent (FR-026)."""
        record = self._recover_for_validation(record)
        self._set_record(
            replace(
                record,
                state="QUEUED",
                current_phase="critic",
                current_worker=None,
                next_action="run the critic step",
                decision=None,
                error=None,
            )
        )
        return self._enter_state("critic")

    def _recover_for_validation(self, record: WorkflowRecord) -> WorkflowRecord:
        """Point the parent record at its existing worktree before validation.

        The parent worktree was prepared when the Feature Card was claimed and
        children ran in their own worktrees, so an inspection is enough; a
        missing worktree is a fail-closed block, never a silent skip.
        """
        if record.workspace_path is not None and record.workspace_branch:
            return record
        try:
            inspection = self.workspaces.inspect_workspace(
                record.project_id, record.task_id
            )
        except WorkspaceError as exc:
            self._set_record(replace(record, error=str(exc)))
            return self._block(record.current_phase, None)
        return replace(
            record,
            workspace_path=inspection.path,
            workspace_branch=inspection.branch,
            error=None,
        )

    def _native_card_project(self, project_id: str) -> str:
        """Return the native project id used for card-creation CLI calls."""
        try:
            record = self.registry.get_project(project_id)
        except Exception:
            return project_id
        if record.kanban_project_ids:
            return record.kanban_project_ids[0]
        return project_id

    def _observe_board_children(self, parent: BoardTask) -> None:
        """Journal manually completed children observed on the board (FR-029)."""
        for child in self._board_children(parent.id, parent.project_id):
            if child.complete and not self._journaled(
                "child-completed", parent.project_id, parent.id, child.id
            ):
                self._journal(
                    "child-completed",
                    parent.project_id,
                    parent.id,
                    child.id,
                    f"board column {child.column or '(board)'}",
                )

    def _parent_for_validation(self, project_id: str | None) -> BoardTask | None:
        """Find a Feature Card whose non-deleted children are all complete."""
        for task in self.task_board.list():
            if project_id is not None and task.project_id != project_id:
                continue
            if task.card_path != "feature" or task.complete:
                continue
            children = self._board_children(task.id, task.project_id)
            if not children or any(not child.complete for child in children):
                continue
            if self._journaled("parent-completed", task.project_id, task.id):
                continue
            return task
        return None

    def _awaiting_record(self, task: BoardTask) -> WorkflowRecord:
        """Build the minimal AWAITING_CHILDREN record for a Feature Card."""
        return WorkflowRecord(
            run_id=uuid.uuid4().hex,
            execution_id=uuid.uuid4().hex,
            state=_AWAITING_CHILDREN,
            workflow_name=self.executor.settings.workflow_name,
            current_phase="awaiting_children",
            project_id=task.project_id,
            task_id=task.id,
            task=task,
            next_action="await child task completion",
            children=tuple(child.id for child in self._board_children(task.id, task.project_id)),
        )

    def _queued(self, task: BoardTask, *, operator_flags: tuple[str, ...] = ()) -> WorkflowRecord:
        return WorkflowRecord(
            run_id=uuid.uuid4().hex,
            execution_id=uuid.uuid4().hex,
            state="QUEUED",
            workflow_name=self.executor.settings.workflow_name,
            current_phase="ready",
            project_id=task.project_id,
            task_id=task.id,
            task=task,
            next_action="start the ready step",
            steps=(StepRecord("QUEUED", "ready"),),
            operator_flags=operator_flags,
            card_path=task.card_path,
            parent_task_id=task.parent_id or None,
        )

    def _enter_state(self, step: str) -> WorkflowRecord:
        if step not in LOOP_STATES:
            return self._fail(step, "", f"unknown graph state: {step}")
        if step in HUMAN_STATES:
            if step == "confirm":
                return self._park_confirm()
            return self._park_uat()
        if step in PARENT_STATES:
            return self._run_github()
        return self._run_agent_step(step)

    def _run_agent_step(self, step: str) -> WorkflowRecord:
        record = self._require_record()
        attempts = record.state_attempts.get(step, 0) + 1
        worker = _worker_for_step(step) or step
        self._set_record(
            replace(
                record,
                state="RUNNING",
                current_phase=step,
                current_worker=worker,
                state_attempts={**record.state_attempts, step: attempts},
                next_action=f"run the {step} step",
                steps=record.steps
                + (
                    StepRecord(
                        f"{step.upper()}_STARTED",
                        step,
                        worker,
                    ),
                ),
            )
        )
        self._emit(
            "task_start",
            {"project": record.project_id, "task": record.task_id, "step": step},
            f"{record.run_id}:step:{step}:{attempts}",
        )
        try:
            result = self.executor.start_step(
                step,
                record.project_id,
                record.task_id,
                task=record.task,
                flow_id=record.run_id,
                operator_flags=record.operator_flags,
                resume_context=record.resume_context,
            )
        except Exception as exc:
            return self._fail(
                step, worker, f"step start failed: {type(exc).__name__}: {exc}"
            )
        current = self._require_record()
        self._set_record(
            replace(
                current,
                steps=current.steps
                + (
                    StepRecord(
                        step.upper(),
                        step,
                        worker,
                        result.status,
                        result.questions,
                        result.reason,
                    ),
                ),
            )
        )
        if result.status == "needs_human":
            return self._park_step_human(step, result)
        if result.status == "stuck":
            return self._retry_or_park(step, result.reason)
        if result.status != "completed":
            return self._retry_or_park(step, result.reason, retryable=result.retryable)
        report = result.report
        if report is None:
            return self._block(worker, None)
        return self._advance(step, report, result)

    def _advance(self, step: str, report: StepReport, result: HarnessResult) -> WorkflowRecord:
        """Advance one step's verified compact report to the next graph state."""
        record = self._require_record()
        fields = report.fields
        if step == "ready":
            if fields["READY"] == "blocked":
                # A stable READY: blocked parks and is never retried.
                return self._block("ready", result)
            if record.card_path == "change":
                return self._enter_state("change")
            if record.card_path == "job":
                return self._enter_state("job")
            return self._enter_state("specify")
        if step in {"change", "job"}:
            return self._after_short_path_step(step, report)
        status = fields.get("STATUS", "")
        if step in {"specify", "clarify", "plan", "tasks", "analyze"}:
            artifact = _artifact_for_step(step, record.task_id)
            if status == "ok" and artifact and not (record.workspace_path / artifact).is_file():
                # Missing spec/plan/tasks artifacts are never retried.
                self._set_record(
                    replace(record, error=f"missing native artifact: {artifact}")
                )
                return self._block(step, None)
            if status == "blocked":
                return self._block(step, None)
            if status != "ok":
                return self._retry_or_park(step, report.fields.get("SUMMARY", "step stuck"))
        if step == "specify":
            return self._enter_state("clarify")
        if step == "clarify":
            return self._after_clarify(report, result)
        if step == "plan":
            self._set_record(
                replace(record, analyze_requested=fields["ANALYZE"] == "yes")
            )
            return self._enter_state("tasks")
        if step == "tasks":
            if record.analyze_requested:
                return self._enter_state("analyze")
            # The tasks artifact is the decomposition boundary (FR-011, D4):
            # the task-generator role lands child Task Cards on the board.
            return self.decompose_children(record)
        if step == "analyze":
            return self.decompose_children(record)
        if step == "implement":
            return self._enter_state("converge")
        if step == "converge":
            return self._after_converge(report)
        if step in {"critic", "tester", "pr-review"}:
            return self._after_verdict_step(step, report, result)
        return self._fail(step, _worker_for_step(step), "unhandled step")

    def _after_clarify(self, report: StepReport, result: HarnessResult) -> WorkflowRecord:
        # A completed clarify session (self-answered under skip, or answers
        # encoded from the relay) either parks confirm when it still carries
        # unresolved questions, or advances straight to planning.
        record = self._require_record()
        if "skip" in record.operator_flags and record.resume_context is None:
            context = ResumeContext(assumptions=_SKIP_ASSUMPTIONS, prior_reason="skip")
            brief = DecisionBrief(
                record.project_id,
                record.task_id,
                "human",
                "Choice report recorded from skip assumptions.",
                "Confirm once before planning continues.",
                (DecisionOption("A", "Continue to planning"),),
            )
            parked = replace(
                record,
                state="HUMAN_DECISION_REQUIRED",
                current_phase="confirm",
                next_action="confirm continuation",
                decision=brief,
                resume_context=context,
                question_queue=(),
            )
            self._set_record(parked)
            self._emit(
                "choice_report",
                self._decision_payload(brief, assumptions=context.assumptions),
                f"{record.run_id}:choice_report",
            )
            self._emit("human_decision", self._decision_payload(brief), f"{record.run_id}:continue")
            self._post_gate_note(parked, brief)
            return parked
        self._set_record(replace(record, question_queue=()))
        # confirm raises only when the clarify report still carries
        # unresolved questions; absent a raise, planning continues (FR-028).
        if self._confirm_raised(result):
            return self._enter_state("confirm")
        return self._enter_state("plan")

    @staticmethod
    def _confirm_raised(result: HarnessResult) -> bool:
        """confirm parks only on unresolved clarify questions or skip."""
        report_questions = result.report.questions if result.report is not None else ()
        return bool(result.questions) or bool(report_questions)

    def _after_converge(self, report: StepReport) -> WorkflowRecord:
        record = self._require_record()
        outcome = report.fields["CONVERGE_OUTCOME"]
        fingerprint = report.fields["FINGERPRINT"]
        if outcome == "blocked":
            return self._block("converge", None)
        if outcome == "tasks_appended":
            if record.converge_fingerprint == fingerprint:
                # An unchanged fingerprint means the loop is stuck: park.
                return self._block("converge", None)
            self._set_record(replace(record, converge_fingerprint=fingerprint))
            # A new implement session; the converge session is never told
            # to implement (FR-004).
            return self._enter_state("implement")
        return self._enter_state("critic")

    def _after_short_path_step(self, step: str, report: StepReport) -> WorkflowRecord:
        """Advance one change/job worker report; SCOPE feature stops closed."""
        record = self._require_record()
        fields = report.fields
        if fields.get("SCOPE") == "feature":
            self._set_record(replace(record, error="scope is a feature"))
            return self._block(step, None)
        status = fields.get("STATUS", "")
        if status == "blocked":
            return self._block(step, None)
        if status != "ok":
            return self._retry_or_park(step, fields.get("SUMMARY", "step stuck"))
        if step == "change":
            return self._enter_state("tester")
        return self._park_job_publish()

    def _park_job_publish(self) -> WorkflowRecord:
        """Park a finished job for the operator's publish decision."""
        record = self._require_record()
        brief = DecisionBrief(
            record.project_id,
            record.task_id,
            "job",
            "Job worker finished. Hermes parks; the operator decides on publishing.",
            "Publishing happens only when the operator approves; the loop "
            "never auto-publishes a job branch.",
            (
                DecisionOption("A", "Publish the job branch as a pull request"),
                DecisionOption("B", "Complete without publishing"),
            ),
            "A",
        )
        parked = replace(
            record,
            state="HUMAN_DECISION_REQUIRED",
            current_phase="job",
            next_action="reply with the option letter",
            decision=brief,
        )
        self._set_record(parked)
        self._emit(
            "human_decision",
            self._decision_payload(brief),
            f"{record.run_id}:job_publish:{len(record.steps)}",
        )
        self._post_gate_note(parked, brief)
        return parked

    def _resume_job_publish(self, record: WorkflowRecord, letter: str):
        if letter == "A":
            publishing = replace(
                record,
                state="RUNNING",
                current_phase="publish",
                decision=None,
                chosen_option=letter,
                next_action="publish the job branch",
            )
            self._set_record(publishing)
            return self._run_github(job_path=True)
        return self._complete("job")

    def _complete(self, phase: str) -> WorkflowRecord:
        """Mark one completed card: board card done, then child hooks."""
        record = self._require_record()
        # The board owns lifecycle; the orchestrator completes the card
        # through the native CLI seam, fail-closed (FR-015).
        self.card_complete_fn(record.task_id)
        completed = replace(
            record,
            state="COMPLETED",
            current_phase=phase,
            next_action="",
            decision=None,
            error=None,
            steps=record.steps
            + (StepRecord("COMPLETED", phase, record.current_worker, "ok", (), ""),),
        )
        self._set_record(completed)
        return self._after_child_completion(completed)

    def _complete_feature(self, record: WorkflowRecord) -> WorkflowRecord:
        """Complete the parent Feature Card after the validator (FR-026/028).

        Zero additional operator actions: the card is marked done on the board
        and `parent-completed` is recorded in the decision journal.
        """
        if not self._journaled("parent-completed", record.project_id, record.task_id):
            self._journal(
                "parent-completed",
                record.project_id,
                record.task_id,
                None,
                "automated validator passed with no raised gate",
            )
        completed = replace(
            record,
            state="COMPLETED",
            current_phase="tester",
            next_action="",
            decision=None,
            error=None,
            steps=record.steps
            + (StepRecord("COMPLETED", "tester", record.current_worker, "ok", (), ""),),
        )
        self._set_record(completed)
        self.card_complete_fn(completed.task_id)
        return self._require_record()

    def _after_child_completion(self, record: WorkflowRecord) -> WorkflowRecord:
        """Journal one child completion and re-evaluate its parent (FR-029)."""
        parent_id = record.task.parent_id
        if not parent_id:
            return record
        if not self._journaled("child-completed", record.project_id, parent_id, record.task_id):
            self._journal(
                "child-completed",
                record.project_id,
                parent_id,
                record.task_id,
                f"board column {record.task.column or '(board)'}",
            )
        try:
            parent_task = self.task_board.get(parent_id)
        except UnknownTaskError:
            # A deleted parent keeps its child records terminal (board truth).
            return record
        children = self._board_children(parent_id, record.project_id)
        incomplete = tuple(
            child.id for child in children if not child.complete
        )
        if incomplete:
            # Parent stays open (AWAITING_CHILDREN); the remaining children
            # stay claimable through the next run_next_workflow scan.
            parent_record = WorkflowRecord(
                run_id=uuid.uuid4().hex,
                execution_id=uuid.uuid4().hex,
                state=_AWAITING_CHILDREN,
                workflow_name=self.executor.settings.workflow_name,
                current_phase="awaiting_children",
                project_id=parent_task.project_id,
                task_id=parent_id,
                task=parent_task,
                next_action="await child task completion",
                children=tuple(child.id for child in children),
            )
            self._set_record(parent_record)
            return record
        return self.run_validator(
            WorkflowRecord(
                run_id=uuid.uuid4().hex,
                execution_id=uuid.uuid4().hex,
                state=_AWAITING_CHILDREN,
                workflow_name=self.executor.settings.workflow_name,
                current_phase="awaiting_children",
                project_id=parent_task.project_id,
                task_id=parent_id,
                task=parent_task,
                next_action="run the automated validator",
                children=tuple(child.id for child in children),
            )
        )

    def _after_verdict_step(
        self, step: str, report: StepReport, result: HarnessResult
    ) -> WorkflowRecord:
        record = self._require_record()
        verdict = report.fields["VERDICT"]
        self._set_record(
            replace(
                record,
                steps=record.steps
                + (
                    StepRecord(
                        f"{step.upper()}_{verdict}",
                        step,
                        _worker_for_step(step),
                        verdict,
                        (),
                        report.fields["SUMMARY"],
                    ),
                ),
            )
        )
        record = self._require_record()
        if verdict == "PASS":
            if step == "tester":
                self._set_record(replace(record, validation_status="pass"))
                record = self._require_record()
                if record.card_path == "change":
                    return self._complete("tester")
                # Feature validation passed. uat raises only when the verdict
                # flags acceptance items or a blocked dependency (FR-028).
                if self._uat_raised(report):
                    return self._enter_state("uat")
                return self._complete_feature(record)
            if step == "critic":
                return self._enter_state("tester")
            return self._park_pr_review_complete(passed=True)
        if result.retryable:
            return self._retry_or_park(step, report.fields["SUMMARY"])
        return self._block(step, None)

    def _uat_raised(self, report: StepReport) -> bool:
        """uat parks only when the tester verdict flags acceptance items."""
        summary = report.fields.get("SUMMARY", "").casefold()
        return any(token in summary for token in ("acceptance", "unverified", "blocked"))

    def _park_step_human(self, step: str, result: HarnessResult) -> WorkflowRecord:
        record = self._require_record()
        context = result.resume_context or ResumeContext(prior_reason=result.reason)
        report_questions = result.report.questions if result.report is not None else ()
        questions = result.questions or report_questions
        queue = tuple(questions)
        options_text = queue or ("Resume the step.",)
        options = tuple(
            DecisionOption(chr(ord("A") + index), text)
            for index, text in enumerate(options_text)
        )
        brief = DecisionBrief(
            record.project_id,
            record.task_id,
            step,
            result.reason,
            "The step stopped and Hermes needs a human decision.",
            options,
        )
        parked = replace(
            record,
            state="HUMAN_DECISION_REQUIRED",
            current_phase=step,
            current_worker=record.current_worker,
            next_action=result.next_action or "reply with the option letter",
            decision=brief,
            resume_context=context,
            question_queue=queue,
        )
        self._set_record(parked)
        if step == "clarify":
            return self._park_clarify(replace(parked, question_queue=queue))
        if step == "job":
            return self._park_job(replace(parked, question_queue=queue))
        self._emit(
            "human_decision",
            self._decision_payload(brief),
            f"{record.run_id}:human:{step}:{len(record.steps)}",
        )
        self._post_gate_note(parked, brief)
        return parked

    def _park_job(self, record: WorkflowRecord) -> WorkflowRecord:
        queue = record.question_queue
        question = queue[0] if queue else "Review the job stop."
        brief = DecisionBrief(
            record.project_id,
            record.task_id,
            "job",
            question,
            "Answer the job question; Hermes relays it to the worker.",
            (DecisionOption("A", question),),
        )
        parked = replace(
            record,
            state="HUMAN_DECISION_REQUIRED",
            current_phase="job",
            next_action="reply with the answer",
            decision=brief,
        )
        self._set_record(parked)
        self._emit(
            "human_decision",
            self._decision_payload(brief),
            f"{record.run_id}:job:{len(record.steps)}",
        )
        self._post_gate_note(parked, brief)
        return parked

    def _park_clarify(self, record: WorkflowRecord) -> WorkflowRecord:
        queue = record.question_queue
        question = queue[0] if queue else "Review the clarify stop."
        brief = DecisionBrief(
            record.project_id,
            record.task_id,
            "clarify",
            question,
            "Answer the clarification question; Hermes relays it to the loop.",
            (DecisionOption("A", question),),
        )
        parked = replace(
            record,
            state="HUMAN_DECISION_REQUIRED",
            current_phase="clarify",
            next_action="reply with the answer",
            decision=brief,
        )
        self._set_record(parked)
        self._emit(
            "human_decision",
            self._decision_payload(brief),
            f"{record.run_id}:clarify:{len(record.steps)}",
        )
        self._post_gate_note(parked, brief)
        return parked

    def _park_confirm(self) -> WorkflowRecord:
        record = self._require_record()
        skipped = "skip" in record.operator_flags
        brief = DecisionBrief(
            record.project_id,
            record.task_id,
            "confirm",
            (
                "Clarify was self-answered under skip. Confirm once before plan."
                if skipped
                else "Confirm the clarification before plan starts."
            ),
            "One human continuation is required before the plan step.",
            (DecisionOption("A", "Continue to planning"),),
            "A",
        )
        parked = replace(
            record,
            state="HUMAN_DECISION_REQUIRED",
            current_phase="confirm",
            next_action="reply with the option letter",
            decision=brief,
        )
        self._set_record(parked)
        self._emit(
            "human_decision",
            self._decision_payload(brief),
            f"{record.run_id}:confirm",
        )
        self._post_gate_note(parked, brief)
        return parked

    def _park_uat(self) -> WorkflowRecord:
        record = self._require_record()
        checklist = record.uat_checklist or self._uat_checklist()
        brief = DecisionBrief(
            record.project_id,
            record.task_id,
            "uat",
            "UAT is human QA. Verify the implemented feature yourself.",
            "Hermes presents a feature-derived QA checklist; no agent runs UAT.",
            (
                DecisionOption("A", "Pass: continue to pr-review"),
                DecisionOption("B", "Problem found: stop for review"),
            ),
            "A",
        )
        payload = self._decision_payload(brief)
        payload["uat_checklist"] = checklist
        parked = replace(
            record,
            state="HUMAN_DECISION_REQUIRED",
            current_phase="uat",
            next_action="verify the checklist, then reply with the option letter",
            decision=brief,
            uat_checklist=checklist,
        )
        self._set_record(parked)
        self._emit("human_decision", payload, f"{record.run_id}:uat")
        self._post_gate_note(parked, brief)
        return parked

    def _uat_checklist(self) -> tuple[str, ...]:
        record = self._require_record()
        items: list[str] = []
        for criterion in record.task.acceptance_criteria.split("\n"):
            text = criterion.strip().lstrip("-* ")
            if text:
                items.append(f"Verify: {text}")
        converge = next(
            (step for step in reversed(record.steps) if step.phase == "converge"), None
        )
        if converge is not None and converge.summary:
            items.append(f"Exercise the converge test path: {converge.summary}")
        if not items:
            items.append("Exercise the implemented feature in the worktree.")
        return tuple(items)

    def _park_pr_review_complete(self, *, passed: bool) -> WorkflowRecord:
        record = self._require_record()
        if passed:
            brief = DecisionBrief(
                record.project_id,
                record.task_id,
                "pr-review",
                "pr-review PASS. Hermes parks; the operator decides on publishing.",
                "Publishing happens only when the operator approves; the loop "
                "never auto-loops after pr-review.",
                (
                    DecisionOption("A", "Publish the feature-branch pull request"),
                    DecisionOption("B", "Stop without publishing"),
                ),
                "A",
            )
        else:
            brief = DecisionBrief(
                record.project_id,
                record.task_id,
                "pr-review",
                "pr-review reported FAIL. Hermes parks; the operator decides.",
                "The loop does not auto-loop after pr-review.",
                (
                    DecisionOption("A", "Abandon this run"),
                    DecisionOption("B", "Retry the pr-review step"),
                ),
            )
        parked = replace(
            record,
            state="HUMAN_DECISION_REQUIRED",
            current_phase="pr-review",
            next_action="reply with the option letter",
            decision=brief,
        )
        self._set_record(parked)
        self._emit(
            "human_decision",
            self._decision_payload(brief),
            f"{record.run_id}:pr_review:{len(record.steps)}",
        )
        self._post_gate_note(parked, brief)
        return parked

    def _retry_or_park(
        self, step: str, reason: str, *, retryable: bool = True
    ) -> WorkflowRecord:
        record = self._require_record()
        if not retryable:
            self._set_record(replace(record, error=reason))
            return self._block(step, None)
        attempts = record.state_attempts.get(step, 0)
        if attempts >= _RECOVERY_BUDGET:
            return self._park_exhausted(step, reason)
        context = record.resume_context or ResumeContext()
        context = replace(
            context,
            diagnostic_summary=_diagnostic_text(
                DiagnosticReport(
                    record.task_id,
                    step,
                    attempts,
                    reason,
                    "one step session",
                    record.state,
                )
            ),
            prior_reason=reason,
        )
        self._set_record(
            replace(
                record,
                state="RETRYABLE_FAILURE",
                resume_context=context,
                next_action=f"retry the {step} step",
            )
        )
        return self._enter_state(step)

    def _park_exhausted(self, step: str, reason: str) -> WorkflowRecord:
        record = self._require_record()
        options_text = ("Review the stuck point and resume explicitly.",)
        options = tuple(
            DecisionOption(chr(ord("A") + index), text)
            for index, text in enumerate(options_text)
        )
        brief = DecisionBrief(
            record.project_id,
            record.task_id,
            step,
            reason,
            "The step exhausted its attempts and Hermes needs a human decision.",
            options,
        )
        parked = replace(
            record,
            state="HUMAN_DECISION_REQUIRED",
            current_phase=step,
            next_action="reply with the option letter",
            decision=brief,
        )
        self._set_record(parked)
        self._emit(
            "human_decision",
            self._decision_payload(brief),
            f"{record.run_id}:stuck:{step}:{record.state_attempts.get(step, 0)}",
        )
        self._post_gate_note(parked, brief)
        return parked

    def _run_github(self, *, reclaim: bool = False, job_path: bool = False) -> WorkflowRecord:
        from .external_framework import _path_like_id as _unused  # noqa: F401
        from .github import (
            ForbiddenGitHubActionError,
            PublishError,
            assert_publish_gate,
            build_pull_request,
        )
        from .workspace import _remote_identity

        while True:
            record = self._require_record()
            attempt = (
                record.publish_attempt
                if reclaim and record.publish_attempt
                else record.publish_attempt + 1
            )
            reclaim = False
            try:
                if job_path:
                    # The job publish gate is the recorded operator approval;
                    # the critic/tester/uat/pr-review chain does not apply.
                    if record.chosen_option != "A" or record.card_path != "job":
                        return self._block_publish(
                            "NON_RETRYABLE", "job publish requires operator approval"
                        )
                else:
                    assert_publish_gate(record.steps)
            except PublishError as exc:
                return self._block_publish("NON_RETRYABLE", str(exc))
            self._set_record(
                replace(
                    record,
                    state="RUNNING",
                    current_phase="publish",
                    publish_attempt=attempt,
                    next_action="publish",
                    decision=None,
                )
            )
            record = self._require_record()
            project = self.registry.resolve_eligible_project(record.project_id)
            copy = record.workspace_path
            branch = record.workspace_branch or ""
            if copy is None or not branch:
                return self._block_publish("NON_RETRYABLE", "missing workspace for publish")
            try:
                self.workspaces.assert_publish_allowed(
                    branch, default_branch=project.default_branch
                )
                _, remote_url = _remote_identity(copy)
                self.git_host.assert_remote_allowed(remote_url)
                self.git_host.ensure_commit(copy, branch, project.default_branch, record.task_id)
                self.git_host.push_feature_branch(copy, branch, remote_url)
                title, body = build_pull_request(
                    task_id=record.task_id,
                    title_source=record.task.problem,
                    summary=record.task.expected_result,
                    changes=f"Work on `{branch}`.",
                    validation=(
                        "job worker report approved by the operator"
                        if job_path
                        else self._last_validation_summary()
                        or "critic, tester, UAT, and pr-review passed"
                    ),
                    limitations="None recorded for this run.",
                    branch=branch,
                )
                identity = self.git_host.upsert_pull_request(
                    copy=copy,
                    head=branch,
                    base=project.default_branch,
                    title=title,
                    body=body,
                )
                if identity.number < 1 or not str(identity.html_url).strip():
                    raise PublishError(
                        "incomplete pull request identity", failure_class="NON_RETRYABLE"
                    )
                record = self._require_record()
                self._set_record(
                    replace(
                        record,
                        state="PR_CREATED",
                        current_phase="publish",
                        pull_request=identity,
                        next_action="",
                        error=None,
                        steps=record.steps
                        + (
                            StepRecord(
                                "PR_CREATED",
                                "publish",
                                None,
                                "success",
                                (),
                                f"PR {identity.number}",
                            ),
                        ),
                    )
                )
                self._emit(
                    "pr_created",
                    {
                        "project": record.project_id,
                        "task": record.task_id,
                        "number": identity.number,
                        "html_url": identity.html_url,
                    },
                    f"{record.run_id}:pr_created",
                )
                return self._record
            except (ForbiddenGitHubActionError, ProtectedBranchError) as exc:
                return self._block_publish("NON_RETRYABLE", str(exc))
            except PublishError as exc:
                class_ = classify_publish(exc)
                if class_ == "TRANSIENT" and attempt < _PUBLISH_BUDGET:
                    continue
                return self._block_publish(class_, str(exc))
            except (OSError, subprocess.CalledProcessError, subprocess.TimeoutExpired) as exc:
                class_ = classify_publish(exc)
                if class_ == "TRANSIENT" and attempt < _PUBLISH_BUDGET:
                    continue
                return self._block_publish(class_, str(exc))

    def _last_validation_summary(self) -> str:
        for step in reversed(self._require_record().steps):
            if step.phase == "tester" and step.summary:
                return step.summary
        return ""

    def _block_publish(self, class_: str, error: str) -> WorkflowRecord:
        record = self._require_record()
        self._set_record(
            replace(record, current_phase="publish", failure_class=class_, error=error)
        )
        return self._block(self._require_record().current_worker or "", None)

    def _block(self, worker: str, result: object | None) -> WorkflowRecord:
        record = self._require_record()
        class_ = record.failure_class or "NON_RETRYABLE"
        reason = (
            getattr(result, "summary", None)
            or getattr(result, "reason", "")
            or record.error
            or "recovery cannot continue"
        )
        brief = DecisionBrief(
            record.project_id,
            record.task_id,
            record.current_phase,
            reason,
            "Recovery cannot continue without a human choice.",
            (DecisionOption("A", "Abandon"), DecisionOption("B", "Retry once")),
            "A" if class_ == "NON_RETRYABLE" else "B",
        )
        parked = replace(
            record,
            state="BLOCKED",
            current_worker=worker or record.current_worker,
            next_action="reply with the option letter",
            decision=brief,
            steps=record.steps
            + (
                StepRecord(
                    "BLOCKED",
                    record.current_phase,
                    worker or record.current_worker,
                    getattr(result, "status", None) if result else None,
                    tuple(getattr(result, "questions", ()) or ()) if result else (),
                    getattr(result, "summary", "") or getattr(result, "reason", "")
                    or brief.decision,
                ),
            ),
        )
        self._set_record(parked)
        self._emit(
            "blocked",
            self._decision_payload(brief),
            f"{record.run_id}:blocked:{record.current_phase}:{record.attempt}",
        )
        self._post_gate_note(parked, brief)
        return parked

    def _fail(self, phase: str, worker: str, error: str) -> WorkflowRecord:
        record = self._require_record()
        failed = replace(
            record,
            state="FAILED",
            current_phase=phase if phase in LOOP_STATES else record.current_phase,
            current_worker=worker,
            next_action="",
            decision=None,
            error=error,
            steps=record.steps + (StepRecord("FAILED", phase, worker, "failed", (), error),),
        )
        self._set_record(failed)
        self._emit(
            "unexpected_failure",
            {"project": record.project_id, "task": record.task_id, "error": error},
            f"{record.run_id}:unexpected_failure",
        )
        return failed

    def _gate_note_text(
        self, brief: DecisionBrief, *, resolution: str | None = None
    ) -> str:
        """Render the flat board marker text from one decision brief (D5)."""
        if resolution is not None:
            return (
                f"HERMES GATE CLOSED — {brief.phase}\n"
                f"{resolution}\n"
                f"Card {brief.task_id} continues; no open gate remains."
            )
        options = "\n".join(
            f"  {option.letter}) {option.text}" for option in brief.options
        )
        return (
            f"HERMES GATE — {brief.phase}\n"
            f"Decision needed: {brief.decision}\n"
            f"Why it matters: {brief.why_it_matters}\n"
            f"Options:\n{options}\n"
            f"Recommended: {brief.recommended or '-'}\n"
            f"Resolve with: --resume {brief.project_id} {brief.task_id} <option letter>"
        )

    def _post_gate_note(self, record: WorkflowRecord, brief: DecisionBrief) -> None:
        """Post the visible gate marker on the parked card (FR-017).

        Fail-closed: a marker CLI failure surfaces and leaves the park state
        unchanged; the operator resolves (or retries) on the board.
        """
        self.card_note_fn(record.task_id, self._gate_note_text(brief))
        if not self._journaled("gate-raised", record.project_id, record.task_id):
            self._journal(
                "gate-raised",
                record.project_id,
                record.task_id,
                None,
                f"gate {brief.phase}: {brief.decision}",
            )

    def _close_gate(self, record: WorkflowRecord, letter: str, choice_text: str) -> None:
        """Record the gate resolution and post the closing note (SC-006)."""
        self._journal(
            "gate-resolved",
            record.project_id,
            record.task_id,
            None,
            f"operator chose {letter}: {choice_text}",
        )
        self.card_note_fn(
            record.task_id,
            self._gate_note_text(
                DecisionBrief(
                    record.project_id,
                    record.task_id,
                    record.current_phase,
                    choice_text,
                    "The operator resolved the gate on the board.",
                    (),
                ),
                resolution=f"operator chose {letter}: {choice_text}",
            ),
        )

    def _decision_payload(
        self,
        brief: DecisionBrief,
        *,
        assumptions: tuple[str, ...] = (),
    ) -> dict[str, object]:
        payload: dict[str, object] = {
            "project": brief.project_id,
            "task": brief.task_id,
            "phase": brief.phase,
            "decision": brief.decision,
            "why_it_matters": brief.why_it_matters,
            "options": tuple(
                {"letter": option.letter, "text": option.text, "consequence": option.consequence}
                for option in brief.options
            ),
            "recommended": brief.recommended,
            "reply_with": brief.reply_with,
        }
        if assumptions:
            payload["assumptions"] = assumptions
        return payload

    def _emit(self, kind: str, payload: dict[str, object], occurrence: str) -> SendRecord | None:
        if self.messaging is None:
            return None
        record = self._require_record()
        existing = next((send for send in record.sends if send.occurrence == occurrence), None)
        if existing is not None and (
            existing.status in {SendStatus.SENT, SendStatus.SKIPPED}
            or (existing.status == SendStatus.FAILED and existing.attempts >= 3)
        ):
            return existing
        try:
            sent = self.messaging.deliver(kind, payload, occurrence=occurrence)
        except Exception as exc:
            sent = SendRecord(occurrence, kind, SendStatus.FAILED, 1, str(exc))
        self._set_record(replace(record, sends=record.sends + (sent,)))
        return sent

    def _require_record(self) -> WorkflowRecord:
        assert self._record is not None
        return self._record
