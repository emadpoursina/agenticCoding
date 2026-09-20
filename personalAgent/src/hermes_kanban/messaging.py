"""Messaging seam for meaningful PIV events and home-chat commands."""

from __future__ import annotations

import re
from collections.abc import Mapping
from dataclasses import dataclass
from enum import StrEnum
from typing import TYPE_CHECKING, Protocol

if TYPE_CHECKING:
    from .orchestrator import PivOrchestrator

EVENT_KINDS = frozenset(
    {
        "task_start",
        "human_decision",
        "choice_report",
        "major_recovery",
        "validation_recovery_failure",
        "blocked",
        "pr_created",
        "unexpected_failure",
    }
)


class SendStatus(StrEnum):
    SENT = "SENT"
    SKIPPED = "SKIPPED"
    FAILED = "FAILED"


@dataclass(frozen=True)
class SendRecord:
    occurrence: str
    kind: str
    status: SendStatus
    attempts: int
    error: str | None = None


@dataclass(frozen=True)
class InboundResult:
    handled: bool
    kind: str


class MessagingChannel(Protocol):
    def deliver(
        self, kind: str, payload: Mapping[str, object], *, occurrence: str
    ) -> SendRecord: ...

    def reply(self, text: str) -> None: ...


def parse_option_letter(text: str) -> str | None:
    if not isinstance(text, str):
        return None
    match = re.fullmatch(r"\s*([A-Za-z])\s*([.)])?\s*", text)
    return match.group(1).upper() if match else None


def format_event(kind: str, payload: Mapping[str, object]) -> str:
    project = str(payload.get("project", ""))
    task = str(payload.get("task", ""))
    if kind == "task_start":
        return f"Task started\nProject: {project}\nTask: {task}"
    if kind == "human_decision":
        return _format_decision(payload, "Human decision required")
    if kind == "choice_report":
        return _format_decision(payload, "Choice report")
    if kind == "blocked":
        return _format_decision(payload, "Blocked")
    if kind == "major_recovery":
        return (
            f"Major recovery started\nProject: {project}\nTask: {task}\n"
            f"Attempt: {payload.get('attempt', '')}"
        )
    if kind == "validation_recovery_failure":
        return (
            f"Recovery validation failed\nProject: {project}\nTask: {task}\n"
            f"Attempt: {payload.get('attempt', '')}\n{payload.get('summary', '')}"
        )
    if kind == "pr_created":
        return (
            f"Pull request created\nProject: {project}\nTask: {task}\n"
            f"PR: #{payload.get('number', '')}\n{payload.get('html_url', '')}"
        )
    if kind == "unexpected_failure":
        return (
            f"Unexpected failure\nProject: {project}\nTask: {task}\n"
            f"{payload.get('error', '')}"
        )
    raise ValueError(f"unknown messaging event: {kind}")


def _format_decision(payload: Mapping[str, object], heading: str) -> str:
    lines = [
        heading,
        f"Project: {payload.get('project', '')}",
        f"Task: {payload.get('task', '')}",
        f"Current phase: {payload.get('phase', '')}",
        f"Decision required: {payload.get('decision', '')}",
        f"Why it matters: {payload.get('why_it_matters', '')}",
        "Options:",
    ]
    options = payload.get("options", ())
    for option in options if isinstance(options, tuple | list) else ():
        if isinstance(option, Mapping):
            consequence = option.get("consequence") or "not stated"
            lines.append(f"{option.get('letter', '')}: {option.get('text', '')}")
            lines.append(f"   Consequence: {consequence}")
    recommended = payload.get("recommended") or "not stated"
    lines.extend(
        [
            f"Recommended option: {recommended}",
            f"How to reply: {payload.get('reply_with', 'option letter')}",
        ]
    )
    return "\n".join(lines)


