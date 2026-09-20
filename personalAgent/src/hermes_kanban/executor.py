"""Single-shot agent execute against a prepared workspace."""

from __future__ import annotations

import json
import os
import re
import shlex
import subprocess
import urllib.error
import urllib.request
import uuid
from dataclasses import dataclass, field, fields, is_dataclass
from pathlib import Path
from typing import Protocol

from .ainative import (
    AgentDefinition,
    AgentDependency,
    AiNativeAdapter,
    ReadOnlyError,
    Revision,
)
from .external_framework import (
    HarnessAdapter,
    HarnessConfigurationError,
    HarnessResult,
    HarnessStartRequest,
    HarnessValidationError,
    RepositoryContext,
    ResumeContext,
    SafetyLimits,
    coerce_timeout_seconds,
    load_harness_config,
    task_context_from_board,
    validate_harness_request,
    validate_harness_result,
)
from .pi import PiHarnessAdapter
from .projects import (
    ContextFile,
    ProjectContext,
    ProjectRegistry,
    _parse_document,
    _path_like_id,
    _SubsetYamlError,
)
from .workspace import (
    CorrelationIdentity,
    InvalidTaskIdError,
    InvalidWorkspaceError,
    WorkspaceManager,
)

_ROLES = ("discovery", "planning", "implementation", "validation")
_DEFAULT_ROLE_AGENTS = {
    "discovery": "scout",
    "planning": "specs-planner",
    "implementation": "builder",
    "validation": "tester",
}
_MODEL_SLOTS = ("planning", "implementation", "validation")
_RESULT_STATUSES = frozenset({"success", "failure", "blocked"})
_PLAN_SECTIONS = (
    "problemunderstanding",
    "scope",
    "likelyaffectedparts",
    "implementationapproach",
    "acceptancecriteriamapping",
    "validationstrategy",
    "risks",
    "openquestions",
)
_HEADING = re.compile(r"^##\s+(.*)$")
# 9router (and some OpenAI-compatible hosts) append an SSE closer after one JSON object.
_TRAILING_SSE_DONE = re.compile(r"\A\s*(?:data:\s*\[DONE\]\s*)?\Z")
_OPENCODE_SESSION_HEADER = "x-opencode-session"
# ponytail: process-wide fallback when execute context has no task/workflow ids.
_PROCESS_OPENCODE_SESSION = f"ses_{uuid.uuid4().hex}"
_MODEL_JSON_ONLY = (
    "Reply with one JSON object only. Do not call tools. Do not use markdown fences. "
    "Project file text is already in workspace_files. "
    "Required key: summary (string). Optional keys: files (object of path to file text), "
    "commit (boolean), plan_markdown (string), tasks_markdown (string), next_action (string), "
    "questions (array of strings), status (success, failure, or blocked). "
    "Resolve routine wording and implementation choices yourself; ask questions only "
    "for consequential product, architecture, security, or irreversible decisions. "
    "When the task and acceptance criteria are complete, questions must be an empty array."
)
_SKIP_WORKSPACE_DIRS = frozenset({".git"})
_PREFERRED_WORKSPACE_FILES = ("index.html", "README.md", "AGENTS.md", "CHANGELOG.md")
_MAX_WORKSPACE_FILES = 8
_MAX_WORKSPACE_FILE_BYTES = 20 * 1024
_MAX_WORKSPACE_TOTAL_BYTES = 24 * 1024


class ExecutorError(Exception):
    """Base error for agent executor failures."""


class UnknownRoleError(ExecutorError):
    """Raised when a role name is not in the closed set."""


class MissingWorkspaceError(ExecutorError):
    """Raised when execute finds no valid prepared working copy."""


class MissingModelAssignmentError(ExecutorError):
    """Raised when the role's model id is missing or empty."""


class MissingModelCredentialsError(ExecutorError):
    """Raised when the live client is missing location or secret env values."""


class InvalidExecutePayloadError(ExecutorError):
    """Raised when an execute payload is present but malformed."""


class UnsafeWorkspaceWriteError(ExecutorError):
    """Raised when a model-requested path leaves the isolated copy."""


@dataclass(frozen=True)
class ExecutePayload:
    """Optional task fields and previous-step outputs for one execute."""

    title: str | None = None
    description: str | None = None
    acceptance_criteria: str | None = None
    priority: str | None = None
    plan: str | None = None
    validation: str | None = None


