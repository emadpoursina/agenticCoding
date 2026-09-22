"""Provider-neutral contract between Hermes and an execution harness.

The module intentionally knows nothing about a provider SDK.  Provider
translation belongs in the adapter selected by Hermes.

One request is exactly one loop step (an agent state on the canonical
graph in ``/ainative/docs/systems/feature-loop.md``); there is no
whole-playbook request anymore.
"""

from __future__ import annotations

import json
import math
import os
import re
import shutil
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING, Literal, Protocol

from .projects import _parse_document, _path_like_id, _SubsetYamlError

if TYPE_CHECKING:
    pass

# Retired Hermes playbook name. A request carrying it (as a step id or
# playbook reference) is refused, never translated (FR-005, FR-014).
PLAYBOOK_ID = "speckit-orchestrate"
REFUSED_PLAYBOOKS = frozenset({PLAYBOOK_ID})

# Canonical loop states (AiNative/docs/systems/feature-loop.md). The graph
# definition is linked, not copied; Hermes only stores these id strings.
# `change` and `job` are short card paths; the feature graph is unchanged.
AGENT_LOOP_STATES = (
    "ready",
    "specify",
    "clarify",
    "plan",
    "tasks",
    "analyze",
    "implement",
    "converge",
    "critic",
    "tester",
    "pr-review",
    "change",
    "job",
)
HUMAN_STATES = ("confirm", "uat")
PARENT_STATES = ("publish",)
LOOP_STATES = AGENT_LOOP_STATES + HUMAN_STATES + PARENT_STATES
STATE_KINDS: dict[str, str] = {
    **{state: "agent" for state in AGENT_LOOP_STATES},
    **{state: "human" for state in HUMAN_STATES},
    **{state: "parent" for state in PARENT_STATES},
}
# AiNative agent states resolve to docs/agents/<name>/; the rest are
# Spec Kit skills in the task worktree. `change` resolves like critic;
# `job` resolves dynamically to one allowlisted skill and is never Spec Kit.
AINATIVE_STEP_AGENTS = {
    "ready": "ready",
    "critic": "critic",
    "tester": "tester",
    "pr-review": "pr-reviewer",
    "change": "change",
}
SPEC_KIT_STATES = tuple(
    state
    for state in AGENT_LOOP_STATES
    if state not in AINATIVE_STEP_AGENTS and state != "job"
)

RESULT_STATUSES = frozenset({"completed", "failed", "needs_human", "stuck"})
MAX_TEXT = 4096
MAX_ITEMS = 32
_ENV_NAME = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")
_SECRET_NAME = re.compile(r"(?:KEY|TOKEN|SECRET|PASSWORD|CREDENTIAL)", re.IGNORECASE)
_PROVIDER_LEAK = re.compile(
    r"(?:pi\s+sdk|cursor[-_](?:gpt|claude|grok)|\b(?:gpt|claude)-\d|"
    r"openai|anthropic|mariozechner|pi-coding-agent|typescript|"
    r"provider\s*[:=]|client\s*[:=])",
    re.IGNORECASE,
)


class HarnessError(Exception):
    """Base error for harness boundary failures."""


class HarnessConfigurationError(HarnessError):
    """Raised when harness configuration cannot be used safely."""


class HarnessRuntimeError(HarnessConfigurationError):
    """Raised when the configured runtime marker is unavailable or mismatched."""


class HarnessValidationError(HarnessError):
    """Raised when a request or result crosses the boundary unsafely."""


class UnsupportedHarnessError(HarnessConfigurationError):
    """Raised when the configured harness is not supported by this release."""


def coerce_timeout_seconds(value: object) -> float:
    """Convert one configured timeout to a finite, positive float."""
    if isinstance(value, bool) or value is None:
        raise HarnessConfigurationError("harness timeout_seconds must be positive and finite")
    if isinstance(value, str):
        if not value.strip():
            raise HarnessConfigurationError("harness timeout_seconds must be positive and finite")
        candidate: object = value.strip()
    elif isinstance(value, (int, float)):
        candidate = value
    else:
        raise HarnessConfigurationError("harness timeout_seconds must be positive and finite")
    try:
        timeout = float(candidate)
    except (TypeError, ValueError, OverflowError) as exc:
        raise HarnessConfigurationError(
            "harness timeout_seconds must be positive and finite"
        ) from exc
    if not math.isfinite(timeout) or timeout <= 0:
        raise HarnessConfigurationError("harness timeout_seconds must be positive and finite")
    return timeout


