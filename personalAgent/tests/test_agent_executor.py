import json
import os
import shutil
import subprocess
from dataclasses import fields
from pathlib import Path

import pytest

from hermes_kanban.ainative import UnknownAgentError
from hermes_kanban.executor import (
    AgentExecutor,
    AssembledContext,
    ExecutePayload,
    ExecuteResult,
    ExecutionSettings,
    MissingModelAssignmentError,
    MissingModelCredentialsError,
    MissingWorkspaceError,
    ModelResponse,
)
from hermes_kanban.projects import DisabledProjectError, UnknownProjectError
from hermes_kanban.workspace import InvalidTaskIdError, ProtectedBranchError, WorkspaceManager

AINATIVE_FIXTURE = Path(__file__).parent / "fixtures" / "ainative-full"
PROJECT_FIXTURE = Path(__file__).parent / "fixtures" / "projects" / "standard"
PACKAGE_ROOT = Path(__file__).resolve().parents[1]


def git(*args: str, cwd: Path) -> str:
    result = subprocess.run(
        ["git", *args], cwd=cwd, check=True, capture_output=True, text=True
    )
    return result.stdout.strip()


def copy_methodology(tmp_path: Path) -> Path:
    methodology = tmp_path / "ainative"
    shutil.copytree(AINATIVE_FIXTURE, methodology)
    git("init", cwd=methodology)
    git("config", "user.email", "tests@example.com", cwd=methodology)
    git("config", "user.name", "Tests", cwd=methodology)
    git("add", ".", cwd=methodology)
    git("commit", "-m", "fixture methodology", cwd=methodology)
    return methodology


def copy_project(tmp_path: Path) -> Path:
    project = tmp_path / "enrolled"
    shutil.copytree(PROJECT_FIXTURE, project)
    git("init", "-b", "main", cwd=project)
    git("config", "user.email", "tests@example.com", cwd=project)
    git("config", "user.name", "Tests", cwd=project)
    git("add", ".", cwd=project)
    git("commit", "-m", "fixture project", cwd=project)
    return project


class StandIn:
    def __init__(self, response: ModelResponse | None = None) -> None:
        self.response = response or ModelResponse(summary="ok")
        self.calls: list[tuple[str, AssembledContext]] = []

    def complete(self, *, assignment: str, context: AssembledContext) -> ModelResponse:
        self.calls.append((assignment, context))
        return self.response

    @property
    def context(self) -> AssembledContext:
        return self.calls[-1][1]


def write_config(
    tmp_path: Path,
    *,
    methodology: Path,
    enrolled: Path,
    workspace_root: Path,
    extra: str = "",
    project_extra: str = "",
    model_roles: str | None = None,
) -> Path:
    if model_roles is None:
        model_roles = (
            "  roles:\n"
            "    planning: test-planning-model\n"
            "    implementation: test-implementation-model\n"
            "    validation: test-validation-model\n"
        )
    config = tmp_path / "config.yaml"
    config.write_text(
        "ainative:\n"
        f"  path: {methodology}\n"
        "  read_only: true\n"
        "workspace:\n"
        f"  root: {workspace_root}\n"
        "projects:\n"
        "  - id: fixture\n"
        "    name: Fixture\n"
        "    repository: github.com/example/fixture\n"
        f"    location: {enrolled}\n"
        f"{project_extra}"
        "workflow:\n"
        "  default: piv\n"
        "model:\n"
        f"{model_roles}"
        "  openai_compatible:\n"
        "    base_url_env: OPENAI_BASE_URL\n"
        "    api_key_env: OPENAI_API_KEY\n"
        f"{extra}",
        encoding="utf-8",
    )
    return config


def make_env(
    tmp_path: Path,
    *,
    extra: str = "",
    model_roles: str | None = None,
    prepare: bool = True,
    stand_in: StandIn | None = None,
) -> tuple[AgentExecutor, StandIn, Path, Path, Path]:
    methodology = copy_methodology(tmp_path)
    enrolled = copy_project(tmp_path)
    workspace_root = tmp_path / "ws"
    workspace_root.mkdir()
    write_config(
        tmp_path,
        methodology=methodology,
        enrolled=enrolled,
        workspace_root=workspace_root,
        extra=extra,
        model_roles=model_roles,
    )
    if prepare:
        WorkspaceManager.from_config(tmp_path / "config.yaml").prepare_workspace("fixture", "123")
    service = stand_in or StandIn()
    executor = AgentExecutor.from_config(tmp_path / "config.yaml", model_service=service)
    return executor, service, enrolled, methodology, workspace_root