@dataclass(frozen=True)
class _TaskSlice:
    id: str
    title: str
    description: str
    acceptance_criteria: str
    priority: str


@dataclass(frozen=True)
class AssembledContext:
    """Bundle given to ModelService.complete. Not a transcript."""

    task: _TaskSlice
    project_id: str
    project_name: str
    repository: str
    default_branch: str
    project_context: ProjectContext
    workspace_path: Path
    workspace_branch: str
    methodology_path: Path
    revision: Revision
    workflow_name: str
    workflow_phase: str
    agent: AgentDefinition
    dependencies: tuple[AgentDependency, ...]
    previous_plan: str | None
    previous_validation: str | None
    model_assignment: str
    workspace_files: tuple[ContextFile, ...] = ()
    framework_artifacts: dict[str, Path] = field(default_factory=dict)


@dataclass(frozen=True)
class ModelResponse:
    """Closed structured object returned by a model service."""

    summary: str
    files: dict[str, str] = field(default_factory=dict)
    commit: bool = False
    plan_markdown: str | None = None
    tasks_markdown: str | None = None
    next_action: str | None = None
    questions: tuple[str, ...] = ()
    status: str | None = None


@dataclass(frozen=True)
class ExecuteResult:
    """Machine-readable outcome of one execute. No reasoning or secrets."""

    status: str
    summary: str
    artifacts: tuple[Path, ...]
    next_action: str | None
    questions: tuple[str, ...]
    identity: CorrelationIdentity
    model_assignment: str
    validation: str | None = None


@dataclass(frozen=True)
class ExecutionSettings:
    """Role map and model-assignment slots from operational YAML."""

    workflow_name: str
    role_agents: dict[str, str]
    model_roles: dict[str, str]
    base_url_env: str | None
    api_key_env: str | None
    harness_playbook: str
    harness_model_profile: str
    harness_timeout_seconds: float

    @classmethod
    def from_config(cls, config_path: Path) -> ExecutionSettings:
        """Load workflow, roles, and model env *names*. Does not invent model ids."""
        try:
            text = config_path.read_text(encoding="utf-8")
        except (OSError, UnicodeError) as exc:
            raise ExecutorError(f"cannot read config: {config_path}") from exc
        cleaned = "\n".join(line for line in text.splitlines() if not line.lstrip().startswith("#"))
        try:
            document = _parse_document(cleaned)
        except _SubsetYamlError as exc:
            raise ExecutorError(f"cannot parse config: {config_path}") from exc

        workflow_name = "piv"
        raw_workflow = document.get("workflow")
        if isinstance(raw_workflow, dict) and "default" in raw_workflow:
            raw_default = raw_workflow["default"]
            if not isinstance(raw_default, str) or not raw_default.strip():
                raise ExecutorError("workflow.default must be non-empty")
            workflow_name = raw_default.strip()

        role_agents = dict(_DEFAULT_ROLE_AGENTS)
        raw_roles = document.get("roles")
        if isinstance(raw_roles, dict):
            for role in _ROLES:
                if role not in raw_roles:
                    continue
                value = raw_roles[role]
                if isinstance(value, str) and value.strip():
                    role_agents[role] = value.strip()

        model_roles = {slot: "" for slot in _MODEL_SLOTS}
        raw_model = document.get("model")
        if isinstance(raw_model, dict):
            raw_model_roles = raw_model.get("roles")
            if isinstance(raw_model_roles, dict):
                for slot in _MODEL_SLOTS:
                    value = raw_model_roles.get(slot)
                    model_roles[slot] = value.strip() if isinstance(value, str) else ""
            compatible = raw_model.get("openai_compatible")
        else:
            compatible = None

        base_url_env = None
        api_key_env = None
        if isinstance(compatible, dict):
            raw_base = compatible.get("base_url_env")
            raw_key = compatible.get("api_key_env")
            if isinstance(raw_base, str) and raw_base.strip():
                base_url_env = raw_base.strip()
            if isinstance(raw_key, str) and raw_key.strip():
                api_key_env = raw_key.strip()

        raw_harness = document.get("harness")
        harness_playbook = "speckit-orchestrate"
        harness_model_profile = "default"
        harness_timeout_seconds = 1800.0
        if isinstance(raw_harness, dict):
            if isinstance(raw_harness.get("playbook"), str):
                harness_playbook = raw_harness["playbook"].strip()
            if isinstance(raw_harness.get("model_profile"), str):
                harness_model_profile = raw_harness["model_profile"].strip()
            try:
                harness_timeout_seconds = coerce_timeout_seconds(
                    raw_harness.get("timeout_seconds")
                )
            except HarnessConfigurationError as exc:
                raise ExecutorError(str(exc)) from exc
        return cls(
            workflow_name,
            role_agents,
            model_roles,
            base_url_env,
            api_key_env,
            harness_playbook,
            harness_model_profile,
            harness_timeout_seconds,
        )


