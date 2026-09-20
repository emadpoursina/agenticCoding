"""Hermes orchestration over one generic harness run."""

from __future__ import annotations

import subprocess
import threading
import time
import uuid
from collections.abc import Callable, Sequence
from dataclasses import dataclass, replace
from pathlib import Path
from typing import TYPE_CHECKING, Protocol

from .executor import (
    AgentExecutor,
    ExecutePayload,
    ExecuteResult,
    MissingWorkspaceError,
    ModelService,
)
from .external_framework import (
    HarnessAdapter,
    HarnessResult,
    ResumeContext,
)
from .messaging import MessagingChannel, SendRecord, SendStatus, parse_option_letter
from .persist import (
    InvalidOverlayDirError,
    OverlaySnapshot,
    SlotHeldError,
    alive_is_fresh,
    load_overlay_dir,
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
    "VALIDATING",
    "HUMAN_DECISION_REQUIRED",
    "RETRYABLE_FAILURE",
    "BLOCKED",
}
_TERMINAL_STATES = {"COMPLETED", "FAILED", "PR_CREATED"}
_ORCHESTRATION_PHASES = {"execution", "human", "validation", "github"}
_RECOVERY_BUDGET = 3
_PUBLISH_BUDGET = 3
_SKIP_ASSUMPTIONS = (
    "Use the task description and acceptance criteria as the specification.",
    "Resolve routine wording from the existing project context.",
)


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
    harness_attempt: int = 1
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
    harness_result: HarnessResult | None = None
    resume_context: ResumeContext | None = None
    operator_flags: tuple[str, ...] = ()
    legacy_migration_reason: str | None = None
    legacy_acknowledged: bool = False


class TaskBoard(Protocol):
    def get(self, task_id: str) -> BoardTask: ...

    def list(self) -> tuple[BoardTask, ...]: ...


class MemoryTaskBoard:
    """Fixture-only read-only task-board seam."""

    def __init__(self, tasks: Sequence[BoardTask]) -> None:
        self._tasks = tuple(tasks)
        self._by_id = {task.id: task for task in self._tasks}

    def get(self, task_id: str) -> BoardTask:
        try:
            return self._by_id[task_id]
        except KeyError as exc:
            raise UnknownTaskError(f"unknown task: {task_id}") from exc

    def list(self) -> tuple[BoardTask, ...]:
        return self._tasks


def classify_validation(result: ExecuteResult) -> str:
    if result.questions:
        return "HUMAN_DECISION_REQUIRED"
    if result.validation == "blocked" and result.status == "failure":
        return "NON_RETRYABLE"
    if result.validation == "fail":
        return "RETRYABLE"
    if result.validation == "blocked" and result.status == "blocked":
        return "TRANSIENT" if result.next_action == "retry" else "NON_RETRYABLE"
    return "NON_RETRYABLE"


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