def test_execute_agent_assembles_context_and_identity(tmp_path: Path):
    executor, stand_in, _enrolled, methodology, _workspace_root = make_env(tmp_path)
    prepared = WorkspaceManager.from_config(tmp_path / "config.yaml").inspect_workspace(
        "fixture", "123"
    )

    result = executor.execute_agent("scout", "fixture", "123")

    assert isinstance(result, ExecuteResult)
    context = stand_in.context
    assert context.task.id == "123"
    assert context.project_id == "fixture"
    assert context.workspace_path == prepared.path
    assert context.workspace_branch == "feature/task-123"
    assert context.workspace_branch not in {"main", "master", "HEAD"}
    assert context.methodology_path == methodology
    assert context.revision.sha
    assert context.agent.name == "scout"
    assert result.identity.worker_id == "scout"
    assert result.identity.workspace_id == "ws-fixture-123"
    assert result.identity.task_id == "123"
    assert result.identity.project_id == "fixture"
    assert result.identity.execution_id
    assert len(result.identity.execution_id) == 32
    assert int(result.identity.execution_id, 16) >= 0
    expected_deps = tuple(executor.adapter.resolve_agent_dependencies("scout"))
    assert context.dependencies == expected_deps
    names = {item.name for item in fields(ExecuteResult)}
    assert not names & {"reasoning", "transcript", "secret", "api_key"}


def test_discovery_reads_workspace_files_and_does_not_write(tmp_path: Path):
    executor, stand_in, enrolled, *_ = make_env(
        tmp_path,
        stand_in=StandIn(
            ModelResponse(
                summary="saw the quiz",
                files={"index.html": "HACKED"},
                commit=True,
            )
        ),
    )
    workspace = WorkspaceManager.from_config(tmp_path / "config.yaml").inspect_workspace(
        "fixture", "123"
    )
    target = workspace.path / "index.html"
    target.write_text("hello quiz", encoding="utf-8")
    enrolled_head = git("rev-parse", "HEAD", cwd=enrolled)
    dirty_before = git("status", "--porcelain", cwd=workspace.path)

    result = executor.execute_agent("scout", "fixture", "123")

    files = {item.path: item.text for item in stand_in.context.workspace_files}
    assert files["index.html"] == "hello quiz"
    assert "README.md" in files
    assert target.read_text(encoding="utf-8") == "hello quiz"
    assert git("rev-parse", "HEAD", cwd=enrolled) == enrolled_head
    assert git("rev-parse", "--abbrev-ref", "HEAD", cwd=workspace.path) == "feature/task-123"
    assert git("status", "--porcelain", cwd=workspace.path) == dirty_before
    assert result.status == "success"
    assert result.identity.worker_id == "scout"


def test_execute_agent_model_slot_validation_does_not_run_project_checks(tmp_path: Path):
    executor, stand_in, *_ = make_env(tmp_path)
    result = executor.execute_agent("tester", "fixture", "123", model_slot="validation")
    assert result.validation is None
    assert stand_in.calls[-1][0] == "test-validation-model"
    executor.execute_agent("tester", "fixture", "123")
    assert stand_in.calls[-1][0] == "test-planning-model"


def test_omitted_payload_does_not_invent_previous_outputs_or_task_fields(tmp_path: Path):
    executor, stand_in, *_ = make_env(tmp_path)

    executor.execute_agent("scout", "fixture", "123")

    context = stand_in.context
    assert context.previous_plan is None
    assert context.previous_validation is None
    assert context.task.title == ""
    assert context.task.description == ""
    assert context.task.acceptance_criteria == ""
    assert context.task.priority == ""


def test_supplied_plan_is_present_unchanged(tmp_path: Path):
    executor, stand_in, *_ = make_env(tmp_path)
    plan = "keep this plan text exactly"

    executor.execute_agent("scout", "fixture", "123", payload=ExecutePayload(plan=plan))

    assert stand_in.context.previous_plan == plan


