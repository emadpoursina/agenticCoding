# Contract: External Framework Planning Adapter

**Feature**: `011-external-framework-planning`

This contract extends the existing `ainative`, `executor`, `orchestrator`,
`workspace`, and `persist` seams. The live entry remains the only production
construction path for native Kanban and active-provider validation.

## Configuration

```yaml
external_framework:
  providers:
    - id: github-spec-kit
      version: 1.0.1
      active: true
  runtime:
    path_env: HERMES_SPECKIT_RUNTIME
```

The live configuration loader MUST:

1. require an `external_framework.providers` sequence;
2. require exactly one `active: true` entry;
3. reject an unsupported active id, empty id, or empty version;
4. resolve the runtime directory through the named environment variable;
5. read a runtime manifest and require exact provider id, version, and
   non-empty revision equality;
6. perform all checks before constructing a framework model request.

V0 supports only `github-spec-kit`. The provider registry may contain future
implementations, but runtime selection remains one active provider.

## Provider-neutral Python surface

The implementation adds a provider-neutral module under
`personalAgent/src/hermes_kanban/`:

```python
from pathlib import Path
from typing import Protocol

class ExternalFrameworkAdapter(Protocol):
    identity: FrameworkIdentity
    framework_revision: str

    def execute(
        self,
        context: ExternalFrameworkContext,
    ) -> ExternalFrameworkResult: ...

@dataclass(frozen=True)
class FrameworkIdentity:
    id: str
    version: str

@dataclass(frozen=True)
class ExternalFrameworkContext:
    lifecycle_step: str
    task: BoardTask
    project: ProjectContext
    workspace_path: Path
    workspace_branch: str
    provider: FrameworkIdentity
    framework_revision: str
    model_assignment: str
    discovery_summary: str
    previous_artifacts: dict[str, Path]
    decision: str | None
    framework_instructions: str
    workspace_files: tuple[ContextFile, ...] = ()

@dataclass(frozen=True)
class ExternalFrameworkResult:
    status: str
    artifacts: dict[str, Path]
    questions: tuple[str, ...]
    next_action: str
    provider_id: str
    provider_version: str
    framework_revision: str
    summary: str
```

The adapter MUST accept the stable lifecycle names `specify`, `clarify`,
`plan`, `tasks`, and `implement`. It MUST execute only `plan` and `tasks` in
this feature and MUST reject the others with a visible unsupported-step
error. `status` is closed to `success`, `failure`, or `blocked`.

For a single lifecycle call, `artifacts` contains the paths produced by that
step. The orchestrator merges the successful `plan` and `tasks` results into
one normalized V0 planning result stored on `WorkflowRecord`. That combined
result MUST:

- use the active provider identity and the runtime manifest revision;
- return native provider paths, not Hermes aliases;
- return both `plan` and `tasks` paths for a successful V0 planning slice;
- preserve questions and next action without inventing an answer;
- omit transcripts, private reasoning, credentials, and secrets;
- fail closed if any returned path is missing, unreadable, non-regular, or
  outside `workspace_path`.

## Spec Kit adapter

The provider-specific implementation is a small `speckit.py` module backed by
the provider-neutral contract:

```python
class SpecKitAdapter:
    def __init__(
        self,
        runtime: SpecKitRuntime,
        model_service: ModelService,
    ) -> None: ...

    def execute(
        self,
        context: ExternalFrameworkContext,
    ) -> ExternalFrameworkResult: ...
```

The runtime port is injected so checks use a disposable fixture and the live
image uses the pinned release:

```python
class SpecKitRuntime(Protocol):
    identity: FrameworkIdentity
    revision: str

    def bootstrap(self, workspace_path: Path) -> None: ...

    def execute_step(
        self,
        context: ExternalFrameworkContext,
        model_service: ModelService,
    ) -> ExternalFrameworkResult: ...
```

`bootstrap` MUST reuse a matching setup marker, reject a mismatched existing
setup, and copy only provider setup assets into the current task worktree.
It MUST NOT install packages, download files, launch a coding-agent runtime,
or touch the enrolled root, AiNative, control-plane state, or sibling
worktrees. Setup is intentionally retained after the run.

`execute_step` is responsible for the provider's native feature directory
and native output naming. The adapter validates the paths returned by the
runtime and does not create `PLAN.md` or `TASKS.md`.

