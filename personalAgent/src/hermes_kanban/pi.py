"""Pi execution adapter.

Pi SDK objects and model settings stop at this module.  Hermes sees only the
generic request/result records from :mod:`external_framework`.

One request is one agent-kind graph state; each start is one fresh Pi
process run that is prompted for that step only.
"""

from __future__ import annotations

import json
import os
import selectors
import subprocess
import time
from dataclasses import dataclass
from pathlib import Path
from threading import Event, Thread
from typing import Protocol

from .external_framework import (
    PLAYBOOK_ID,
    HarnessArtifact,
    HarnessResult,
    HarnessRuntime,
    HarnessValidationError,
    ResumeContext,
    StepStartRequest,
    _safe_relative_path,
    contains_secret,
    validate_harness_result,
    validate_step_request,
)


@dataclass(frozen=True)
class PiRunRequest:
    """Private request shape understood by the injected Pi runtime."""

    step_id: str
    flow_id: str
    skill_path: str
    task_id: str
    task_title: str
    task_description: str
    acceptance_criteria: str
    workspace_path: Path
    workspace_branch: str
    model_profile: object
    timeout_seconds: float
    deadline: float
    operator_flags: tuple[str, ...]
    resume_context: ResumeContext | None
    inputs: dict[str, object] | None = None


@dataclass(frozen=True)
class PiRunResponse:
    """Private, normalized stand-in for a Pi SDK response."""

    status: str
    reason: str
    next_action: str = ""
    artifacts: tuple[HarnessArtifact, ...] = ()
    changes: tuple[str, ...] = ()
    output_reference: str | None = None
    retryable: bool = False
    questions: tuple[str, ...] = ()
    resume_context: ResumeContext | None = None
    report: dict[str, object] | None = None


class PiSdkPort(Protocol):
    """Minimal injected runtime port; no SDK dependency is imported."""

    def run(self, request: PiRunRequest) -> PiRunResponse | dict[str, object]: ...


class UnavailablePiRuntime:
    """Production-safe placeholder when the external Pi runtime is not loaded."""

    def run(self, request: PiRunRequest) -> PiRunResponse:
        del request
        return PiRunResponse(
            status="failed",
            reason="Pi runtime is unavailable",
            next_action="install or inject the configured Pi runtime",
        )


class _PiTransportError(Exception):
    """Raised when the private Pi process cannot complete one RPC exchange."""


def _resume_payload(context: ResumeContext | None) -> dict[str, object] | None:
    if context is None:
        return None
    return {
        "answers": list(context.answers),
        "assumptions": list(context.assumptions),
        "continue_confirmed": context.continue_confirmed,
        "diagnostic_summary": context.diagnostic_summary,
        "prior_reason": context.prior_reason,
        "resume_reference": context.resume_reference,
    }


# Fixed, unchanged safety constraints carried on every step run (write root
# is the task worktree, feature branch only, never publish/push/merge).
_SAFETY_CONSTRAINTS = {
    "write_root": ".",
    "feature_branch_only": True,
    "allow_publish": False,
    "allow_protected_branch": False,
    "allow_external_writes": False,
    "reject_secrets": True,
}


def _prompt_message(request: StepStartRequest) -> str:
    """Wrap one step job in the prompt understood by Pi RPC.

    The prompt names only this step and its skill path. It must never
    instruct Pi to run a later graph state (FR-004).
    """
    job = json.dumps(_job_payload(request), separators=(",", ":"))
    return (
        f"Execute exactly one Hermes step: {request.step_id}. Use only the "
        f"skill at {request.skill_path} in the current worktree. Do not run "
        "any other step and do not continue to a next step. Do not publish, "
        "push, merge, deploy, or write outside the worktree. When the step "
        "is finished, reply with exactly one JSON object and no markdown "
        "using this schema: "
        '{"status":"completed|failed|needs_human|stuck","reason":"...",'
        '"next_action":"...","artifacts":[],"changes":[],"output_reference":null,'
        '"retryable":false,"questions":[],"resume_context":null,"report":{}}. '
        "The status must be one of the four values shown. The step document is:\n"
        + job
    )


