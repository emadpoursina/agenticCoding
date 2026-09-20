"""Atomic persistence and liveness for the single V0 execution slot."""

from __future__ import annotations

import json
import os
import re
import time
from collections.abc import Callable
from dataclasses import dataclass, fields, is_dataclass
from enum import Enum
from pathlib import Path
from typing import TYPE_CHECKING, Literal

if TYPE_CHECKING:
    from .orchestrator import WorkflowRecord

OverlaySlot = Literal["occupied", "free"]
OverlaySchema = Literal["v0"]
Clock = Callable[[], float]

_ALIVE_TTL = 60.0
_PHASE_ALIASES = {
    "publish": "github",
    "diagnose": "diagnosis",
    "re-check": "validation",
}
_SECRET_NAME = re.compile(r"(?:KEY|TOKEN|SECRET|PASSWORD|CREDENTIAL)", re.IGNORECASE)


class PersistError(Exception):
    """Base error for overlay persistence failures."""


class InvalidOverlayDirError(PersistError):
    """Raised when the configured overlay directory cannot be used."""


class OverlayReadError(PersistError):
    """Raised when the sole overlay snapshot is corrupt or incomplete."""


class SlotHeldError(PersistError):
    """Raised when another live control-plane copy holds the slot."""


# ponytail: one JSON document is sufficient for the single V0 slot; upgrade
# identities onto native Kanban columns when a later phase needs that mapping.
@dataclass(frozen=True)
class OverlaySnapshot:
    """Last complete operational record and its derived slot state."""

    record: WorkflowRecord | None
    slot: OverlaySlot
    schema: OverlaySchema = "v0"


def validate_overlay_dir(directory: Path) -> Path:
    """Validate the required existing writable overlay directory."""
    if not isinstance(directory, Path) or not directory.is_dir():
        raise InvalidOverlayDirError(f"invalid overlay directory: {directory}")
    if not os.access(directory, os.R_OK | os.W_OK | os.X_OK):
        raise InvalidOverlayDirError(f"overlay directory is not writable: {directory}")
    try:
        with os.scandir(directory):
            pass
    except OSError as exc:
        raise InvalidOverlayDirError(f"overlay directory is not writable: {directory}") from exc
    return directory


def load_overlay_dir(config_path: Path) -> Path:
    """Load and validate execution.overlay_dir from operational YAML."""
    from .projects import _parse_document, _SubsetYamlError

    try:
        text = config_path.read_text(encoding="utf-8")
        document = _parse_document(text)
    except (OSError, UnicodeError, _SubsetYamlError) as exc:
        raise InvalidOverlayDirError(f"cannot read config: {config_path}") from exc
    execution = document.get("execution")
    raw_directory = execution.get("overlay_dir") if isinstance(execution, dict) else None
    if not isinstance(raw_directory, str) or not raw_directory.strip():
        raise InvalidOverlayDirError("execution.overlay_dir is missing or empty")
    return validate_overlay_dir(Path(raw_directory.strip()))


def write_overlay(directory: Path, snapshot: OverlaySnapshot) -> None:
    """Atomically replace the last complete overlay snapshot."""
    validate_overlay_dir(directory)
    if not isinstance(snapshot, OverlaySnapshot):
        raise TypeError("snapshot must be OverlaySnapshot")
    if snapshot.schema != "v0" or snapshot.slot not in {"occupied", "free"}:
        raise OverlayReadError("unsupported overlay snapshot")
    payload = _jsonable(snapshot)
    temporary = directory / "overlay.json.tmp"
    target = directory / "overlay.json"
    try:
        with temporary.open("w", encoding="utf-8") as stream:
            json.dump(payload, stream, sort_keys=True, separators=(",", ":"))
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, target)
    except OSError as exc:
        raise PersistError(f"cannot write overlay: {target}") from exc


def read_overlay(directory: Path) -> OverlaySnapshot | None:
    """Read only the complete overlay file and never use its temporary sibling."""
    validate_overlay_dir(directory)
    target = directory / "overlay.json"
    if not target.exists():
        return None
    try:
        payload = json.loads(target.read_text(encoding="utf-8"))
        if not isinstance(payload, dict):
            raise ValueError("snapshot must be an object")
        if payload.get("schema") != "v0":
            raise ValueError("unsupported overlay schema")
        slot = payload.get("slot")
        if slot not in {"occupied", "free"}:
            raise ValueError("invalid overlay slot")
        raw_record = payload.get("record")
        record = None if raw_record is None else _record_from_dict(raw_record)
        _validate_saved_harness_record(record)
        return OverlaySnapshot(record=record, slot=slot, schema="v0")
    except (OSError, UnicodeError, json.JSONDecodeError, TypeError, ValueError) as exc:
        raise OverlayReadError(f"cannot read complete overlay: {target}") from exc


