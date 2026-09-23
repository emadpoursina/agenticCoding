"""Single-shot agent execute and per-step harness dispatch.

The live execution path is per-step: :meth:`AgentExecutor.start_step`
assembles one :class:`StepStartRequest` for one agent-kind graph state and
each agent state becomes exactly one new Pi session. The old role map
(discovery/planning/implementation/validation), the whole-playbook
config, and the shell `_run_validation` gate are removed; the tester
state carries the project's declared `validation_commands` as request
inputs and Hermes never executes them itself.
"""

from __future__ import annotations

import json
import os
import re
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
    Revision,
)
from .external_framework import (
    AGENT_LOOP_STATES,
    AINATIVE_STEP_AGENTS,
    HarnessAdapter,
    HarnessConfigurationError,
    HarnessResult,
    HarnessValidationError,
    ResumeContext,
    StepStartRequest,
    coerce_timeout_seconds,
    load_harness_config,
    step_skill_path,
    validate_harness_result,
    validate_step_request,
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

_MODEL_SLOTS = ("planning", "implementation", "validation")
_RESULT_STATUSES = frozenset({"success", "failure", "blocked"})
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
_MAX_WORKSPACE_FILES = 8
_MAX_WORKSPACE_FILE_BYTES = 20 * 1024
_MAX_WORKSPACE_TOTAL_BYTES = 24 * 1024


class ExecutorError(Exception):
    """Base error for agent executor failures."""


class MissingWorkspaceError(ExecutorError):
    """Raised when execute finds no valid prepared working copy."""


class MissingModelAssignmentError(ExecutorError):
    """Raised when the role's model id is missing or empty."""


class MissingModelCredentialsError(ExecutorError):
    """Raised when the live client is missing location or secret env values."""


class InvalidExecutePayloadError(ExecutorError):
    """Raised when an execute payload is present but malformed."""


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
    """Model-assignment slots and per-step harness profile mapping."""

    workflow_name: str
    model_roles: dict[str, str]
    base_url_env: str | None
    api_key_env: str | None
    harness_model_profile: str
    harness_step_profiles: dict[str, str]
    harness_timeout_seconds: float

    @classmethod
    def from_config(cls, config_path: Path) -> ExecutionSettings:
        """Load workflow, model env *names*, and the per-step profile map."""
        try:
            text = config_path.read_text(encoding="utf-8")
        except (OSError, UnicodeError) as exc:
            raise ExecutorError(f"cannot read config: {config_path}") from exc
        cleaned = "\n".join(line for line in text.splitlines() if not line.lstrip().startswith("#"))
        try:
            document = _parse_document(cleaned)
        except _SubsetYamlError as exc:
            raise ExecutorError(f"cannot parse config: {config_path}") from exc

        workflow_name = "feature-loop"
        raw_workflow = document.get("workflow")
        if isinstance(raw_workflow, dict) and "default" in raw_workflow:
            raw_default = raw_workflow["default"]
            if not isinstance(raw_default, str) or not raw_default.strip():
                raise ExecutorError("workflow.default must be non-empty")
            workflow_name = raw_default.strip()

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
        harness_model_profile = "default"
        harness_step_profiles: dict[str, str] = {}
        harness_timeout_seconds = 1800.0
        if isinstance(raw_harness, dict):
            if isinstance(raw_harness.get("model_profile"), str):
                harness_model_profile = raw_harness["model_profile"].strip()
            raw_step_profiles = raw_harness.get("step_profiles")
            if raw_step_profiles is not None:
                if not isinstance(raw_step_profiles, dict):
                    raise ExecutorError("harness.step_profiles must be a mapping")
                for step, profile in raw_step_profiles.items():
                    if step not in AGENT_LOOP_STATES:
                        # Unknown step in the map fails closed at startup.
                        raise ExecutorError(f"unknown harness step profile: {step}")
                    if not isinstance(profile, str) or not profile.strip():
                        raise ExecutorError(f"step profile for {step} must be a named reference")
                    if "/" in profile or "\\" in profile:
                        raise ExecutorError("model profile must be a named reference")
                    harness_step_profiles[step] = profile.strip()
            try:
                harness_timeout_seconds = coerce_timeout_seconds(
                    raw_harness.get("timeout_seconds")
                )
            except HarnessConfigurationError as exc:
                raise ExecutorError(str(exc)) from exc
        return cls(
            workflow_name,
            model_roles,
            base_url_env,
            api_key_env,
            harness_model_profile,
            harness_step_profiles,
            harness_timeout_seconds,
        )

    def profile_for_step(self, step_id: str) -> str:
        """Resolve one step's model profile; unknown steps use the default."""
        return self.harness_step_profiles.get(step_id, self.harness_model_profile)


class ModelService(Protocol):
    def complete(
        self,
        *,
        assignment: str,
        context: AssembledContext,
    ) -> ModelResponse: ...


def _assignment_slot(model_slot: str | None = None) -> str:
    return model_slot or "planning"


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

    for name in ("index.html", "README.md", "AGENTS.md"):
        _add(root / name)
    docs = root / "docs"
    if docs.is_dir():
        for path in sorted(docs.glob("*.md")):
            _add(path)
    return tuple(found)


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
    """Trust boundary for one named agent or one graph step."""

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
                harness_adapter = PiHarnessAdapter.from_runtime(
                    configuration.runtime,
                    model_selections=dict(configuration.models),
                )
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
            model_slot=model_slot,
            framework_artifacts=framework_artifacts,
        )

    def start_step(
        self,
        step_id: str,
        project_id: str,
        task_id: str,
        *,
        task: object | None = None,
        flow_id: str,
        operator_flags: tuple[str, ...] = (),
        resume_context: ResumeContext | None = None,
        timeout_seconds: float | None = None,
    ) -> HarnessResult:
        """Assemble and invoke exactly one per-step provider-neutral request.

        Each agent state is one new Pi session. Requests for non-agent
        states or a retired playbook id are refused before any runtime.
        """
        from .orchestrator import BoardTask

        if step_id not in AGENT_LOOP_STATES:
            raise HarnessValidationError(f"step_id is not an agent state: {step_id}")
        if "playbook" in step_id:
            raise HarnessValidationError("playbook requests are refused")
        selected = self.harness_adapter
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
        # The tester state carries the declared validation_commands as
        # inputs; Hermes does not execute them itself (FR-008).
        card_path = getattr(task, "card_path", "feature") or "feature"
        card_skill = getattr(task, "card_skill", "") or ""
        inputs: dict[str, object] = {
            "task_id": task_id,
            "task_problem": task.problem,
            "expected_result": task.expected_result,
            "acceptance_criteria": task.acceptance_criteria,
            "priority": task.priority,
            "card_path": card_path,
        }
        if step_id == "tester":
            inputs["validation_commands"] = tuple(project_context.validation_commands)
        if step_id == "job":
            from .orchestrator import _JOB_SKILLS

            skill = card_skill.strip().lower()
            if skill not in _JOB_SKILLS:
                raise HarnessValidationError(f"unknown job skill: {card_skill}")
            self.adapter.get_agent(skill)  # fail closed on an unresolvable agent
            skill_path = f"docs/agents/{skill}/"
            inputs["job_skill"] = skill
        elif step_id in AINATIVE_STEP_AGENTS:
            agent_name = AINATIVE_STEP_AGENTS[step_id]
            self.adapter.get_agent(agent_name)  # fail closed on an unresolvable agent
            skill_path = f"docs/agents/{agent_name}/"
        else:
            skill_path = step_skill_path(step_id)
            if not (inspection.path / skill_path).is_file():
                raise HarnessValidationError(f"step skill is missing in the worktree: {skill_path}")
        request = StepStartRequest(
            step_id=step_id,
            flow_id=flow_id,
            skill_path=skill_path,
            workspace_path=inspection.path,
            workspace_branch=inspection.branch,
            model_profile=self.settings.profile_for_step(step_id),
            timeout_seconds=actual_timeout,
            inputs=inputs,
            operator_flags=operator_flags,
            resume_context=resume_context,
        )
        validate_step_request(request)
        result = selected.start(request)
        return validate_harness_result(
            result,
            workspace_path=inspection.path,
            adapter_id=selected.identity,
            step_id=step_id,
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

    def _execute(
        self,
        name: str,
        project_id: str,
        task_id: str,
        *,
        payload: ExecutePayload | None,
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
        agent = self.adapter.get_agent(name)
        dependencies = tuple(self.adapter.resolve_agent_dependencies(name))
        execution = self.adapter.build_execution_context(agent, workflow_phase="agent")
        assignment = self.settings.model_roles.get(_assignment_slot(model_slot), "")
        if not assignment:
            raise MissingModelAssignmentError(
                f"missing model assignment for {_assignment_slot(model_slot)}"
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
        status = response.status if response.status in _RESULT_STATUSES else "success"
        return ExecuteResult(
            status=status,
            summary=response.summary,
            artifacts=(),
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
            validation=None,
        )