def _rpc_prompt(request: StepStartRequest) -> dict[str, object]:
    return {
        "id": f"hermes-{request.flow_id}-{request.step_id}",
        "type": "prompt",
        "message": _prompt_message(request),
    }


def _job_payload(request: StepStartRequest) -> dict[str, object]:
    """Build the bounded provider-neutral document sent to Pi."""
    return {
        "step_id": request.step_id,
        "flow_id": request.flow_id,
        "skill": request.skill_path,
        "task_id": str(request.inputs.get("task_id", "")),
        "worktree": {
            "root": ".",
            "branch": request.workspace_branch,
        },
        "constraints": dict(_SAFETY_CONSTRAINTS),
        "model_profile": request.model_profile,
        "operator_flags": list(request.operator_flags),
        "resume_context": _resume_payload(request.resume_context),
        "inputs": {
            key: list(value) if isinstance(value, (list, tuple)) else value
            for key, value in request.inputs.items()
        },
    }


def _failed(reason: str, *, next_action: str = "inspect the harness failure") -> HarnessResult:
    return HarnessResult(
        status="failed",
        reason=reason,
        next_action=next_action,
        retryable=False,
        harness_id="pi",
    )


def _usable_path(relative: str, workspace: Path, *, require_file: bool) -> str | None:
    """Return an advisory path only when it validates against the worktree."""
    try:
        return _safe_relative_path(relative, workspace, "advisory path", require_file=require_file)
    except HarnessValidationError:
        return None


def _sanitize_advisory_paths(
    response: PiRunResponse, workspace: Path
) -> tuple[tuple[HarnessArtifact, ...], tuple[str, ...], str | None]:
    """Drop drifted advisory paths instead of rejecting a finished run.

    ponytail: models drift from the documented result schema; status, reason,
    and questions stay strict while advisory paths are sanitized. Upgrade is a
    pinned step report schema enforced inside the Pi runtime.
    """
    artifacts = tuple(
        HarnessArtifact(artifact.kind, kept)
        for artifact in response.artifacts
        if (kept := _usable_path(artifact.relative_path, workspace, require_file=True)) is not None
    )
    changes = tuple(
        kept
        for change in response.changes
        if (kept := _usable_path(change, workspace, require_file=False)) is not None
    )
    output = response.output_reference
    if output is not None:
        output = _usable_path(output, workspace, require_file=True)
    return artifacts, changes, output


def _coerce_artifacts(raw: object) -> tuple[HarnessArtifact, ...]:
    if raw is None:
        return ()
    if isinstance(raw, dict):
        if not all(isinstance(kind, str) and isinstance(path, str) for kind, path in raw.items()):
            raise HarnessValidationError("Pi artifacts are malformed")
        return tuple(HarnessArtifact(kind, path) for kind, path in raw.items())
    if not isinstance(raw, (tuple, list)):
        raise HarnessValidationError("Pi artifacts are malformed")
    result: list[HarnessArtifact] = []
    for item in raw:
        if isinstance(item, HarnessArtifact):
            result.append(item)
        elif isinstance(item, str):
            # ponytail: models emit bare paths despite the documented object
            # schema; kind is descriptive and paths stay validated downstream.
            if not item.strip():
                raise HarnessValidationError("Pi artifact is malformed")
            result.append(HarnessArtifact("file", item))
        elif isinstance(item, dict):
            kind = item.get("kind", "file")
            path = item.get("relative_path")
            if not isinstance(kind, str) or not isinstance(path, str) or not path.strip():
                raise HarnessValidationError("Pi artifact is malformed")
            result.append(HarnessArtifact(kind, path))
        else:
            raise HarnessValidationError("Pi artifact is malformed")
    return tuple(result)