def touch_alive(directory: Path, *, clock: Clock = time.time) -> None:
    """Atomically refresh the control-plane alive signal."""
    validate_overlay_dir(directory)
    temporary = directory / "alive.tmp"
    target = directory / "alive"
    payload = {"written_at": float(clock()), "fresh_for": _ALIVE_TTL}
    try:
        with temporary.open("w", encoding="utf-8") as stream:
            json.dump(payload, stream, sort_keys=True, separators=(",", ":"))
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, target)
    except OSError as exc:
        raise PersistError(f"cannot write alive signal: {target}") from exc


def alive_is_fresh(directory: Path, *, clock: Clock = time.time, ttl_s: float = _ALIVE_TTL) -> bool:
    """Return whether the alive signal is newer than the supplied TTL."""
    validate_overlay_dir(directory)
    target = directory / "alive"
    if not target.exists():
        return False
    try:
        payload = json.loads(target.read_text(encoding="utf-8"))
        written_at = float(payload["written_at"])
        return float(clock()) - written_at < float(ttl_s)
    except (OSError, UnicodeError, KeyError, TypeError, ValueError, json.JSONDecodeError):
        return False


def _canonical_phase(value: str) -> str:
    return _PHASE_ALIASES.get(value, value)


def _redact(value: str) -> str:
    """Remove runtime secret values before an operational string is stored."""
    result = value
    for name, secret in os.environ.items():
        if (name == "SSH_AUTH_SOCK" or _SECRET_NAME.search(name)) and len(secret) >= 4:
            result = result.replace(secret, "[redacted]")
    if "BEGIN OPENSSH PRIVATE KEY" in result:
        return "[redacted private key]"
    return result


def _jsonable(value: object, *, field_name: str | None = None) -> object:
    if isinstance(value, str):
        if field_name in {"phase", "current_phase"}:
            return _canonical_phase(value)
        return _redact(value)
    if value is None or isinstance(value, (bool, int, float)):
        return value
    if isinstance(value, Path):
        return str(value)
    if isinstance(value, Enum):
        return value.value
    if is_dataclass(value) and not isinstance(value, type):
        return {
            item.name: _jsonable(getattr(value, item.name), field_name=item.name)
            for item in fields(value)
        }
    if isinstance(value, dict):
        return {
            _redact(str(key)): _jsonable(item, field_name=str(key)) for key, item in value.items()
        }
    if isinstance(value, (list, tuple)):
        return [_jsonable(item) for item in value]
    return _redact(str(value))