## Hermes model-service boundary

The existing `ModelService.complete` remains the only model call surface.
Its accepted context becomes the existing `AssembledContext` or the new
`ExternalFrameworkContext` (a type alias or protocol is acceptable). For
framework context it MUST:

- use the configured assignment supplied by `ExecutionSettings`;
- include provider instructions and structured task/project/workspace data;
- avoid AiNative planner/builder instructions;
- return a bounded `ModelResponse` that the runtime can materialize;
- never choose a provider or model from project/framework documents.

The adapter makes exactly one model-service request per supported lifecycle
step in normal execution: one for `plan`, then one for `tasks`. It does not
retry. Existing Hermes orchestration owns retry/recovery decisions.

## Executor and orchestrator integration

The existing executor gains a framework operation that reuses its trust
boundary checks:

```python
def execute_framework(
    self,
    adapter: ExternalFrameworkAdapter,
    lifecycle_step: str,
    project_id: str,
    task_id: str,
    *,
    discovery_summary: str = "",
    previous_artifacts: dict[str, Path] | None = None,
    decision: str | None = None,
) -> ExternalFrameworkResult: ...
```

It validates the task/project/workspace, protected branch, model assignment,
and context before calling the adapter. It MUST NOT call `get_agent` for
external steps.

`PivOrchestrator` receives an optional external adapter for the existing
injected test seam and a required validated adapter on the live constructor.
For the live plan-then-build path it runs:

```text
discovery -> external plan -> external tasks -> PLANNING_COMPLETE
```

The planning branch:

1. runs `execute_role("discovery", ...)` first;
2. parks existing questions before starting any framework call;
3. invokes `execute_framework(..., "plan", ...)`;
4. invokes `execute_framework(..., "tasks", ...)` only after plan succeeds;
5. combines the two native paths and provider metadata into
   `WorkflowRecord.external_result`;
6. appends a planning step and stores `state="PLANNING_COMPLETE"`;
7. writes a free overlay slot and returns without implementation,
   validation, GitHub, merge, or deployment.

On resume, a previously validated plan path may be supplied as
`previous_artifacts` so a task question continues at `tasks`; otherwise the
incomplete step is rerun. Provider failures and questions use existing
`_fail`, `_park`, overlay, heartbeat, and decision behavior. No second retry
machine is added.

`PLANNING_COMPLETE` is terminal for slot occupancy but is not
`COMPLETED`/`PR_CREATED`; validation stays pending and no pull request
identity is created.

## Runtime/CLI behavior

`build_live_orchestrator` MUST validate the active framework and runtime
before opening a model request. It continues to build the native
read-only `SqliteTaskBoard` from `HERMES_HOME/kanban.db`.

When `main` receives a successful planning-only result, it prints the
operator-visible text:

```text
planning complete
```

It returns success for `PLANNING_COMPLETE`, and failure for `FAILED` or
`BLOCKED`, using the existing CLI behavior for other modes.

## Safety and prohibited behavior

The feature MUST NOT:

- modify or copy files into live `AiNative`;
- require `specs-planner` or `builder` in the live methodology;
- write the enrolled project root, control-plane repository, Kanban DB,
  projects DB, or another task worktree;
- create `PLAN.md`, `TASKS.md`, or a second task database;
- install/download Spec Kit during a task;
- launch Cursor/Claude Code or a framework-owned model runtime;
- push, open a pull request, merge, deploy, or run implementation/validation;
- answer framework questions or add adapter-local retries;
- place secrets in artifacts, records, notices, or logs.

## Error mapping

| Condition | Contract result |
|---|---|
| Zero/multiple active providers | Configuration error before model/framework work |
| Unsupported provider or missing pin | Configuration error before model/framework work |
| Runtime missing or manifest mismatch | Runtime error before model work |
| Missing/mismatched setup | Visible failure/blocked result; no overwrite |
| Missing/incomplete task/project/worktree | Existing Hermes boundary error |
| Provider path escapes worktree | Unsafe result; no success artifact paths |
| Native plan/task missing or unreadable | Failure/blocked; no guessed path |
| Framework question | Existing human-decision state with questions/next action |
| Provider/model failure | Existing failure/retry/recovery rules |
| Builder requested in V0 | No builder call; unsupported lifecycle result |