def test_stand_in_succeeds_without_model_env(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.delenv("OPENAI_BASE_URL", raising=False)
    executor, stand_in, *_ = make_env(tmp_path)

    result = executor.execute_agent("scout", "fixture", "123")

    assert result.status in {"success", "failure", "blocked"}
    assert stand_in.calls
    assert os.environ.get("OPENAI_API_KEY") is None
    assert os.environ.get("OPENAI_BASE_URL") is None


def test_empty_task_id_is_invalid_and_not_joined_to_a_path(tmp_path: Path):
    executor, stand_in, *_rest = make_env(tmp_path)

    with pytest.raises(InvalidTaskIdError):
        executor.execute_agent("scout", "fixture", "../123")
    with pytest.raises(InvalidTaskIdError):
        executor.execute_agent("scout", "fixture", "")
    assert stand_in.calls == []


def test_execution_settings_from_default_yaml_has_no_live_model_ids():
    settings = ExecutionSettings.from_config(PACKAGE_ROOT / "config" / "default.yaml")
    assert settings.workflow_name == "feature-loop"
    assert settings.model_roles["planning"] == ""
    assert settings.harness_step_profiles == {}
    assert settings.profile_for_step("ready") == "default"
    assert settings.base_url_env == "OPENAI_BASE_URL"
    assert settings.api_key_env == "OPENAI_API_KEY"
    text = (PACKAGE_ROOT / "config" / "default.yaml").read_text(encoding="utf-8")
    assert "id: ich-mag-dich" in text
    assert "name: emadpoursina/ich-mag-dich" in text
    assert "location: /workspaces/ich-mag-dich" in text
    assert "id: sandbox" not in text
    assert "hermes-v0-sandbox" not in text
    assert "root: /workspaces" in text
    assert "$HOME" not in text
    assert "WORKSPACE_ROOT" not in text
    assert "gpt-" not in text
    assert "openrouter" not in text.lower()


def test_successful_result_has_explicit_status_shape(tmp_path: Path):
    executor, *_ = make_env(tmp_path)

    result = executor.execute_agent("scout", "fixture", "123")

    assert result.status in {"success", "failure", "blocked"}
    assert isinstance(result.summary, str)
    assert isinstance(result.artifacts, tuple)
    assert result.next_action is None or isinstance(result.next_action, str)
    assert isinstance(result.questions, tuple)


def test_missing_model_assignment_does_not_ask_the_model(tmp_path: Path):
    empty_planning = (
        "  roles:\n"
        "    planning:\n"
        "    implementation: test-implementation-model\n"
        "    validation: test-validation-model\n"
    )
    executor, stand_in, *_ = make_env(tmp_path, model_roles=empty_planning)
    for call in (
        lambda: executor.execute_agent("scout", "fixture", "123"),
    ):
        with pytest.raises(MissingModelAssignmentError):
            call()
    assert stand_in.calls == []

    empty_implementation = (
        "  roles:\n"
        "    planning: test-planning-model\n"
        "    implementation:\n"
        "    validation: test-validation-model\n"
    )
    executor, stand_in, *_ = make_env(
        tmp_path / "impl", model_roles=empty_implementation
    )
    with pytest.raises(MissingModelAssignmentError):
        executor.execute_agent("tester", "fixture", "123", model_slot="implementation")
    assert stand_in.calls == []


def test_live_client_reads_completion_with_sse_done_trailer(
    monkeypatch: pytest.MonkeyPatch,
):
    from hermes_kanban.executor import (
        OpenAICompatibleModelService,
        _load_first_json,
        _parse_model_payload,
    )

    body = (
        '{"id":"router-1","object":"chat.completion","choices":'
        '[{"message":{"content":"{\\"summary\\":\\"ok\\",\\"status\\":\\"success\\",'
        '\\"files\\":{},\\"commit\\":false}"}}]}data: [DONE]\n\n'
    )
    garbage = body.replace("data: [DONE]\n\n", '{"extra":true}')

    class _Reply:
        def __init__(self, payload: str) -> None:
            self._payload = payload

        def read(self) -> bytes:
            return self._payload.encode("utf-8")

        def __enter__(self):
            return self

        def __exit__(self, *_args: object) -> None:
            return None

    class _Agent:
        purpose = "purpose"
        howto = "howto"
        constraints = "rule"

    class _Ctx:
        agent = _Agent()

    assert _load_first_json(body)["choices"][0]["message"]["content"].startswith("{")
    with pytest.raises(json.JSONDecodeError):
        _load_first_json(garbage)

    monkeypatch.setenv("OPENAI_BASE_URL", "http://example.test")
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")
    service = OpenAICompatibleModelService("OPENAI_BASE_URL", "OPENAI_API_KEY")
    monkeypatch.setattr(
        "hermes_kanban.executor.urllib.request.urlopen",
        lambda *_args, **_kwargs: _Reply(body),
    )
    response = service.complete(assignment="DeepSeekFlash", context=_Ctx())  # type: ignore[arg-type]
    assert response.summary == "ok"
    assert response.status == "success"

    monkeypatch.setattr(
        "hermes_kanban.executor.urllib.request.urlopen",
        lambda *_args, **_kwargs: _Reply(garbage),
    )
    failed = service.complete(assignment="DeepSeekFlash", context=_Ctx())  # type: ignore[arg-type]
    assert failed.status == "failure"
    assert failed.summary == "model response could not be parsed"

    live_shape = _parse_model_payload(
        {
            "summary": "Defining landing page subtitle concept with 3 key questions.",
            "files": [],
            "commit": None,
            "status": "in_progress",
        }
    )
    assert live_shape is not None
    assert live_shape.files == {}
    assert live_shape.commit is False
    assert _parse_model_payload({"summary": "ok", "files": "nope"}) is None
    assert _parse_model_payload({"files": {}}) is None


def test_live_empty_http_body_fails_closed_and_url_does_not_double_v1(
    monkeypatch: pytest.MonkeyPatch,
):
    from hermes_kanban.executor import (
        OpenAICompatibleModelService,
        _chat_completions_url,
    )

    empty = (
        Path(__file__).parent / "fixtures" / "model" / "live-empty-body.txt"
    ).read_bytes()
    assert empty == b""
    assert (
        _chat_completions_url("http://127.0.0.1:20128/v1")
        == "http://127.0.0.1:20128/v1/chat/completions"
    )
    assert (
        _chat_completions_url("http://127.0.0.1:20128")
        == "http://127.0.0.1:20128/v1/chat/completions"
    )

    class _Reply:
        def read(self) -> bytes:
            return empty

        def __enter__(self):
            return self

        def __exit__(self, *_args: object) -> None:
            return None

    class _Agent:
        purpose = "p"
        howto = "h"
        constraints = "c"

    class _Ctx:
        agent = _Agent()

    seen: list[str] = []

    def fake_urlopen(request, *_args, **_kwargs):
        seen.append(request.full_url)
        return _Reply()

    monkeypatch.setenv("OPENAI_BASE_URL", "http://127.0.0.1:20128/v1")
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")
    monkeypatch.setattr("hermes_kanban.executor.urllib.request.urlopen", fake_urlopen)
    response = OpenAICompatibleModelService("OPENAI_BASE_URL", "OPENAI_API_KEY").complete(
        assignment="DeepSeekFlash",
        context=_Ctx(),  # type: ignore[arg-type]
    )
    assert seen == ["http://127.0.0.1:20128/v1/chat/completions"]
    assert response.status == "failure"
    assert response.summary == "model response could not be parsed"


def test_live_sends_opencode_session_header_and_fails_closed_on_http_400(
    monkeypatch: pytest.MonkeyPatch,
):
    import io
    import urllib.error
    import urllib.request

    from hermes_kanban.executor import (
        _OPENCODE_SESSION_HEADER,
        OpenAICompatibleModelService,
        _opencode_session_id,
    )

    class _Task:
        id = "t_507ca35e"

    class _Agent:
        purpose = "p"
        howto = "h"
        constraints = "c"

    class _Ctx:
        agent = _Agent()
        task = _Task()
        project_id = "ich-mag-dich"
        workflow_name = "piv"

    captured: list[urllib.request.Request] = []

    def fake_urlopen(request, *_args, **_kwargs):
        captured.append(request)
        raise urllib.error.HTTPError(
            request.full_url,
            400,
            "Bad Request",
            {},
            io.BytesIO(b'{"error":{"message":"MissingSessionID"}}'),
        )

    monkeypatch.setenv("OPENAI_BASE_URL", "http://127.0.0.1:20128/v1")
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")
    monkeypatch.setattr("hermes_kanban.executor.urllib.request.urlopen", fake_urlopen)
    service = OpenAICompatibleModelService("OPENAI_BASE_URL", "OPENAI_API_KEY")
    first = service.complete(assignment="DeepSeekFlash", context=_Ctx())  # type: ignore[arg-type]
    second = service.complete(assignment="DeepSeekFlash", context=_Ctx())  # type: ignore[arg-type]
    assert first.status == "failure"
    assert first.summary == "model HTTP 400"
    assert second.status == "failure"
    header_name = _OPENCODE_SESSION_HEADER.lower()
    sessions = []
    for request in captured:
        headers = {key.lower(): value for key, value in request.header_items()}
        session = headers.get(header_name, "")
        assert session
        sessions.append(session)
    expected = _opencode_session_id(_Ctx())
    assert sessions == [expected, expected]


def test_live_client_requires_credentials_stand_in_does_not(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
):
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.delenv("OPENAI_BASE_URL", raising=False)
    methodology = copy_methodology(tmp_path)
    enrolled = copy_project(tmp_path)
    workspace_root = tmp_path / "ws"
    workspace_root.mkdir()
    config = write_config(
        tmp_path, methodology=methodology, enrolled=enrolled, workspace_root=workspace_root
    )
    WorkspaceManager.from_config(config).prepare_workspace("fixture", "123")
    live = AgentExecutor.from_config(config)
    with pytest.raises(MissingModelCredentialsError):
        live.execute_agent("scout", "fixture", "123")

    stand_in = StandIn()
    injected = AgentExecutor.from_config(config, model_service=stand_in)
    result = injected.execute_agent("scout", "fixture", "123")
    assert result.status == "success"
    assert stand_in.calls


def test_missing_workspace_does_not_prepare(tmp_path: Path):
    executor, stand_in, _enrolled, _methodology, workspace_root = make_env(
        tmp_path, prepare=False
    )
    before = {path for path in workspace_root.rglob("*")}

    def boom(*_args, **_kwargs):
        raise AssertionError("prepare_workspace must not be called")

    executor.workspaces.prepare_workspace = boom  # type: ignore[method-assign]
    with pytest.raises(MissingWorkspaceError):
        executor.execute_agent("scout", "fixture", "123")
    assert stand_in.calls == []
    assert {path for path in workspace_root.rglob("*")} == before


def test_protected_work_branch_is_refused(tmp_path: Path):
    executor, stand_in, *_ = make_env(tmp_path)
    workspace = WorkspaceManager.from_config(tmp_path / "config.yaml").inspect_workspace(
        "fixture", "123"
    )
    git("checkout", "-B", "master", cwd=workspace.path)

    with pytest.raises(ProtectedBranchError):
        executor.execute_agent("scout", "fixture", "123")
    assert stand_in.calls == []
    assert git("rev-parse", "--abbrev-ref", "HEAD", cwd=workspace.path) == "master"


def test_unknown_project_and_path_like_agent_names(tmp_path: Path):
    executor, stand_in, *_ = make_env(tmp_path)
    with pytest.raises(UnknownProjectError):
        executor.execute_agent("scout", "missing", "123")
    with pytest.raises(UnknownAgentError):
        executor.execute_agent("template", "fixture", "123")
    with pytest.raises(UnknownAgentError):
        executor.execute_agent("_skills", "fixture", "123")
    with pytest.raises(UnknownAgentError):
        executor.execute_agent("../scout", "fixture", "123")
    assert stand_in.calls == []

    disabled = tmp_path / "disabled"
    disabled.mkdir()
    enrolled = copy_project(disabled)
    methodology = copy_methodology(disabled)
    workspace_root = disabled / "ws"
    workspace_root.mkdir()
    write_config(
        disabled,
        methodology=methodology,
        enrolled=enrolled,
        workspace_root=workspace_root,
        project_extra="    enabled: false\n",
    )
    disabled_executor = AgentExecutor.from_config(
        disabled / "config.yaml", model_service=StandIn()
    )
    with pytest.raises(DisabledProjectError):
        disabled_executor.execute_agent("scout", "fixture", "123")