class PivOrchestrator:
    """Select, run, validate, and publish one task through a harness."""

    def __init__(
        self,
        executor: AgentExecutor,
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
    ) -> None:
        from .github import LiveGitHost

        if task_board is None:
            raise MissingTaskBoardError("task board is required")
        if overlay_dir is None:
            raise InvalidOverlayDirError("execution.overlay_dir is required")
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
        )
        orchestrator.become_ready()
        return orchestrator

    def become_ready(self) -> WorkflowRecord | None:
        """Load the durable slot and park removed legacy records."""
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
        old_phases = {"discovery", "planning", "tasks", "implementation", "diagnosis", "debug"}
        return (
            record.state == "PLANNING_COMPLETE"
            or record.current_phase in old_phases
            or any(
                step.phase in old_phases or step.state == "PLANNING_COMPLETE"
                for step in record.steps
            )
        )

    def _park_legacy(self, record: WorkflowRecord) -> WorkflowRecord:
        reason = (
            "Historical Hermes Spec Kit stage work was parked for human review; "
            "the removed stage machine will not resume and Pi will not auto-start."
        )
        brief = DecisionBrief(
            record.project_id,
            record.task_id,
            "human",
            reason,
            "A person must decide how to continue this historical task.",
            (DecisionOption("A", "Review the retained worktree and choose a new action"),),
        )
        return replace(
            record,
            state="HUMAN_DECISION_REQUIRED",
            current_phase="human",
            next_action="review the historical task",
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
        if current.current_phase == "validation":
            return self._run_validation()
        if current.current_phase == "github":
            return self._run_github(reclaim=True)
        if current.current_phase == "execution":
            return self._retry_harness("reclaimed interrupted harness run")
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
        self.registry.load_project_context(project_id)
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
            return self._run_harness()
        except Exception:
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
        if (
            record is not None
            and record.project_id == project_id
            and record.task_id == task_id
            and record.legacy_acknowledged
            and record.legacy_migration_reason is None
            and record.state == "QUEUED"
        ):
            return record
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
        if record.legacy_migration_reason:
            acknowledged = replace(
                record,
                state="QUEUED",
                current_phase="execution",
                next_action="await restart before starting the harness",
                decision=None,
                chosen_option=letter,
                legacy_migration_reason=None,
                legacy_acknowledged=True,
            )
            self._set_record(acknowledged)
            return acknowledged
        if record.state == "BLOCKED":
            if letter == "A":
                return self._fail(record.current_phase, record.current_worker or "", "abandoned")
            return self._retry_harness("human-approved recovery")
        if record.current_phase == "validation":
            self._set_record(
                replace(
                    record,
                    state="QUEUED",
                    decision=None,
                    chosen_option=letter,
                    next_action="validate",
                )
            )
            return self._run_validation()

        context = record.resume_context or ResumeContext(
            prior_reason=record.harness_result.reason if record.harness_result else ""
        )
        is_confirmation = choice.text.lower().startswith("continue the ")
        if is_confirmation:
            context = replace(context, continue_confirmed=True)
        elif not context.continue_confirmed:
            answers = context.answers + (choice.text,)
            if "skip" in record.operator_flags and not context.assumptions:
                context = replace(
                    context,
                    assumptions=_SKIP_ASSUMPTIONS,
                    answers=answers,
                )
            else:
                context = replace(context, answers=answers)
            brief = DecisionBrief(
                record.project_id,
                record.task_id,
                "human",
                (
                    "Choice report recorded from skip assumptions."
                    if context.assumptions
                    else "Clarification recorded."
                ),
                "Confirm once before the harness continues to planning.",
                (DecisionOption("A", "Continue the Spec Kit playbook"),),
            )
            parked = replace(
                record,
                state="HUMAN_DECISION_REQUIRED",
                current_phase="human",
                decision=brief,
                resume_context=context,
                next_action="confirm continuation",
                chosen_option=letter,
            )
            self._set_record(parked)
            if context.assumptions:
                self._emit(
                    "choice_report",
                    self._decision_payload(brief, assumptions=context.assumptions),
                    f"{record.run_id}:choice_report",
                )
            self._emit("human_decision", self._decision_payload(brief), f"{record.run_id}:continue")
            return parked
        else:
            context = replace(context, answers=context.answers + (choice.text,))
        self._set_record(
            replace(
                record,
                state="QUEUED",
                current_phase="execution",
                decision=None,
                resume_context=context,
                chosen_option=letter,
                attempt=record.attempt + 1,
                harness_attempt=record.harness_attempt + 1,
                next_action="start harness",
            )
        )
        return self._run_harness()

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

    def _queued(self, task: BoardTask, *, operator_flags: tuple[str, ...] = ()) -> WorkflowRecord:
        return WorkflowRecord(
            run_id=uuid.uuid4().hex,
            execution_id=uuid.uuid4().hex,
            state="QUEUED",
            workflow_name=self.executor.settings.workflow_name,
            current_phase="execution",
            project_id=task.project_id,
            task_id=task.id,
            task=task,
            next_action="start harness",
            steps=(StepRecord("QUEUED", "execution"),),
            operator_flags=operator_flags,
        )

    def _run_harness(self) -> WorkflowRecord:
        record = self._require_record()
        worker = self.harness_adapter.identity if self.harness_adapter is not None else ""
        self._set_record(
            replace(
                record,
                state="RUNNING",
                current_phase="execution",
                current_worker=worker,
                next_action="run harness",
                steps=record.steps + (StepRecord("EXECUTION_STARTED", "execution", worker),),
            )
        )
        self._emit(
            "task_start",
            {"project": record.project_id, "task": record.task_id},
            f"{record.run_id}:task_start",
        )
        try:
            result = self.executor.start_harness(
                self.harness_adapter,
                record.project_id,
                record.task_id,
                task=record.task,
                operator_flags=record.operator_flags,
                resume_context=record.resume_context,
            )
        except Exception as exc:
            return self._fail(
                "execution", worker, f"harness start failed: {type(exc).__name__}: {exc}"
            )
        self._set_record(
            replace(
                self._require_record(),
                harness_result=result,
                steps=self._require_record().steps
                + (
                    StepRecord(
                        "EXECUTION_FINISHED",
                        "execution",
                        worker,
                        result.status,
                        result.questions,
                        result.reason,
                    ),
                ),
            )
        )
        if result.status == "needs_human":
            return self._park_harness(result)
        if result.status == "stuck":
            if result.retryable and record.attempt < _RECOVERY_BUDGET:
                return self._retry_harness(result.reason)
            return self._park_harness(result, stuck=True)
        if result.status != "completed":
            return self._fail("execution", worker, result.reason)
        return self._run_validation()

    def _park_harness(self, result: HarnessResult, *, stuck: bool = False) -> WorkflowRecord:
        record = self._require_record()
        context = result.resume_context or ResumeContext(prior_reason=result.reason)
        if (
            result.status == "needs_human"
            and "skip" in record.operator_flags
            and record.resume_context is None
            and not context.continue_confirmed
        ):
            context = replace(
                context,
                answers=context.answers + _SKIP_ASSUMPTIONS,
                assumptions=_SKIP_ASSUMPTIONS,
                prior_reason=result.reason,
            )
            brief = DecisionBrief(
                record.project_id,
                record.task_id,
                "human",
                "Choice report recorded from skip assumptions.",
                "Confirm once before the harness continues to planning.",
                (DecisionOption("A", "Continue the Spec Kit playbook"),),
            )
            parked = replace(
                record,
                state="HUMAN_DECISION_REQUIRED",
                current_phase="human",
                next_action="confirm continuation",
                decision=brief,
                resume_context=context,
            )
            self._set_record(parked)
            self._emit(
                "choice_report",
                self._decision_payload(brief, assumptions=context.assumptions),
                f"{record.run_id}:choice_report",
            )
            self._emit("human_decision", self._decision_payload(brief), f"{record.run_id}:continue")
            return parked
        options_text = result.questions or (
            ("Review the stuck point and resume explicitly." if stuck else "Resume the harness."),
        )
        options = tuple(
            DecisionOption(chr(ord("A") + index), text) for index, text in enumerate(options_text)
        )
        brief = DecisionBrief(
            record.project_id,
            record.task_id,
            "human",
            result.reason,
            "The harness stopped and Hermes needs a human decision.",
            options,
        )
        parked = replace(
            record,
            state="HUMAN_DECISION_REQUIRED",
            current_phase="human",
            current_worker=record.current_worker,
            next_action=result.next_action or "reply with the option letter",
            decision=brief,
            resume_context=context,
            steps=record.steps
            + (
                StepRecord(
                    "HUMAN_DECISION_REQUIRED",
                    "human",
                    record.current_worker,
                    result.status,
                    result.questions,
                    result.reason,
                ),
            ),
        )
        self._set_record(parked)
        self._emit(
            "human_decision",
            self._decision_payload(brief),
            f"{record.run_id}:human:{len(record.steps)}",
        )
        return parked

    def _retry_harness(self, reason: str) -> WorkflowRecord:
        record = self._require_record()
        if record.attempt >= _RECOVERY_BUDGET:
            return self._park_harness(
                HarnessResult(
                    status="stuck",
                    reason=reason,
                    next_action="review the repeated harness failure",
                    retryable=False,
                    harness_id=record.current_worker or "pi",
                ),
                stuck=True,
            )
        context = record.resume_context or ResumeContext()
        context = replace(
            context,
            diagnostic_summary=_diagnostic_text(
                DiagnosticReport(
                    record.task_id,
                    record.current_phase,
                    record.attempt,
                    reason,
                    "whole harness run",
                    record.state,
                )
            ),
            prior_reason=reason,
        )
        updated = replace(
            record,
            state="RETRYABLE_FAILURE",
            current_phase="execution",
            attempt=record.attempt + 1,
            harness_attempt=record.harness_attempt + 1,
            resume_context=context,
            decision=None,
            next_action="retry harness",
            steps=record.steps
            + (
                StepRecord(
                    "RETRYABLE_FAILURE", "execution", record.current_worker, "retry", (), reason
                ),
            ),
        )
        self._set_record(updated)
        return self._run_harness()

    def _run_validation(self) -> WorkflowRecord:
        record = self._require_record()
        worker = self.executor.settings.role_agents["validation"]
        self._set_record(
            replace(
                record,
                state="VALIDATING",
                current_phase="validation",
                current_worker=worker,
                next_action="validate",
                decision=None,
                steps=record.steps + (StepRecord("VALIDATING", "validation", worker),),
            )
        )
        result = self._execute_role("validation")
        if result is None:
            return self._fail("validation", worker, "missing workspace")
        return self._after_validation(result, worker)

    def _execute_role(self, role: str) -> ExecuteResult | None:
        record = self._require_record()
        payload = ExecutePayload(
            title=record.task.problem,
            description=record.task.expected_result,
            acceptance_criteria=record.task.acceptance_criteria,
            priority=record.task.priority,
            validation=_diagnostic_text(record.diagnostic) if record.diagnostic else None,
        )
        try:
            return self.executor.execute_role(
                role,
                record.project_id,
                record.task_id,
                payload=payload,
            )
        except MissingWorkspaceError:
            return None

    def _after_validation(self, result: ExecuteResult, worker: str) -> WorkflowRecord:
        if result.questions:
            return self._park_validation(result, worker)
        self._set_record(
            replace(
                self._require_record(),
                validation_status=result.validation or "failed",
                steps=self._require_record().steps
                + (
                    StepRecord(
                        "VALIDATED",
                        "validation",
                        worker,
                        result.status,
                        result.questions,
                        result.summary,
                    ),
                ),
            )
        )
        if result.validation == "pass":
            return self._begin_github(worker, result)
        class_ = classify_validation(result)
        if class_ == "RETRYABLE" and self._require_record().attempt < _RECOVERY_BUDGET:
            current = self._require_record()
            report = DiagnosticReport(
                current.task_id,
                "validation",
                current.attempt,
                result.summary,
                "project validation",
                "VALIDATING",
            )
            self._set_record(replace(current, diagnostic=report, failure_class=class_))
            return self._retry_harness(result.summary)
        return self._block(worker, result)

    def _park_validation(self, result: ExecuteResult, worker: str) -> WorkflowRecord:
        record = self._require_record()
        brief = DecisionBrief(
            record.project_id,
            record.task_id,
            "validation",
            result.summary,
            "Validation needs a human choice before it can continue.",
            tuple(
                DecisionOption(chr(ord("A") + i), question)
                for i, question in enumerate(result.questions)
            ),
        )
        parked = replace(
            record,
            state="HUMAN_DECISION_REQUIRED",
            current_phase="validation",
            current_worker=worker,
            decision=brief,
            next_action="reply with the option letter",
        )
        self._set_record(parked)
        self._emit("human_decision", self._decision_payload(brief), f"{record.run_id}:validation")
        return parked

    def _begin_github(self, worker: str, result: ExecuteResult) -> WorkflowRecord:
        record = self._require_record()
        self._set_record(
            replace(
                record,
                state="RUNNING",
                current_phase="github",
                current_worker=worker,
                validation_status="pass",
                next_action="publish",
                decision=None,
                steps=record.steps
                + (
                    StepRecord(
                        "COMPLETED",
                        "validation",
                        worker,
                        result.status,
                        result.questions,
                        result.summary,
                    ),
                ),
            )
        )
        return self._run_github()

    def _guard_github(self, action: str) -> None:
        self.git_host.forbidden(action)

    def _run_github(self, *, reclaim: bool = False) -> WorkflowRecord:
        from .github import ForbiddenGitHubActionError, PublishError, build_pull_request
        from .workspace import _remote_identity

        while True:
            record = self._require_record()
            attempt = (
                record.publish_attempt
                if reclaim and record.publish_attempt
                else record.publish_attempt + 1
            )
            reclaim = False
            self._set_record(
                replace(
                    record,
                    state="RUNNING",
                    current_phase="github",
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
                    validation=self._last_validation_summary() or "project checks passed",
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
                        current_phase="github",
                        pull_request=identity,
                        next_action="",
                        error=None,
                        steps=record.steps
                        + (
                            StepRecord(
                                "PR_CREATED", "github", None, "success", (), f"PR {identity.number}"
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
            if step.phase == "validation" and step.summary:
                return step.summary
        return ""

    def _block_publish(self, class_: str, error: str) -> WorkflowRecord:
        record = self._require_record()
        self._set_record(replace(record, current_phase="github", failure_class=class_, error=error))
        return self._block(self._require_record().current_worker or "", None)

    def _block(self, worker: str, result: ExecuteResult | None) -> WorkflowRecord:
        record = self._require_record()
        class_ = record.failure_class or "NON_RETRYABLE"
        brief = DecisionBrief(
            record.project_id,
            record.task_id,
            record.current_phase,
            result.summary if result else (record.error or "recovery cannot continue"),
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
                    result.status if result else None,
                    result.questions if result else (),
                    result.summary if result else brief.decision,
                ),
            ),
        )
        self._set_record(parked)
        self._emit(
            "blocked",
            self._decision_payload(brief),
            f"{record.run_id}:blocked:{record.current_phase}:{record.attempt}",
        )
        return parked

    def _fail(self, phase: str, worker: str, error: str) -> WorkflowRecord:
        record = self._require_record()
        failed = replace(
            record,
            state="FAILED",
            current_phase=phase if phase in _ORCHESTRATION_PHASES else "execution",
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