@dataclass(frozen=True)
class RepositoryContext:
    """Read-only repository information needed by a harness."""

    repository: str
    default_branch: str
    enrolled_root: Path | None = None


@dataclass(frozen=True)
class SafetyLimits:
    """Non-negotiable write and publication limits for one run."""

    write_root: str = "."
    feature_branch_only: bool = True
    allow_publish: bool = False
    allow_protected_branch: bool = False
    allow_external_writes: bool = False
    reject_secrets: bool = True


@dataclass(frozen=True)
class ResumeContext:
    """Safe operator or recovery data passed to one step attempt."""

    answers: tuple[str, ...] = ()
    assumptions: tuple[str, ...] = ()
    continue_confirmed: bool = False
    diagnostic_summary: str = ""
    prior_reason: str = ""
    resume_reference: str | None = None


@dataclass(frozen=True)
class HarnessArtifact:
    """One native artifact, represented relative to the task worktree."""

    kind: str
    relative_path: str


@dataclass(frozen=True)
class StepStartRequest:
    """One per-step harness start request.

    One instance starts exactly one new Pi session for one agent-kind
    graph state. There is no playbook id and no whole-flow request.
    """

    step_id: str
    flow_id: str
    skill_path: str
    workspace_path: Path
    workspace_branch: str
    model_profile: str
    timeout_seconds: float
    inputs: Mapping[str, object]
    operator_flags: tuple[str, ...] = ()
    resume_context: ResumeContext | None = None


@dataclass(frozen=True)
class StepReport:
    """Strict per-state compact report parsed by Hermes."""

    step_id: str
    fields: Mapping[str, str]
    questions: tuple[str, ...] = ()


@dataclass(frozen=True)
class HarnessResult:
    """The only result Hermes receives from a harness."""

    status: Literal["completed", "failed", "needs_human", "stuck"]
    reason: str
    next_action: str = ""
    artifacts: tuple[HarnessArtifact, ...] = ()
    changes: tuple[str, ...] = ()
    output_reference: str | None = None
    retryable: bool = False
    questions: tuple[str, ...] = ()
    resume_context: ResumeContext | None = None
    harness_id: str = ""
    report: StepReport | None = None


class HarnessAdapter(Protocol):
    """The provider-neutral adapter contract."""

    identity: str

    def start(self, request: StepStartRequest) -> HarnessResult: ...


def contains_secret(value: str) -> bool:
    """Return whether text contains a likely credential or private key."""
    if not isinstance(value, str):
        return False
    lowered = value.lower()
    if "bearer " in lowered or "-----begin " in lowered:
        return True
    for name, secret in os.environ.items():
        if (name == "SSH_AUTH_SOCK" or _SECRET_NAME.search(name)) and len(secret) >= 4:
            if secret in value:
                return True
    return False


def _safe_text(value: object, field: str, *, empty: bool = True) -> str:
    if not isinstance(value, str):
        raise HarnessValidationError(f"{field} must be a string")
    if not empty and not value.strip():
        raise HarnessValidationError(f"{field} must be non-empty")
    if len(value) > MAX_TEXT:
        raise HarnessValidationError(f"{field} is too long")
    if contains_secret(value):
        raise HarnessValidationError(f"{field} contains a secret")
    if _PROVIDER_LEAK.search(value):
        raise HarnessValidationError(f"{field} contains provider or SDK metadata")
    return value


def _validate_items(values: object, field: str) -> tuple[str, ...]:
    if not isinstance(values, (tuple, list)) or len(values) > MAX_ITEMS:
        raise HarnessValidationError(f"{field} must be a bounded sequence")
    result = tuple(_safe_text(value, field, empty=False) for value in values)
    return result