def _record_from_dict(raw: object) -> WorkflowRecord:
    """Rebuild the public workflow dataclasses from one validated JSON object."""
    from .external_framework import harness_result_from_dict
    from .github import PullRequestIdentity
    from .messaging import SendRecord, SendStatus
    from .orchestrator import (
        BoardTask,
        DecisionBrief,
        DecisionOption,
        DiagnosticReport,
        StepRecord,
        WorkflowRecord,
    )

    if not isinstance(raw, dict):
        raise ValueError("record must be an object")
    task_raw = raw["task"]
    if not isinstance(task_raw, dict):
        raise ValueError("record task must be an object")
    task_fields = {
        "id",
        "project_id",
        "problem",
        "expected_result",
        "acceptance_criteria",
        "priority",
        "created_at",
        "platform",
        "technical_notes",
        "dependencies",
        "owner",
        "reviewer",
        "complete",
        "column",
    }
    task_values = {name: task_raw[name] for name in task_fields if name in task_raw}
    task_values["dependencies"] = tuple(task_values.get("dependencies", ()))
    task = BoardTask(**task_values)

    options: tuple[DecisionOption, ...] = ()
    decision_raw = raw.get("decision")
    if decision_raw is not None:
        if not isinstance(decision_raw, dict):
            raise ValueError("decision must be an object")
        options = tuple(
            DecisionOption(
                str(option["letter"]),
                str(option["text"]),
                option.get("consequence"),
            )
            for option in decision_raw.get("options", ())
        )
        decision = DecisionBrief(
            str(decision_raw["project_id"]),
            str(decision_raw["task_id"]),
            _canonical_phase(str(decision_raw["phase"])),
            str(decision_raw["decision"]),
            str(decision_raw["why_it_matters"]),
            options,
            decision_raw.get("recommended"),
            str(decision_raw.get("reply_with", "option letter")),
        )
    else:
        decision = None

    steps = tuple(
        StepRecord(
            str(step["state"]),
            _canonical_phase(str(step.get("phase", ""))),
            step.get("worker"),
            step.get("execute_status"),
            tuple(step.get("questions", ())),
            str(step.get("summary", "")),
        )
        for step in raw.get("steps", ())
    )
    diagnostic_raw = raw.get("diagnostic")
    diagnostic = None
    if diagnostic_raw is not None:
        if not isinstance(diagnostic_raw, dict):
            raise ValueError("diagnostic must be an object")
        diagnostic = DiagnosticReport(
            str(diagnostic_raw["task_id"]),
            _canonical_phase(str(diagnostic_raw["phase"])),
            int(diagnostic_raw["attempt"]),
            str(diagnostic_raw["failure"]),
            str(diagnostic_raw["what_was_attempted"]),
            str(diagnostic_raw["current_state"]),
            str(diagnostic_raw.get("decision_required", "")),
        )

    pull_request_raw = raw.get("pull_request")
    pull_request = None
    if pull_request_raw is not None:
        if not isinstance(pull_request_raw, dict):
            raise ValueError("pull_request must be an object")
        pull_request = PullRequestIdentity(
            int(pull_request_raw["number"]), str(pull_request_raw["html_url"])
        )

    sends = tuple(
        SendRecord(
            str(send["occurrence"]),
            str(send["kind"]),
            SendStatus(str(send["status"])),
            int(send["attempts"]),
            send.get("error"),
        )
        for send in raw.get("sends", ())
    )
    legacy_acknowledged = raw.get("legacy_acknowledged", False)
    if not isinstance(legacy_acknowledged, bool):
        raise ValueError("legacy_acknowledged must be boolean")
    return WorkflowRecord(
        run_id=str(raw["run_id"]),
        execution_id=str(raw.get("execution_id", raw["run_id"])),
        state=str(raw["state"]),
        workflow_name=str(raw["workflow_name"]),
        current_phase=_canonical_phase(str(raw["current_phase"])),
        project_id=str(raw["project_id"]),
        task_id=str(raw["task_id"]),
        task=task,
        next_action=str(raw.get("next_action", "")),
        current_worker=raw.get("current_worker"),
        attempt=int(raw.get("attempt", 1)),
        harness_attempt=int(raw.get("harness_attempt", raw.get("attempt", 1))),
        workspace_path=(
            Path(raw["workspace_path"]) if raw.get("workspace_path") is not None else None
        ),
        workspace_branch=raw.get("workspace_branch"),
        workspace_id=raw.get("workspace_id"),
        validation_status=str(raw.get("validation_status", "pending")),
        blockers=tuple(raw.get("blockers", ())),
        pull_request=pull_request,
        publish_attempt=int(raw.get("publish_attempt", 0)),
        decision=decision,
        chosen_option=raw.get("chosen_option"),
        steps=steps,
        error=raw.get("error"),
        failure_class=raw.get("failure_class"),
        diagnostic=diagnostic,
        sends=sends,
        harness_result=harness_result_from_dict(raw.get("harness_result")),
        resume_context=_resume_context_from_dict(raw.get("resume_context")),
        operator_flags=tuple(raw.get("operator_flags", ())),
        legacy_migration_reason=raw.get("legacy_migration_reason"),
        legacy_acknowledged=legacy_acknowledged,
    )


def _resume_context_from_dict(raw: object):
    from .external_framework import ResumeContext

    if raw is None:
        return None
    if not isinstance(raw, dict):
        raise ValueError("resume_context must be an object")
    return ResumeContext(
        tuple(raw.get("answers", ())),
        tuple(raw.get("assumptions", ())),
        bool(raw.get("continue_confirmed", False)),
        str(raw.get("diagnostic_summary", "")),
        str(raw.get("prior_reason", "")),
        raw.get("resume_reference"),
    )


def _validate_saved_harness_record(record: WorkflowRecord | None) -> None:
    """Reject unsafe normalized harness data while reading the overlay."""
    if record is None:
        return
    from .external_framework import (
        RESULT_STATUSES,
        HarnessValidationError,
        contains_secret,
        validate_harness_result,
        validate_resume_context,
    )

    try:
        validate_resume_context(record.resume_context)
    except HarnessValidationError as exc:
        raise ValueError(f"invalid saved resume context: {exc}") from exc
    if record.harness_result is None:
        return
    result = record.harness_result
    if result.status not in RESULT_STATUSES:
        raise ValueError("saved harness status is unknown")
    if contains_secret(result.reason) or contains_secret(result.next_action):
        raise ValueError("saved harness metadata is unsafe")
    if result.harness_id and contains_secret(result.harness_id):
        raise ValueError("saved harness identity is unsafe")
    if any(contains_secret(question) for question in result.questions):
        raise ValueError("saved harness question is unsafe")
    if result.artifacts and record.workspace_path is None:
        raise ValueError("saved harness artifacts require a workspace")
    try:
        if record.workspace_path is not None:
            validate_harness_result(
                result,
                workspace_path=record.workspace_path,
                adapter_id=result.harness_id or None,
            )
    except HarnessValidationError as exc:
        raise ValueError(f"invalid saved harness result: {exc}") from exc