class ModelService(Protocol):
    def complete(
        self,
        *,
        assignment: str,
        context: AssembledContext,
    ) -> ModelResponse: ...


def _git(repo: Path, *args: str) -> str:
    result = subprocess.run(
        ["git", "-C", str(repo), *args],
        check=True,
        capture_output=True,
        text=True,
    )
    return result.stdout.strip()


def _has_plan_sections(body: str) -> bool:
    found = {
        re.sub(r"[^a-z0-9]", "", match.group(1).lower())
        for line in body.splitlines()
        if (match := _HEADING.match(line.strip()))
    }
    return all(section in found for section in _PLAN_SECTIONS)


def _assignment_slot(role: str | None, model_slot: str | None = None) -> str:
    if model_slot:
        return model_slot
    if role in {"implementation", "validation"}:
        return role
    return "planning"


def _chat_completions_url(base_url: str) -> str:
    """Join /v1/chat/completions without doubling a base that already ends in /v1."""
    root = base_url.strip().rstrip("/")
    if root.endswith("/v1"):
        return f"{root}/chat/completions"
    return f"{root}/v1/chat/completions"


def _opencode_session_id(context: object) -> str:
    """Stable OpenCode Go routing id for one workflow/run. Not a secret."""
    task = getattr(context, "task", None)
    task_id = getattr(task, "id", "") if task is not None else ""
    project_id = getattr(context, "project_id", "") or ""
    workflow = getattr(context, "workflow_name", "") or ""
    if not isinstance(task_id, str):
        task_id = ""
    if not isinstance(project_id, str):
        project_id = ""
    if not isinstance(workflow, str):
        workflow = ""
    if project_id or task_id or workflow:
        digest = uuid.uuid5(
            uuid.NAMESPACE_URL, f"hermes-kanban:{project_id}:{task_id}:{workflow}"
        ).hex
        return f"ses_{digest}"
    return _PROCESS_OPENCODE_SESSION


def _read_workspace_files(workspace: Path) -> tuple[ContextFile, ...]:
    """Read a small, preferred set of text files. Does not write."""
    # ponytail: prefer index.html and a few notes, 24KiB total; upgrade is a card-named list.
    root = workspace.resolve()
    found: list[ContextFile] = []
    total = 0
    seen: set[str] = set()

    def _add(path: Path) -> None:
        nonlocal total
        if len(found) >= _MAX_WORKSPACE_FILES or total >= _MAX_WORKSPACE_TOTAL_BYTES:
            return
        try:
            resolved = path.resolve()
            relative = resolved.relative_to(root).as_posix()
        except (OSError, ValueError):
            return
        if relative in seen or path.is_symlink() or not resolved.is_file():
            return
        try:
            data = resolved.read_bytes()
        except OSError:
            return
        if len(data) > _MAX_WORKSPACE_FILE_BYTES:
            return
        try:
            text = data.decode("utf-8")
        except UnicodeError:
            return
        if total + len(data) > _MAX_WORKSPACE_TOTAL_BYTES:
            return
        seen.add(relative)
        total += len(data)
        found.append(ContextFile(relative, text))

    for name in _PREFERRED_WORKSPACE_FILES:
        _add(root / name)
    docs = root / "docs"
    if docs.is_dir():
        for path in sorted(docs.glob("*.md")):
            _add(path)
    return tuple(found)