def validate_resume_context(context: ResumeContext | None) -> ResumeContext | None:
    if context is None:
        return None
    if not isinstance(context, ResumeContext):
        raise HarnessValidationError("resume_context must be ResumeContext")
    answers = _validate_items(context.answers, "resume answer")
    assumptions = _validate_items(context.assumptions, "resume assumption")
    diagnostic = _safe_text(context.diagnostic_summary, "diagnostic summary")
    prior = _safe_text(context.prior_reason, "prior reason")
    reference = context.resume_reference
    if reference is not None:
        _safe_text(reference, "resume reference", empty=False)
    return ResumeContext(
        answers=answers,
        assumptions=assumptions,
        continue_confirmed=bool(context.continue_confirmed),
        diagnostic_summary=diagnostic,
        prior_reason=prior,
        resume_reference=reference,
    )


def validate_safety_limits(limits: SafetyLimits) -> SafetyLimits:
    if not isinstance(limits, SafetyLimits):
        raise HarnessValidationError("safety_limits must be SafetyLimits")
    if limits.write_root != ".":
        raise HarnessValidationError("harness write root must be the task worktree")
    if (
        limits.feature_branch_only is not True
        or limits.allow_publish is not False
        or limits.allow_protected_branch is not False
        or limits.allow_external_writes is not False
        or limits.reject_secrets is not True
    ):
        raise HarnessValidationError("unsafe harness limits")
    return limits


def validate_step_request(request: StepStartRequest) -> StepStartRequest:
    """Validate one per-step request before any runtime or model starts."""
    if not isinstance(request, StepStartRequest):
        raise HarnessValidationError("request must be StepStartRequest")
    step = request.step_id
    if not isinstance(step, str) or not step or _path_like_id(step):
        raise HarnessValidationError("step_id is missing or path-like")
    if step in REFUSED_PLAYBOOKS or "playbook" in step:
        raise HarnessValidationError(f"playbook requests are refused: {step}")
    if STATE_KINDS.get(step) != "agent":
        raise HarnessValidationError(f"step_id is not an agent state: {step or '(missing)'}")
    _safe_text(request.flow_id, "flow_id", empty=False)
    _safe_text(request.skill_path, "skill_path", empty=False)
    skill = Path(request.skill_path)
    if skill.is_absolute() or any(part in {"", ".", ".."} for part in skill.parts):
        raise HarnessValidationError("skill_path must be a normalized relative path")
    if not isinstance(request.workspace_path, Path):
        raise HarnessValidationError("workspace path must be a Path")
    workspace = request.workspace_path.resolve(strict=False)
    if workspace.is_symlink() or not workspace.is_dir():
        raise HarnessValidationError("workspace path is unavailable")
    _safe_text(request.workspace_branch, "workspace branch", empty=False)
    if request.workspace_branch in {"main", "master"}:
        raise HarnessValidationError("protected branch is not allowed")
    _safe_text(request.model_profile, "model profile", empty=False)
    if "/" in request.model_profile or "\\" in request.model_profile:
        raise HarnessValidationError("model profile must be a named reference")
    try:
        timeout = coerce_timeout_seconds(request.timeout_seconds)
    except HarnessConfigurationError as exc:
        raise HarnessValidationError(str(exc)) from exc
    if timeout != request.timeout_seconds:
        raise HarnessValidationError("timeout_seconds must be normalized before execution")
    inputs = request.inputs
    if not isinstance(inputs, Mapping) or not inputs or len(inputs) > MAX_ITEMS:
        raise HarnessValidationError("inputs must be a small non-empty mapping")
    for key, value in inputs.items():
        _safe_text(key, "inputs key", empty=False)
        if isinstance(value, str):
            _safe_text(value, f"inputs.{key}")
        elif isinstance(value, (tuple, list)):
            _validate_items(value, f"inputs.{key}")
        else:
            raise HarnessValidationError(f"inputs.{key} must be a string or string sequence")
    flags = _validate_items(request.operator_flags, "operator flag")
    if any(flag not in {"skip"} for flag in flags):
        raise HarnessValidationError("unsupported operator flag")
    validate_resume_context(request.resume_context)
    return request


