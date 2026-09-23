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
            current_phase="ready",
            project_id=task.project_id,
            task_id=task.id,
            task=task,
            next_action="start the ready step",
            steps=(StepRecord("QUEUED", "ready"),),
            operator_flags=operator_flags,
            card_path=task.card_path,
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
            return self._enter_state("implement")
        if step == "analyze":
            return self._enter_state("implement")
        if step == "implement":
            return self._enter_state("converge")
        if step == "converge":
            return self._after_converge(report)
        if step in {"critic", "tester", "pr-review"}:
            return self._after_verdict_step(step, report, result)
        return self._fail(step, _worker_for_step(step), "unhandled step")

    def _after_clarify(self, report: StepReport, result: HarnessResult) -> WorkflowRecord:
        # A completed clarify session (self-answered under skip, or answers
        # encoded from the relay) advances to the confirm human gate.
        del result
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
            return parked
        self._set_record(replace(record, question_queue=()))
        return self._enter_state("confirm")

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
        """Mark one short path COMPLETED with no publish."""
        record = self._require_record()
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
        return self._require_record()

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
                if record.card_path == "change":
                    return self._complete("tester")
                return self._enter_state("uat")
            if step == "critic":
                return self._enter_state("tester")
            return self._park_pr_review_complete(passed=True)
        if result.retryable:
            return self._retry_or_park(step, report.fields["SUMMARY"])
        return self._block(step, None)

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