class MemoryMessagingChannel:
    """In-process channel for contract checks; never opens a Telegram session."""

    def __init__(
        self,
        *,
        enabled: bool = True,
        fail_times: int = 0,
        fail_all: bool = False,
    ) -> None:
        self.enabled = enabled
        self.fail_times = max(0, fail_times)
        self.fail_all = fail_all
        self.deliveries: list[tuple[str, dict[str, object], str]] = []
        self.records: list[SendRecord] = []
        self.replies: list[str] = []
        self._by_occurrence: dict[str, SendRecord] = {}

    def deliver(
        self, kind: str, payload: Mapping[str, object], *, occurrence: str
    ) -> SendRecord:
        if kind not in EVENT_KINDS:
            raise ValueError(f"unknown messaging event: {kind}")
        prior = self._by_occurrence.get(occurrence)
        if prior is not None and prior.status in {
            SendStatus.SENT,
            SendStatus.SKIPPED,
        }:
            return prior
        if not self.enabled:
            record = SendRecord(occurrence, kind, SendStatus.SKIPPED, 0)
            self._remember(record)
            return record
        attempts = prior.attempts if prior else 0
        error: str | None = None
        for _ in range(3 - attempts):
            attempts += 1
            if self.fail_all or self.fail_times:
                if self.fail_times:
                    self.fail_times -= 1
                error = "memory messaging failure"
                continue
            record = SendRecord(occurrence, kind, SendStatus.SENT, attempts)
            self.deliveries.append((kind, dict(payload), occurrence))
            self._remember(record)
            return record
        record = SendRecord(occurrence, kind, SendStatus.FAILED, attempts, error)
        self._remember(record)
        return record

    def reply(self, text: str) -> None:
        self.replies.append(text)

    def _remember(self, record: SendRecord) -> None:
        self._by_occurrence[record.occurrence] = record
        self.records.append(record)


class HermesTelegramChannel:
    """Retrying wrapper around Hermes' already-connected Telegram adapter."""

    def __init__(self, adapter: object, home_chat_id: str) -> None:
        self.home_chat_id = str(home_chat_id).strip()
        self._records: dict[str, SendRecord] = {}
        self.notifier = None
        if not self.home_chat_id:
            return
        try:
            from hermes_cli.telegram_notifier import TelegramNotifier
        except ImportError as exc:
            raise RuntimeError("Hermes Telegram notifier is unavailable") from exc
        self.notifier = TelegramNotifier.from_gateway_adapter(
            adapter, chat_id=self.home_chat_id
        )

    def deliver(
        self, kind: str, payload: Mapping[str, object], *, occurrence: str
    ) -> SendRecord:
        if kind not in EVENT_KINDS:
            raise ValueError(f"unknown messaging event: {kind}")
        if self.notifier is None:
            record = SendRecord(occurrence, kind, SendStatus.SKIPPED, 0)
            self._records[occurrence] = record
            return record
        prior = self._records.get(occurrence)
        if prior is not None and prior.status in {SendStatus.SENT, SendStatus.SKIPPED}:
            return prior
        attempts = prior.attempts if prior else 0
        error: str | None = None
        for _ in range(3 - attempts):
            attempts += 1
            try:
                self.notifier.send(format_event(kind, payload))
                record = SendRecord(occurrence, kind, SendStatus.SENT, attempts)
                self._records[occurrence] = record
                return record
            except Exception as exc:
                error = str(exc)
        record = SendRecord(occurrence, kind, SendStatus.FAILED, attempts, error)
        self._records[occurrence] = record
        return record

    def reply(self, text: str) -> None:
        if self.notifier is not None:
            self.notifier.send(text)


def _active_record(orchestrator: PivOrchestrator, project_id: str | None = None):
    record = orchestrator._record
    if record is None or (project_id is not None and record.project_id != project_id):
        return None
    return record