def step_skill_path(step_id: str) -> str:
    """Return the Spec Kit skill path for one Spec Kit graph state."""
    if step_id not in SPEC_KIT_STATES:
        raise HarnessValidationError(f"step is not a Spec Kit state: {step_id}")
    return f".cursor/skills/speckit-{step_id}/SKILL.md"


# Per-state compact-report contract (contracts/compact-reports.md).
REQUIRED_REPORT_FIELDS: dict[str, tuple[str, ...]] = {
    "ready": ("READY", "FLOW_ID", "BRANCH", "CHECKS", "FIXES"),
    "specify": ("FLOW_ID", "ARTIFACTS", "STATUS", "SUMMARY"),
    "clarify": ("FLOW_ID", "ARTIFACTS", "STATUS", "SUMMARY"),
    "plan": ("FLOW_ID", "ARTIFACTS", "STATUS", "SUMMARY", "ANALYZE"),
    "tasks": ("FLOW_ID", "ARTIFACTS", "STATUS", "SUMMARY"),
    "analyze": ("FLOW_ID", "ARTIFACTS", "STATUS", "SUMMARY"),
    "implement": ("IMPLEMENT_STATUS", "TASKS_DONE", "TASKS_OPEN", "BLOCKER", "SUMMARY"),
    "converge": ("CONVERGE_OUTCOME", "FINDINGS", "FINGERPRINT", "TASKS_APPENDED", "SUMMARY"),
    "critic": ("VERDICT", "SUMMARY"),
    "tester": ("VERDICT", "SUMMARY"),
    "pr-review": ("VERDICT", "SUMMARY"),
    "change": ("STATUS", "SCOPE", "SUMMARY"),
    "job": ("STATUS", "SCOPE", "SUMMARY"),
}
_REPORT_VALUE_SETS: dict[str, frozenset[str]] = {
    "READY": frozenset({"ok", "blocked"}),
    "STATUS": frozenset({"ok", "stuck", "blocked"}),
    "ANALYZE": frozenset({"yes", "no"}),
    "CONVERGE_OUTCOME": frozenset({"converged", "tasks_appended", "blocked"}),
    "VERDICT": frozenset({"PASS", "FAIL"}),
    "SCOPE": frozenset({"ok", "feature"}),
}


def parse_step_report(step_id: str, raw: object) -> StepReport:
    """Strictly parse one state's compact report; unknown/missing fields fail."""
    if step_id not in REQUIRED_REPORT_FIELDS:
        raise HarnessValidationError(f"unknown step report: {step_id}")
    if not isinstance(raw, dict):
        raise HarnessValidationError(f"{step_id} report must be an object")
    required = REQUIRED_REPORT_FIELDS[step_id]
    allowed = set(required)
    if step_id == "clarify":
        allowed.add("questions")
    unknown = set(raw) - allowed
    if unknown:
        raise HarnessValidationError(f"{step_id} report has unsupported fields: {sorted(unknown)}")
    missing = [field for field in required if field not in raw]
    if missing:
        raise HarnessValidationError(f"{step_id} report is missing fields: {missing}")
    fields: dict[str, str] = {}
    for key in required:
        value = _safe_text(raw[key], f"{step_id} report {key}", empty=False)
        expected = _REPORT_VALUE_SETS.get(key)
        if expected is not None and value not in expected:
            raise HarnessValidationError(f"{step_id} report {key} is invalid: {value}")
        fields[key] = value
    questions: tuple[str, ...] = ()
    if "questions" in raw:
        questions = _validate_items(raw["questions"], f"{step_id} report questions")
    return StepReport(step_id=step_id, fields=fields, questions=questions)


