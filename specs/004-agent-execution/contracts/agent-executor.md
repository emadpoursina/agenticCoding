# Contract: Agent Executor (in-process)

**Feature**: `004-agent-execution` | **Package**: `hermes_kanban.executor`

Library API, not HTTP. Callers are later Hermes workers in the same Python process. Plan → implement → validate chaining, retry, Git hosting (push/PR), and Telegram are **not** in this contract.

Types: see [data-model.md](../data-model.md). Executor errors subclass `ExecutorError`. Methodology / registry / workspace errors MUST propagate unchanged except missing workspace → `MissingWorkspaceError`.

## Construction

```python
class ExecutionSettings:
    workflow_name: str
    role_agents: dict[str, str]
    model_roles: dict[str, str]
    base_url_env: str | None
    api_key_env: str | None

    @classmethod
    def from_config(cls, config_path: Path) -> ExecutionSettings: ...

class ModelService(Protocol):
    def complete(
        self,
        *,
        assignment: str,
        context: AssembledContext,
    ) -> ModelResponse: ...

class AgentExecutor:
    def __init__(
        self,
        adapter: AiNativeAdapter,
        registry: ProjectRegistry,
        workspaces: WorkspaceManager,
        settings: ExecutionSettings,
        model_service: ModelService,
    ) -> None: ...

    @classmethod
    def from_config(
        cls,
        config_path: Path,
        *,
        model_service: ModelService | None = None,
    ) -> AgentExecutor: ...
```

**Trust boundary (construction)**: `from_config` builds adapter, registry, and workspace manager from the same path (those classes keep their own validation). `ExecutionSettings.from_config` MUST NOT invent model ids or host paths. `model_service` omitted → live OpenAI-compatible client using `base_url_env` / `api_key_env`. Checks MUST pass a stand-in.

## Execute

```python
def execute_agent(
    self,
    name: str,
    project_id: str,
    task_id: str,
    *,
    payload: ExecutePayload | None = None,
) -> ExecuteResult: ...

def execute_role(
    self,
    role: str,
    project_id: str,
    task_id: str,
    *,
    payload: ExecutePayload | None = None,
) -> ExecuteResult: ...
```

### Shared gates (before the model is asked)

- `role` (when used) MUST be `discovery` | `planning` | `implementation` | `validation`. Else `UnknownRoleError`.
- `execute_role` maps `role` through `settings.role_agents` (defaults: scout / specs-planner / builder / tester).
- `name` MUST follow the methodology adapter identity rules. Unknown, reserved, path-like → existing `UnknownAgentError`. MUST NOT join a caller-supplied name onto a filesystem path.
- Unresolved dependencies → existing `UnresolvedDependencyError`. MUST NOT run a partial context.
- `resolve_eligible_project` then `load_project_context`. Unknown / disabled / invalid location / missing project configuration → existing registry errors. MUST NOT invent a project path.
- `inspect_workspace(project_id, task_id)`. MUST NOT call `prepare_workspace`. Missing or invalid copy → `MissingWorkspaceError`. Dirty copy is allowed.
- Work branch MUST pass `assert_publish_allowed` (`main` / `master` / project default refused).
- Model assignment for the role slot MUST be a non-empty string. Discovery and bare `execute_agent` use the planning slot. Missing/empty → `MissingModelAssignmentError`. MUST NOT invent a model.
- Live client: empty/missing env for base URL or API key → `MissingModelCredentialsError`. Stand-in MUST NOT require env.
- Payload omitted slots stay empty/`None`. MUST NOT read the host task store. MUST NOT invent previous-step outputs.

### Context

Assembled context MUST include non-empty task id, project id, workspace path, workspace branch, methodology path, methodology revision SHA, agent definition, and resolved dependencies. Previous plan/validation present only when the payload supplied them.

Supporting rules and skills MUST be the same list `resolve_agent_dependencies` already returns.

### Result

On a completed run (model was asked, or validation commands ran):

- `status` is exactly `success` | `failure` | `blocked`
- `summary`, `artifacts` (possibly empty), `next_action` (possibly empty/`None`), `questions` (possibly empty)
- `identity.worker_id` equals the agent that ran
- `identity` includes `task_id`, `project_id`, `workspace_id`, `execution_id`
- `model_assignment` equals the role’s configured id
- MUST NOT include private reasoning, transcript text, or secrets

Boundary failures raise and MUST NOT return a guessed agent, project, workspace, or model.

### Planning

Successful planning-role run MUST write `{workspace}/PLAN.md` with the eight required sections and list that path on `artifacts`. Missing sections → `status=failure`. Discovery MUST NOT require this artifact.

Planner how-to text is passed through. MUST NOT install an external planning framework into the control plane.

### Implementation

File writes from `ModelResponse.files` occur only inside the isolated copy. Paths under methodology → `ReadOnlyError`, methodology unchanged. Paths that escape the copy or target the enrolled location → `UnsafeWorkspaceWriteError`. Optional local `git commit` only in that copy on the work branch after `assert_publish_allowed`. MUST NOT push, open a pull request, merge, deploy, or edit the enrolled project location.

### Validation

MUST run `project_context.validation_commands` with `cwd` = isolated copy. MUST NOT invent generic checks. `result.validation` and `result.status` come from command outcomes, not from model prose. The model is still asked (assignment gate applies); claimed model status is overwritten.

### Isolation / editor

MUST NOT depend on a specific editor. MUST NOT execute instruction documents as programs. MUST NOT create the workspace as a side effect. MUST publish 0 branches.

## Stand-in model service

Checks inject a `ModelService` that returns predetermined `ModelResponse` values. A live model account MUST NOT be required for contract checks.

## Errors

| Exception | Condition |
|---|---|
| `UnknownRoleError` | Role not in the closed set |
| `MissingWorkspaceError` | No valid prepared copy; execute did not prepare one |
| `MissingModelAssignmentError` | Role model id missing or empty |
| `MissingModelCredentialsError` | Live client missing location or secret |
| `InvalidExecutePayloadError` | Malformed payload types |
| `UnsafeWorkspaceWriteError` | Write target outside the isolated copy or into the enrolled tree |
| `ReadOnlyError` | Write would mutate methodology (existing adapter error) |
| `UnknownAgentError` | Unlisted / reserved / path-like agent name (existing) |
| `UnresolvedDependencyError` | Skill resolve failed (existing) |
| `ProtectedBranchError` | Work branch is protected (existing) |
| Registry errors | Unknown / disabled / invalid location / missing project configuration |

## Out of contract

- Plan → implement → validate orchestration and state transitions
- Failure classification, retry, debug loop, human-decision pause
- `git push`, pull requests, merge, deploy
- Reading or writing `kanban.db` / `projects.db`
- Adding agents to live methodology
- Installing specs.md or any editor command files
- Telegram / notifications
- Concurrent executes