def _safe_write_path(relative: str, workspace: Path, methodology: Path, enrolled: Path) -> Path:
    workspace = workspace.resolve()
    candidate = Path(relative)
    if not isinstance(relative, str) or not relative or candidate.is_absolute():
        raise UnsafeWorkspaceWriteError(f"unsafe write: {relative}")
    resolved = candidate.resolve() if candidate.is_absolute() else (workspace / relative).resolve()
    try:
        resolved.relative_to(methodology.resolve())
        raise ReadOnlyError("AiNative methodology is read-only")
    except ValueError:
        pass
    if any(part in {"", ".", ".."} for part in candidate.parts):
        raise UnsafeWorkspaceWriteError(f"unsafe write: {relative}")
    try:
        resolved.relative_to(workspace)
    except ValueError as exc:
        raise UnsafeWorkspaceWriteError(f"unsafe write: {relative}") from exc
    try:
        resolved.relative_to(enrolled.resolve())
        raise UnsafeWorkspaceWriteError(f"unsafe write: {relative}")
    except ValueError:
        pass
    return resolved


def _run_validation(commands: tuple[str, ...], cwd: Path) -> tuple[str, str]:
    # ponytail: no subprocess timeout; upgrade is a bounded timeout when a project check hangs.
    for command in commands:
        try:
            completed = subprocess.run(
                shlex.split(command), cwd=cwd, capture_output=True, text=True
            )
        except OSError:
            return "blocked", "failure"
        if completed.returncode != 0:
            return "fail", "failure"
    return "pass", "success"


def _jsonable(value: object) -> object:
    if value is None or isinstance(value, (bool, int, float, str)):
        return value
    if isinstance(value, Path):
        return str(value)
    if isinstance(value, dict):
        return {str(key): _jsonable(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_jsonable(item) for item in value]
    if is_dataclass(value) and not isinstance(value, type):
        return {item.name: _jsonable(getattr(value, item.name)) for item in fields(value)}
    return str(value)


def _model_system_instructions(context: AssembledContext) -> str:
    """Build safe model instructions for the existing validation service."""
    agent = getattr(context, "agent", None)
    if agent is not None:
        parts = (agent.purpose, agent.howto, agent.constraints)
    else:
        parts = (getattr(context, "framework_instructions", ""),)
    return "\n".join(part for part in (*parts, _MODEL_JSON_ONLY) if part)


def _load_first_json(text: str) -> object:
    """Parse the first JSON value. Allow a trailing SSE `data: [DONE]`. Refuse other leftover."""
    decoder = json.JSONDecoder()
    value, end = decoder.raw_decode(text)
    if not _TRAILING_SSE_DONE.match(text[end:]):
        raise json.JSONDecodeError("Extra data", text, end)
    return value


def _parse_model_payload(raw: object) -> ModelResponse | None:
    if not isinstance(raw, dict):
        return None
    summary = raw.get("summary")
    if not isinstance(summary, str):
        return None
    files = raw.get("files", {})
    if files is None or files == []:
        files = {}
    if not isinstance(files, dict) or not all(
        isinstance(key, str) and isinstance(value, str) for key, value in files.items()
    ):
        return None
    commit = raw.get("commit", False)
    if commit is None:
        commit = False
    if not isinstance(commit, bool):
        return None
    plan_markdown = raw.get("plan_markdown")
    if plan_markdown is not None and not isinstance(plan_markdown, str):
        return None
    tasks_markdown = raw.get("tasks_markdown")
    if tasks_markdown is not None and not isinstance(tasks_markdown, str):
        return None
    next_action = raw.get("next_action")
    if next_action is not None and not isinstance(next_action, str):
        return None
    questions = raw.get("questions", ())
    if questions is None:
        questions = ()
    if not isinstance(questions, (list, tuple)):
        return None
    if not all(isinstance(item, str) for item in questions):
        return None
    status = raw.get("status")
    if status is not None and not isinstance(status, str):
        return None
    return ModelResponse(
        summary=summary,
        files=files,
        commit=commit,
        plan_markdown=plan_markdown,
        tasks_markdown=tasks_markdown,
        next_action=next_action,
        questions=tuple(questions),
        status=status,
    )


class OpenAICompatibleModelService:
    """Stdlib OpenAI-compatible chat completions client.

    ponytail: single-shot structured response (no tool loop, no streaming);
    upgrade is a Hermes-native tool-using worker later.
    """

    def __init__(self, base_url_env: str | None, api_key_env: str | None) -> None:
        self.base_url_env = base_url_env
        self.api_key_env = api_key_env

    def complete(
        self,
        *,
        assignment: str,
        context: AssembledContext,
    ) -> ModelResponse:
        if not self.base_url_env or not self.api_key_env:
            raise MissingModelCredentialsError("missing model location or secret env name")
        base_url = os.environ.get(self.base_url_env, "").strip()
        api_key = os.environ.get(self.api_key_env, "").strip()
        if not base_url or not api_key:
            raise MissingModelCredentialsError("missing model location or secret")
        body = json.dumps(
            {
                "model": assignment,
                "messages": [
                    {
                        "role": "system",
                        "content": _model_system_instructions(context),
                    },
                    {
                        "role": "user",
                        "content": (json.dumps(_jsonable(context)) + "\n\n" + _MODEL_JSON_ONLY),
                    },
                ],
                "tool_choice": "none",
                "stream": False,
            }
        ).encode("utf-8")
        request = urllib.request.Request(
            _chat_completions_url(base_url),
            data=body,
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {api_key}",
                "User-Agent": "hermes-kanban",
                _OPENCODE_SESSION_HEADER: _opencode_session_id(context),
            },
            method="POST",
        )
        try:
            with urllib.request.urlopen(request) as response:
                payload = _load_first_json(response.read().decode("utf-8"))
            if not isinstance(payload, dict):
                raise TypeError("chat completion must be an object")
            content = payload["choices"][0]["message"]["content"]
            if isinstance(content, str):
                normalized = content.strip()
                if normalized.startswith("```") and normalized.endswith("```"):
                    normalized = re.sub(r"^```(?:json)?\s*", "", normalized)
                    normalized = re.sub(r"\s*```$", "", normalized)
                content = _load_first_json(normalized)
            parsed = _parse_model_payload(content)
        except urllib.error.HTTPError as exc:
            return ModelResponse(summary=f"model HTTP {exc.code}", status="failure")
        except (
            KeyError,
            IndexError,
            TypeError,
            ValueError,
            UnicodeError,
            json.JSONDecodeError,
            urllib.error.URLError,
            OSError,
        ):
            parsed = None
        if parsed is None:
            return ModelResponse(summary="model response could not be parsed", status="failure")
        return parsed