def format_status(orchestrator: PivOrchestrator, project_id: str | None = None) -> str:
    record = _active_record(orchestrator, project_id)
    if record is not None and record.state in {
        "QUEUED",
        "RUNNING",
        "VALIDATING",
        "HUMAN_DECISION_REQUIRED",
        "RETRYABLE_FAILURE",
        "BLOCKED",
    }:
        return (
            f"Project: {record.project_id}\nTask: {record.task_id}\n"
            f"Phase: {record.current_phase}\nState: {record.state}\n"
            f"Next: {record.next_action or 'none'}"
        )
    scope = f" for {project_id}" if project_id else ""
    if record is not None and (project_id is None or record.project_id == project_id):
        return (
            f"Nothing running{scope}.\n"
            f"Last finished: {record.state} {record.project_id}/{record.task_id}"
        )
    return f"Nothing running{scope}."


def format_projects(orchestrator: PivOrchestrator) -> str:
    projects = orchestrator.registry.list_projects()
    if not projects:
        return "Enrolled projects: (none)"
    return "Enrolled projects:\n" + "\n".join(
        f"- {item.id}: {item.name} ({'enabled' if item.enabled else 'disabled'})"
        for item in projects
    )


def format_tasks(orchestrator: PivOrchestrator) -> str:
    tasks = orchestrator.task_board.list()
    if not tasks:
        return "Tasks: (none)"
    record = orchestrator._record
    lines = []
    for task in tasks:
        state = record.state if record and record.task_id == task.id else (
            "complete" if task.complete else "queued"
        )
        lines.append(f"- {task.project_id}/{task.id}: {state}")
    return "Tasks:\n" + "\n".join(lines)


def format_blockers(orchestrator: PivOrchestrator) -> str:
    record = orchestrator._record
    if record is None or record.state not in {"HUMAN_DECISION_REQUIRED", "BLOCKED"}:
        return "Nothing blocked or waiting."
    return (
        f"Waiting: {record.project_id}/{record.task_id}\n"
        f"State: {record.state}\n"
        f"Decision: {record.decision.decision if record.decision else record.next_action}"
    )


def format_prs(orchestrator: PivOrchestrator) -> str:
    record = orchestrator._record
    if record is None or record.pull_request is None:
        return "No pull requests waiting for review."
    return (
        f"Pull request waiting for review: #{record.pull_request.number}\n"
        f"{record.pull_request.html_url}"
    )


def handle_inbound(
    orchestrator: PivOrchestrator,
    chat_id: str,
    text: str,
    channel: MessagingChannel,
    *,
    home_chat_id: str,
) -> InboundResult:
    if str(chat_id) != str(home_chat_id) or not str(home_chat_id).strip():
        return InboundResult(False, "ignored")
    command = text.strip() if isinstance(text, str) else ""
    commands = {
        "/projects": lambda: format_projects(orchestrator),
        "/tasks": lambda: format_tasks(orchestrator),
        "/blockers": lambda: format_blockers(orchestrator),
        "/prs": lambda: format_prs(orchestrator),
    }
    if command in commands:
        channel.reply(commands[command]())
        return InboundResult(True, "status")
    if command == "/status" or command.startswith("/status "):
        project_id = command[8:].strip() or None
        if project_id is not None:
            try:
                orchestrator.registry.get_project(project_id)
            except Exception:
                channel.reply(f"Unknown project: {project_id}")
                return InboundResult(True, "error")
        channel.reply(format_status(orchestrator, project_id))
        return InboundResult(True, "status")

    record = orchestrator._record
    if record is None or record.state not in {"HUMAN_DECISION_REQUIRED", "BLOCKED"}:
        if parse_option_letter(command):
            channel.reply("Nothing is waiting for a decision.")
            return InboundResult(True, "nothing_waiting")
        return InboundResult(False, "ignored")
    letter = parse_option_letter(command)
    choices = {option.letter for option in record.decision.options} if record.decision else set()
    if letter is None or letter not in choices:
        listed = ", ".join(sorted(choices)) or "none"
        channel.reply(f"Reply with one listed option: {listed}.")
        return InboundResult(True, "correction")
    try:
        orchestrator.resume_workflow(record.project_id, record.task_id, letter)
    except Exception as exc:
        channel.reply(str(exc))
        return InboundResult(True, "error")
    return InboundResult(True, "resume")