def _coerce_resume_context(raw: object) -> ResumeContext | None:
    if raw is None or isinstance(raw, ResumeContext):
        return raw
    if not isinstance(raw, dict):
        raise HarnessValidationError("Pi resume context is malformed")
    answers = raw.get("answers", ())
    assumptions = raw.get("assumptions", ())
    if (
        not isinstance(answers, (list, tuple))
        or not isinstance(assumptions, (list, tuple))
        or not all(isinstance(item, str) for item in (*answers, *assumptions))
    ):
        raise HarnessValidationError("Pi resume context is malformed")
    continue_confirmed = raw.get("continue_confirmed", False)
    if not isinstance(continue_confirmed, bool):
        raise HarnessValidationError("Pi resume context is malformed")
    values = {
        "diagnostic_summary": raw.get("diagnostic_summary", ""),
        "prior_reason": raw.get("prior_reason", ""),
        "resume_reference": raw.get("resume_reference"),
    }
    if (
        not isinstance(values["diagnostic_summary"], str)
        or not isinstance(values["prior_reason"], str)
        or (
            values["resume_reference"] is not None
            and not isinstance(values["resume_reference"], str)
        )
    ):
        raise HarnessValidationError("Pi resume context is malformed")
    return ResumeContext(
        tuple(answers),
        tuple(assumptions),
        continue_confirmed,
        values["diagnostic_summary"],
        values["prior_reason"],
        values["resume_reference"],
    )


def _coerce_report(raw: object) -> dict[str, object] | None:
    if raw is None:
        return None
    if not isinstance(raw, dict):
        raise HarnessValidationError("Pi step report is malformed")
    if not all(isinstance(key, str) for key in raw):
        raise HarnessValidationError("Pi step report is malformed")
    for value in raw.values():
        if isinstance(value, (list, tuple)) and not all(
            isinstance(item, str) for item in value
        ):
            raise HarnessValidationError("Pi step report is malformed")
        if value is not None and not isinstance(value, (str, list, tuple)):
            raise HarnessValidationError("Pi step report is malformed")
    return raw


def _coerce_response(raw: object) -> PiRunResponse:
    if isinstance(raw, PiRunResponse):
        raw = {
            "status": raw.status,
            "reason": raw.reason,
            "next_action": raw.next_action,
            "artifacts": raw.artifacts,
            "changes": raw.changes,
            "output_reference": raw.output_reference,
            "retryable": raw.retryable,
            "questions": raw.questions,
            "resume_context": raw.resume_context,
            "report": raw.report,
        }
    if isinstance(raw, HarnessResult):
        raw = {
            "status": raw.status,
            "reason": raw.reason,
            "next_action": raw.next_action,
            "artifacts": raw.artifacts,
            "changes": raw.changes,
            "output_reference": raw.output_reference,
            "retryable": raw.retryable,
            "questions": raw.questions,
            "resume_context": raw.resume_context,
            "report": raw.report.fields if raw.report else None,
        }
    if not isinstance(raw, dict):
        raise HarnessValidationError("Pi runtime returned malformed output")
    allowed = {
        "status",
        "reason",
        "next_action",
        "artifacts",
        "changes",
        "output_reference",
        "retryable",
        "questions",
        "resume_context",
        "report",
    }
    if set(raw) - allowed:
        raise HarnessValidationError("Pi runtime returned unsupported fields")
    status = raw.get("status")
    reason = raw.get("reason")
    next_action = raw.get("next_action", "")
    changes = raw.get("changes", ())
    output_reference = raw.get("output_reference")
    retryable = raw.get("retryable", False)
    questions = raw.get("questions", ())
    if (
        not isinstance(status, str)
        or not status.strip()
        or not isinstance(reason, str)
        or not reason.strip()
        or not isinstance(next_action, str)
        or not isinstance(changes, (list, tuple))
        or not all(isinstance(item, str) for item in changes)
        or (output_reference is not None and not isinstance(output_reference, str))
        or not isinstance(retryable, bool)
        or not isinstance(questions, (list, tuple))
        or not all(isinstance(item, str) for item in questions)
    ):
        raise HarnessValidationError("Pi runtime returned malformed output")
    return PiRunResponse(
        status=status,
        reason=reason,
        next_action=next_action,
        artifacts=_coerce_artifacts(raw.get("artifacts")),
        changes=tuple(changes),
        output_reference=output_reference,
        retryable=retryable,
        questions=tuple(questions),
        resume_context=_coerce_resume_context(raw.get("resume_context")),
        report=_coerce_report(raw.get("report")),
    )