def step_report_from_dict(raw: object) -> StepReport | None:
    """Deserialize a saved compact report from the existing overlay."""
    if raw is None:
        return None
    if not isinstance(raw, dict):
        raise ValueError("report must be an object")
    step = raw.get("step_id")
    if not isinstance(step, str) or step not in REQUIRED_REPORT_FIELDS:
        raise ValueError("report step_id is unknown")
    fields = raw.get("fields")
    if not isinstance(fields, dict) or not all(
        isinstance(key, str) and isinstance(value, str) for key, value in fields.items()
    ):
        raise ValueError("report fields must be a string mapping")
    questions = raw.get("questions", ())
    if not isinstance(questions, (list, tuple)) or not all(
        isinstance(item, str) for item in questions
    ):
        raise ValueError("report questions must be a sequence")
    return StepReport(step_id=step, fields=fields, questions=tuple(questions))


def validate_harness_result(
    result: HarnessResult,
    *,
    workspace_path: Path,
    adapter_id: str | None = None,
    step_id: str | None = None,
) -> HarnessResult:
    """Validate normalized adapter output before persistence or advancing."""
    if not isinstance(result, HarnessResult):
        raise HarnessValidationError("adapter did not return HarnessResult")
    if result.status not in RESULT_STATUSES:
        raise HarnessValidationError("unknown harness result status")
    if adapter_id is not None and result.harness_id not in {"", adapter_id}:
        raise HarnessValidationError("harness identity changed during execution")
    if not isinstance(workspace_path, Path) or not workspace_path.is_dir():
        raise HarnessValidationError("result worktree is unavailable")
    reason = _safe_text(result.reason, "result reason", empty=False)
    next_action = _safe_text(result.next_action, "next action")
    questions = _validate_items(result.questions, "question")
    if result.status == "needs_human" and (not questions or not next_action.strip()):
        raise HarnessValidationError("needs_human requires questions and next action")
    artifacts: list[HarnessArtifact] = []
    if not isinstance(result.artifacts, (tuple, list)) or len(result.artifacts) > MAX_ITEMS:
        raise HarnessValidationError("artifacts must be a bounded sequence")
    for artifact in result.artifacts:
        if not isinstance(artifact, HarnessArtifact):
            raise HarnessValidationError("invalid harness artifact")
        kind = _safe_text(artifact.kind, "artifact kind", empty=False)
        artifacts.append(
            HarnessArtifact(
                kind,
                _safe_relative_path(
                    artifact.relative_path,
                    workspace_path,
                    "artifact path",
                    require_file=True,
                ),
            )
        )
    changes = tuple(
        _safe_relative_path(path, workspace_path, "change path", require_file=False)
        for path in _validate_items(result.changes, "change path")
    )
    output = result.output_reference
    if output is not None:
        output = _safe_relative_path(output, workspace_path, "output reference", require_file=True)
    resume = validate_resume_context(result.resume_context)
    harness_id = _safe_text(result.harness_id, "harness id")
    report = result.report
    if report is not None:
        if not isinstance(report, StepReport):
            raise HarnessValidationError("report must be a StepReport")
        if step_id is not None and report.step_id != step_id:
            raise HarnessValidationError("report does not match the started step")
    return HarnessResult(
        status=result.status,
        reason=reason,
        next_action=next_action,
        artifacts=tuple(artifacts),
        changes=changes,
        output_reference=output,
        retryable=bool(result.retryable),
        questions=questions,
        resume_context=resume,
        harness_id=harness_id,
        report=report,
    )


def _safe_relative_path(
    relative: str,
    workspace: Path,
    field: str,
    *,
    require_file: bool,
) -> str:
    _safe_text(relative, field, empty=False)
    path = Path(relative)
    if path.is_absolute() or any(part in {"", ".", ".."} for part in path.parts):
        raise HarnessValidationError(f"{field} must be a normalized relative path")
    root = workspace.resolve()
    candidate = (root / path).resolve(strict=False)
    try:
        candidate.relative_to(root)
    except ValueError as exc:
        raise HarnessValidationError(f"{field} escapes the task worktree") from exc
    current = root
    for part in path.parts[:-1]:
        current /= part
        if current.is_symlink():
            raise HarnessValidationError(f"{field} crosses a symlink")
    if candidate.is_symlink():
        raise HarnessValidationError(f"{field} is a symlink")
    if require_file and (not candidate.is_file() or not os.access(candidate, os.R_OK)):
        raise HarnessValidationError(f"{field} is not a readable file")
    return path.as_posix()