class AgentExecutor:
    """Trust boundary for one named agent or role against a prepared workspace."""

    def __init__(
        self,
        adapter: AiNativeAdapter,
        registry: ProjectRegistry,
        workspaces: WorkspaceManager,
        settings: ExecutionSettings,
        model_service: ModelService,
        harness_adapter: HarnessAdapter | None = None,
    ) -> None:
        self.adapter = adapter
        self.registry = registry
        self.workspaces = workspaces
        self.settings = settings
        self.model_service = model_service
        self.harness_adapter = harness_adapter

    @classmethod
    def from_config(
        cls,
        config_path: Path,
        *,
        model_service: ModelService | None = None,
        harness_adapter: HarnessAdapter | None = None,
    ) -> AgentExecutor:
        adapter = AiNativeAdapter.from_config(config_path)
        registry = ProjectRegistry.from_config(config_path)
        workspaces = WorkspaceManager.from_config(config_path, registry)
        settings = ExecutionSettings.from_config(config_path)
        if model_service is None:
            model_service = OpenAICompatibleModelService(
                settings.base_url_env, settings.api_key_env
            )
        if harness_adapter is None:
            try:
                configuration = load_harness_config(config_path)
            except HarnessConfigurationError:
                if "harness:" in config_path.read_text(encoding="utf-8"):
                    raise
            else:
                harness_adapter = PiHarnessAdapter.from_runtime(configuration.runtime)
        return cls(
            adapter,
            registry,
            workspaces,
            settings,
            model_service,
            harness_adapter,
        )

    def execute_agent(
        self,
        name: str,
        project_id: str,
        task_id: str,
        *,
        payload: ExecutePayload | None = None,
        model_slot: str | None = None,
        framework_artifacts: dict[str, Path] | None = None,
    ) -> ExecuteResult:
        return self._execute(
            name,
            project_id,
            task_id,
            payload=payload,
            role=None,
            model_slot=model_slot,
            framework_artifacts=framework_artifacts,
        )

    def execute_role(
        self,
        role: str,
        project_id: str,
        task_id: str,
        *,
        payload: ExecutePayload | None = None,
        framework_artifacts: dict[str, Path] | None = None,
    ) -> ExecuteResult:
        if role not in _ROLES:
            raise UnknownRoleError(f"unknown role: {role}")
        return self._execute(
            self.settings.role_agents[role],
            project_id,
            task_id,
            payload=payload,
            role=role,
            framework_artifacts=framework_artifacts,
        )

    def start_harness(
        self,
        adapter: HarnessAdapter | None,
        project_id: str,
        task_id: str,
        *,
        task: object | None = None,
        timeout_seconds: float | None = None,
        operator_flags: tuple[str, ...] = (),
        resume_context: ResumeContext | None = None,
    ) -> HarnessResult:
        """Assemble and invoke exactly one provider-neutral harness request."""
        from .orchestrator import BoardTask

        selected = adapter or self.harness_adapter
        if selected is None:
            raise HarnessValidationError("harness adapter is required")
        if not isinstance(task, BoardTask):
            raise HarnessValidationError("complete board task is required")
        if task.id != task_id or task.project_id != project_id:
            raise HarnessValidationError("task identity does not match harness request")
        if not isinstance(task_id, str) or _path_like_id(task_id):
            raise InvalidTaskIdError(f"invalid task id: {task_id}")
        project_context = self.registry.load_project_context(project_id)
        try:
            inspection = self.workspaces.inspect_workspace(project_id, task_id)
        except InvalidWorkspaceError as exc:
            raise MissingWorkspaceError(f"missing workspace: {project_id} {task_id}") from exc
        expected_workspace = (self.workspaces.workspace_root / project_id / task_id).resolve(
            strict=False
        )
        if inspection.path.resolve(strict=False) != expected_workspace:
            raise HarnessValidationError("harness worktree boundary mismatch")
        if inspection.branch != f"feature/task-{task_id}":
            raise HarnessValidationError("harness branch boundary mismatch")
        self.workspaces.assert_publish_allowed(
            inspection.branch, default_branch=project_context.default_branch
        )
        actual_timeout = (
            self.settings.harness_timeout_seconds if timeout_seconds is None else timeout_seconds
        )
        try:
            actual_timeout = coerce_timeout_seconds(actual_timeout)
        except HarnessConfigurationError as exc:
            raise HarnessValidationError(str(exc)) from exc
        request = HarnessStartRequest(
            project_id=project_id,
            task_id=task_id,
            task_context=task_context_from_board(task),
            repository_context=RepositoryContext(
                project_context.repository,
                project_context.default_branch,
                project_context.location,
            ),
            workspace_path=inspection.path,
            workspace_branch=inspection.branch,
            playbook_id=self.settings.harness_playbook,
            model_profile=self.settings.harness_model_profile,
            timeout_seconds=actual_timeout,
            safety_limits=SafetyLimits(),
            operator_flags=operator_flags,
            resume_context=resume_context,
        )
        validate_harness_request(request)
        result = selected.start(request)
        return validate_harness_result(
            result,
            workspace_path=inspection.path,
            adapter_id=selected.identity,
        )

    def _payload(self, payload: ExecutePayload | None) -> ExecutePayload:
        if payload is None:
            return ExecutePayload()
        if not isinstance(payload, ExecutePayload):
            raise InvalidExecutePayloadError("payload must be ExecutePayload")
        for name in (
            "title",
            "description",
            "acceptance_criteria",
            "priority",
            "plan",
            "validation",
        ):
            value = getattr(payload, name)
            if value is not None and not isinstance(value, str):
                raise InvalidExecutePayloadError(f"payload.{name} must be a string")
        return payload

    def _apply_files(
        self,
        files: dict[str, str],
        *,
        workspace: Path,
        methodology: Path,
        enrolled: Path,
        branch: str,
        default_branch: str,
        commit: bool,
        task_id: str,
    ) -> None:
        # ponytail: whole-file writes from the model list (no tool loop);
        # upgrade is a Hermes-native tool-using worker.
        targets = [
            (_safe_write_path(relative, workspace, methodology, enrolled), content)
            for relative, content in files.items()
        ]
        for path, content in targets:
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(content, encoding="utf-8")
        if not commit:
            return
        self.workspaces.assert_publish_allowed(branch, default_branch=default_branch)
        if not _git(workspace, "status", "--porcelain"):
            return
        _git(workspace, "add", "-A")
        _git(workspace, "commit", "-m", f"task {task_id}")

    def _execute(
        self,
        name: str,
        project_id: str,
        task_id: str,
        *,
        payload: ExecutePayload | None,
        role: str | None,
        model_slot: str | None = None,
        framework_artifacts: dict[str, Path] | None = None,
    ) -> ExecuteResult:
        if not isinstance(task_id, str) or _path_like_id(task_id):
            raise InvalidTaskIdError(f"invalid task id: {task_id}")
        self.registry.resolve_eligible_project(project_id)
        project_context = self.registry.load_project_context(project_id)
        try:
            inspection = self.workspaces.inspect_workspace(project_id, task_id)
        except InvalidWorkspaceError as exc:
            raise MissingWorkspaceError(f"missing workspace: {project_id} {task_id}") from exc
        self.workspaces.assert_publish_allowed(
            inspection.branch, default_branch=project_context.default_branch
        )
        payload = self._payload(payload)
        if role == "validation" and model_slot is None:
            validation, status = _run_validation(
                project_context.validation_commands, inspection.path
            )
            return ExecuteResult(
                status=status,
                summary=f"project checks {validation}",
                artifacts=(),
                next_action=None,
                questions=(),
                identity=CorrelationIdentity(
                    task_id=task_id,
                    execution_id=uuid.uuid4().hex,
                    project_id=project_id,
                    workspace_id=f"ws-{project_id}-{task_id}",
                    worker_id=self.settings.role_agents[role],
                ),
                model_assignment="",
                validation=validation,
            )
        agent = self.adapter.get_agent(name)
        dependencies = tuple(self.adapter.resolve_agent_dependencies(name))
        execution = self.adapter.build_execution_context(agent, workflow_phase=role or "agent")
        assignment = self.settings.model_roles.get(_assignment_slot(role, model_slot), "")
        if not assignment:
            raise MissingModelAssignmentError(
                f"missing model assignment for {_assignment_slot(role)}"
            )
        context = AssembledContext(
            task=_TaskSlice(
                id=task_id,
                title=payload.title or "",
                description=payload.description or "",
                acceptance_criteria=payload.acceptance_criteria or "",
                priority=payload.priority or "",
            ),
            project_id=project_id,
            project_name=project_context.name,
            repository=project_context.repository,
            default_branch=project_context.default_branch,
            project_context=project_context,
            workspace_path=inspection.path,
            workspace_branch=inspection.branch,
            methodology_path=execution.methodology_path,
            revision=execution.revision,
            workflow_name=self.settings.workflow_name,
            workflow_phase=execution.workflow_phase or "agent",
            agent=agent,
            dependencies=dependencies,
            previous_plan=payload.plan,
            previous_validation=payload.validation,
            model_assignment=assignment,
            workspace_files=_read_workspace_files(inspection.path),
            framework_artifacts=dict(framework_artifacts or {}),
        )
        response = self.model_service.complete(assignment=assignment, context=context)
        artifacts: tuple[Path, ...] = ()
        failed = False
        if role == "planning":
            plan_path = inspection.path / "PLAN.md"
            plan_path.write_text(response.plan_markdown or "", encoding="utf-8")
            if _has_plan_sections(response.plan_markdown or ""):
                artifacts = (plan_path,)
            else:
                failed = True
        elif role == "implementation":
            self._apply_files(
                response.files,
                workspace=inspection.path,
                methodology=execution.methodology_path,
                enrolled=project_context.location,
                branch=inspection.branch,
                default_branch=project_context.default_branch,
                commit=response.commit,
                task_id=task_id,
            )
        validation = None
        if role == "validation":
            validation, status = _run_validation(
                project_context.validation_commands, inspection.path
            )
        else:
            status = (
                "failure"
                if failed
                else (response.status if response.status in _RESULT_STATUSES else "success")
            )
        return ExecuteResult(
            status=status,
            summary=response.summary,
            artifacts=artifacts,
            next_action=response.next_action,
            questions=response.questions,
            identity=CorrelationIdentity(
                task_id=task_id,
                execution_id=uuid.uuid4().hex,
                project_id=project_id,
                workspace_id=f"ws-{project_id}-{task_id}",
                worker_id=name,
            ),
            model_assignment=assignment,
            validation=validation,
        )