class PiHarnessAdapter:
    """Map one step request to exactly one complete Pi session run."""

    identity = "pi"

    def __init__(
        self,
        runtime: PiSdkPort | None = None,
        *,
        runtime_marker: HarnessRuntime | None = None,
        model_profiles: dict[str, object] | None = None,
        clock=time.monotonic,
    ) -> None:
        self.runtime = runtime if runtime is not None else UnavailablePiRuntime()
        self.runtime_marker = runtime_marker
        self.model_profiles = model_profiles or {"default": object()}
        self.clock = clock
        self._process_runtime = runtime is None and runtime_marker is not None

    @classmethod
    def from_runtime(
        cls,
        runtime: HarnessRuntime,
        *,
        sdk: PiSdkPort | None = None,
        model_profiles: dict[str, object] | None = None,
    ) -> PiHarnessAdapter:
        return cls(
            sdk,
            runtime_marker=runtime,
            model_profiles=model_profiles,
        )

    def _private_profile(self, name: str) -> object:
        try:
            return self.model_profiles[name]
        except KeyError as exc:
            raise HarnessValidationError(f"unknown model profile: {name}") from exc

    @staticmethod
    def _discover_artifacts(request: StepStartRequest) -> tuple[HarnessArtifact, ...]:
        task_id = str(request.inputs.get("task_id", ""))
        feature = request.workspace_path / "specs" / task_id
        expected = (
            ("specification", feature / "spec.md"),
            ("plan", feature / "plan.md"),
            ("tasks", feature / "tasks.md"),
        )
        return tuple(
            HarnessArtifact(kind, path.relative_to(request.workspace_path).as_posix())
            for kind, path in expected
            if task_id and path.is_file()
        )

    @staticmethod
    def _decode_result_text(text: str) -> object:
        stripped = text.strip()
        if stripped.startswith("```") and stripped.endswith("```"):
            lines = stripped.splitlines()
            if lines and lines[0].strip().lower() in {"```", "```json"}:
                stripped = "\n".join(lines[1:-1]).strip()
        try:
            value = json.loads(stripped)
        except json.JSONDecodeError as exc:
            raise _PiTransportError("Pi assistant returned malformed step JSON") from exc
        if not isinstance(value, dict):
            raise _PiTransportError("Pi assistant result must be a JSON object")
        return value

    @classmethod
    def _assistant_text(cls, event: dict[str, object]) -> str | None:
        if event.get("type") != "message_end":
            return None
        message = event.get("message")
        if not isinstance(message, dict) or message.get("role") != "assistant":
            return None
        content = message.get("content")
        if not isinstance(content, list):
            return None
        text = "".join(
            part.get("text", "")
            for part in content
            if isinstance(part, dict)
            and part.get("type") == "text"
            and isinstance(part.get("text"), str)
        )
        return text or None

    @classmethod
    def _result_candidate(cls, text: str) -> object | None:
        stripped = text.strip()
        if not stripped.startswith(("{", "```")):
            return None
        return cls._decode_result_text(stripped)

    @staticmethod
    def _decode_rpc_line(line: bytes) -> dict[str, object]:
        try:
            event = json.loads(line.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise _PiTransportError("Pi runtime returned malformed RPC output") from exc
        if not isinstance(event, dict) or not isinstance(event.get("type"), str):
            raise _PiTransportError("Pi runtime returned an invalid RPC event")
        return event

    @staticmethod
    def _stop_process(process: subprocess.Popen[bytes]) -> None:
        if process.poll() is None:
            process.terminate()
            try:
                process.wait(timeout=0.5)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait(timeout=0.5)

    def _run_process(self, request: StepStartRequest) -> object:
        marker = self.runtime_marker
        executable = marker.executable if marker is not None else None
        if (
            marker is None
            or executable is None
            or not executable.is_file()
            or not os.access(executable, os.X_OK)
        ):
            raise _PiTransportError("configured Pi runtime executable is unavailable")
        process: subprocess.Popen[bytes] | None = None
        selector: selectors.BaseSelector | None = None
        buffer = b""
        result: object | None = None
        result_count = 0
        saw_malformed_result = False
        agent_error = False
        try:
            process = subprocess.Popen(
                [str(executable), "--mode", "rpc"],
                cwd=request.workspace_path,
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.DEVNULL,
            )
            assert process.stdin is not None
            assert process.stdout is not None
            process.stdin.write(
                (json.dumps(_rpc_prompt(request), separators=(",", ":")) + "\n").encode("utf-8")
            )
            process.stdin.flush()
            selector = selectors.DefaultSelector()
            selector.register(process.stdout, selectors.EVENT_READ)
            deadline = self.clock() + float(request.timeout_seconds)
            settled = False
            while not settled:
                remaining = deadline - self.clock()
                if remaining <= 0:
                    raise _PiTransportError("Pi harness timed out")
                events = selector.select(remaining)
                if not events:
                    raise _PiTransportError("Pi harness timed out")
                for key, _ in events:
                    chunk = os.read(key.fileobj.fileno(), 65536)
                    if not chunk:
                        continue
                    buffer += chunk
                    while b"\n" in buffer:
                        line, buffer = buffer.split(b"\n", 1)
                        if not line.strip():
                            continue
                        event = self._decode_rpc_line(line.rstrip(b"\r"))
                        event_type = event["type"]
                        if event_type == "response" and event.get("command") == "prompt":
                            if event.get("success") is not True:
                                raise _PiTransportError("Pi rejected the step prompt")
                        elif event_type == "turn_end":
                            message = event.get("message")
                            if isinstance(message, dict) and message.get("stopReason") == "error":
                                agent_error = True
                        elif event_type == "message_end":
                            text = self._assistant_text(event)
                            if text is not None:
                                try:
                                    candidate = self._result_candidate(text)
                                except _PiTransportError:
                                    saw_malformed_result = True
                                else:
                                    if candidate is not None:
                                        result_count += 1
                                        if result_count > 1:
                                            raise _PiTransportError(
                                                "Pi assistant returned multiple step results"
                                            )
                                        result = candidate
                        elif event_type == "agent_settled":
                            settled = True
                            break
                if process.poll() is not None and not settled:
                    raise _PiTransportError("Pi runtime exited before returning a result")
            if agent_error and result is None:
                return {
                    "status": "failed",
                    "reason": "Pi agent failed before returning a step result",
                    "next_action": "inspect the Pi run before retrying",
                }
            if result is None:
                if saw_malformed_result:
                    raise _PiTransportError("Pi assistant returned malformed step JSON")
                raise _PiTransportError("Pi assistant returned no step result")
            if buffer.strip():
                raise _PiTransportError("Pi runtime returned an incomplete RPC event")
            self._stop_process(process)
            return result
        except (OSError, ValueError, subprocess.SubprocessError) as exc:
            if isinstance(exc, _PiTransportError):
                raise
            raise _PiTransportError("Pi runtime could not be started") from exc
        finally:
            if selector is not None:
                selector.close()
            if process is not None:
                self._stop_process(process)
                if process.stdin is not None:
                    process.stdin.close()
                if process.stdout is not None:
                    process.stdout.close()

    def start(self, request: StepStartRequest) -> HarnessResult:
        """Validate, invoke exactly once, and normalize one Pi step run."""
        try:
            validate_step_request(request)
            if "playbook" in request.step_id or request.step_id == PLAYBOOK_ID:
                raise HarnessValidationError("playbook requests are refused")
        except HarnessValidationError:
            raise
        except Exception as exc:
            return _failed(f"Pi startup validation failed: {type(exc).__name__}")

        if self._process_runtime:
            try:
                response = _coerce_response(self._run_process(request))
            except (_PiTransportError, HarnessValidationError) as exc:
                message = str(exc) or "Pi runtime returned malformed output"
                return _failed(message)
            return self._normalize_response(request, response)

        try:
            profile = self._private_profile(request.model_profile)
            if isinstance(profile, str) and contains_secret(profile):
                raise HarnessValidationError("model profile contains a secret")
        except HarnessValidationError:
            raise

        started = self.clock()
        private_request = PiRunRequest(
            step_id=request.step_id,
            flow_id=request.flow_id,
            skill_path=request.skill_path,
            task_id=str(request.inputs.get("task_id", "")),
            task_title=str(request.inputs.get("task_problem", "")),
            task_description=str(request.inputs.get("expected_result", "")),
            acceptance_criteria=str(request.inputs.get("acceptance_criteria", "")),
            workspace_path=request.workspace_path,
            workspace_branch=request.workspace_branch,
            model_profile=profile,
            timeout_seconds=float(request.timeout_seconds),
            deadline=started + float(request.timeout_seconds),
            operator_flags=request.operator_flags,
            resume_context=request.resume_context,
            inputs=dict(request.inputs),
        )
        result_box: list[object] = []
        error_box: list[BaseException] = []
        finished = Event()

        def invoke() -> None:
            try:
                result_box.append(self.runtime.run(private_request))
            except BaseException as exc:  # convert runtime failures to a safe result
                error_box.append(exc)
            finally:
                finished.set()

        Thread(target=invoke, name="hermes-pi-run", daemon=True).start()
        if not finished.wait(float(request.timeout_seconds)):
            return _failed(
                "Pi harness timed out",
                next_action="inspect retained native artifacts before retrying",
            )
        if error_box:
            return _failed(f"Pi runtime failed: {type(error_box[0]).__name__}")
        try:
            response = _coerce_response(result_box[0])
        except (HarnessValidationError, IndexError) as exc:
            return _failed(f"Pi runtime returned malformed output: {type(exc).__name__}")
        if self.clock() > private_request.deadline or response.status == "timeout":
            return _failed(
                "Pi harness timed out",
                next_action="inspect retained native artifacts before retrying",
            )
        return self._normalize_response(request, response)

    def _normalize_response(
        self, request: StepStartRequest, response: PiRunResponse
    ) -> HarnessResult:
        if response.status == "timeout":
            return _failed(
                "Pi harness timed out",
                next_action="inspect retained native artifacts before retrying",
            )
        status = response.status
        if status == "question":
            status = "needs_human"
        elif status in {"blocked", "error"}:
            status = "failed"
        if status not in {"completed", "failed", "needs_human", "stuck"}:
            return _failed("Pi runtime returned an unknown status")
        artifacts, changes, output_reference = _sanitize_advisory_paths(
            response, request.workspace_path
        )
        report = None
        try:
            from .external_framework import parse_step_report

            if response.report is not None:
                report = parse_step_report(request.step_id, response.report)
            elif status == "completed":
                return _failed(f"Pi returned no {request.step_id} compact report")
        except HarnessValidationError as exc:
            return _failed(f"Pi step report rejected: {exc}")
        result = HarnessResult(
            status=status,
            reason=response.reason or "Pi run finished without a reason",
            next_action=response.next_action
            or ("answer the step questions" if status == "needs_human" else ""),
            artifacts=artifacts or self._discover_artifacts(request),
            changes=changes,
            output_reference=output_reference,
            retryable=response.retryable,
            questions=response.questions,
            resume_context=response.resume_context,
            harness_id=self.identity,
            report=report,
        )
        try:
            return validate_harness_result(
                result,
                workspace_path=request.workspace_path,
                adapter_id=self.identity,
                step_id=request.step_id,
            )
        except HarnessValidationError as exc:
            return _failed(f"Pi result rejected: {exc}")