@dataclass(frozen=True)
class HarnessRuntime:
    """A verified runtime marker; the SDK remains private to the adapter."""

    adapter_id: str
    version: str
    revision: str
    runtime_path: Path
    manifest_path: Path
    executable: Path | None = None


@dataclass(frozen=True)
class HarnessConfiguration:
    """Validated harness selection and named profile configuration."""

    adapter_id: str
    model_profile: str
    step_profiles: Mapping[str, str]
    runtime_path_env: str
    runtime: HarnessRuntime
    timeout_seconds: float


def _read_json(path: Path, error: type[HarnessError]) -> dict[str, object]:
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise error(f"cannot read runtime manifest: {path}") from exc
    if not isinstance(raw, dict):
        raise error("runtime manifest must be an object")
    return raw


def load_harness_runtime(
    *,
    adapter_id: str,
    path_env: str,
    executable: str | None = None,
    environ: dict[str, str] | None = None,
) -> HarnessRuntime:
    if not isinstance(path_env, str) or not _ENV_NAME.fullmatch(path_env.strip()):
        raise HarnessConfigurationError("runtime_path_env must be an env-var name")
    values = os.environ if environ is None else environ
    raw_path = values.get(path_env.strip(), "").strip()
    if not raw_path:
        raise HarnessRuntimeError(f"runtime environment variable is missing: {path_env}")
    runtime_path = Path(raw_path).resolve(strict=False)
    manifest_path = runtime_path / "manifest.json"
    raw = _read_json(manifest_path, HarnessRuntimeError)
    configured_id = raw.get("adapter_id", raw.get("provider_id"))
    version = raw.get("version")
    revision = raw.get("revision")
    if (
        configured_id != adapter_id
        or not isinstance(version, str)
        or not version.strip()
        or not isinstance(revision, str)
        or not revision.strip()
    ):
        raise HarnessRuntimeError("runtime marker does not match active harness")
    marker_executable = raw.get("executable")
    requested_executable = executable or (
        marker_executable if isinstance(marker_executable, str) else None
    )
    if requested_executable is None:
        default_executable = runtime_path / "pi"
        if not default_executable.exists():
            raise HarnessRuntimeError("runtime executable is missing")
        requested_executable = "pi"
    requested_executable = requested_executable.strip()
    if not requested_executable:
        raise HarnessRuntimeError("runtime executable is missing")
    candidate = Path(requested_executable)
    if not candidate.is_absolute():
        local_candidate = runtime_path / candidate
        candidate = local_candidate if local_candidate.exists() else Path(
            shutil.which(requested_executable) or ""
        )
    candidate = candidate.resolve(strict=False)
    if not candidate.is_file() or not os.access(candidate, os.X_OK):
        raise HarnessRuntimeError("configured Pi runtime executable is unavailable")
    return HarnessRuntime(
        adapter_id=adapter_id,
        version=version,
        revision=revision,
        runtime_path=runtime_path,
        manifest_path=manifest_path,
        executable=candidate,
    )


def _parse_step_profiles(raw: object) -> dict[str, str]:
    """Parse the optional per-step model-profile mapping; fail closed."""
    if raw is None:
        return {}
    if not isinstance(raw, dict):
        raise HarnessConfigurationError("harness.step_profiles must be a mapping")
    profiles: dict[str, str] = {}
    for key, value in raw.items():
        if not isinstance(key, str) or key not in AGENT_LOOP_STATES:
            raise HarnessConfigurationError(f"unknown harness step profile: {key}")
        if not isinstance(value, str) or not value.strip():
            raise HarnessConfigurationError(f"step profile for {key} must be a named reference")
        if "/" in value or "\\" in value:
            raise HarnessConfigurationError("model profile must be a named reference")
        profiles[key] = value.strip()
    return profiles


def load_harness_config(
    config_path: Path,
    *,
    environ: dict[str, str] | None = None,
) -> HarnessConfiguration:
    """Load one active Pi harness and its verified runtime marker."""
    try:
        document = _parse_document(config_path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, _SubsetYamlError) as exc:
        raise HarnessConfigurationError(f"cannot read harness config: {config_path}") from exc
    raw = document.get("harness")
    if not isinstance(raw, dict):
        raise HarnessConfigurationError("harness is required")
    adapters = raw.get("adapters")
    if not isinstance(adapters, list):
        raise HarnessConfigurationError("harness.adapters must be a sequence")
    active: list[dict[str, object]] = []
    for entry in adapters:
        if not isinstance(entry, dict):
            raise HarnessConfigurationError("harness adapter entries must be mappings")
        if not isinstance(entry.get("active"), bool):
            raise HarnessConfigurationError("harness adapter active must be boolean")
        if entry["active"]:
            active.append(entry)
    if len(active) != 1:
        raise HarnessConfigurationError("exactly one active harness is required")
    selected = active[0]
    adapter_id = selected.get("id")
    if adapter_id != "pi":
        raise UnsupportedHarnessError(f"unsupported harness: {adapter_id}")
    path_env = selected.get("runtime_path_env", selected.get("path_env"))
    if not isinstance(path_env, str) or not path_env.strip():
        raise HarnessConfigurationError("harness runtime_path_env is required")
    if "playbook" in raw:
        raise HarnessConfigurationError("harness.playbook is retired; use per-step states")
    profile = raw.get("model_profile")
    if not isinstance(profile, str) or not profile.strip():
        raise HarnessConfigurationError("harness model_profile is required")
    step_profiles = _parse_step_profiles(raw.get("step_profiles"))
    if "timeout_seconds" not in raw:
        raise HarnessConfigurationError("harness timeout_seconds is required")
    timeout = coerce_timeout_seconds(raw["timeout_seconds"])
    runtime = load_harness_runtime(
        adapter_id="pi",
        path_env=path_env,
        executable=selected.get("executable")
        if isinstance(selected.get("executable"), str)
        else None,
        environ=environ,
    )
    return HarnessConfiguration(
        adapter_id="pi",
        model_profile=profile.strip(),
        step_profiles=step_profiles,
        runtime_path_env=path_env.strip(),
        runtime=runtime,
        timeout_seconds=timeout,
    )


def harness_result_from_dict(raw: object) -> HarnessResult | None:
    """Deserialize a normalized result from the existing overlay."""
    if raw is None:
        return None
    if not isinstance(raw, dict):
        raise ValueError("harness_result must be an object")
    status = raw.get("status")
    reason = raw.get("reason")
    if not isinstance(status, str) or not isinstance(reason, str):
        raise ValueError("harness_result status and reason are required")
    artifacts_raw = raw.get("artifacts", ())
    if isinstance(artifacts_raw, dict):
        artifacts = tuple(
            HarnessArtifact(str(kind), str(path)) for kind, path in artifacts_raw.items()
        )
    elif isinstance(artifacts_raw, (list, tuple)):
        artifacts = tuple(
            HarnessArtifact(str(item["kind"]), str(item["relative_path"]))
            for item in artifacts_raw
            if isinstance(item, dict)
        )
    else:
        raise ValueError("harness_result.artifacts must be a sequence")
    resume_raw = raw.get("resume_context")
    resume = None
    if resume_raw is not None:
        if not isinstance(resume_raw, dict):
            raise ValueError("resume_context must be an object")
        resume = ResumeContext(
            tuple(resume_raw.get("answers", ())),
            tuple(resume_raw.get("assumptions", ())),
            bool(resume_raw.get("continue_confirmed", False)),
            str(resume_raw.get("diagnostic_summary", "")),
            str(resume_raw.get("prior_reason", "")),
            resume_raw.get("resume_reference"),
        )
    return HarnessResult(
        status=status,
        reason=reason,
        next_action=str(raw.get("next_action", "")),
        artifacts=artifacts,
        changes=tuple(raw.get("changes", ())),
        output_reference=raw.get("output_reference"),
        retryable=bool(raw.get("retryable", False)),
        questions=tuple(raw.get("questions", ())),
        resume_context=resume,
        harness_id=str(raw.get("harness_id", "")),
        report=step_report_from_dict(raw.get("report")),
    )
