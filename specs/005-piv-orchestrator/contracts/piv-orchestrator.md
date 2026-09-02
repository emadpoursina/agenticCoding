# Contract: PIV Orchestrator (in-process)

**Feature**: `005-piv-orchestrator` | **Package**: `hermes_kanban.orchestrator`

Library API, not HTTP. Callers are later Hermes workers in the same Python process. Recovery (retry/debug), Git hosting (push/PR), Telegram, and a background worker are **not** in this contract.

Types: see [data-model.md](../data-model.md). Orchestrator errors subclass `OrchestratorError`. Methodology / registry / workspace / executor errors MUST propagate unchanged except as noted.

Reuse: [agent executor](../../004-agent-execution/contracts/agent-executor.md), [workspace manager](../../003-workspace-manager/contracts/workspace-manager.md), [project registry](../../002-project-registry/contracts/project-registry.md), [AiNative adapter](../../001-ainative-adapter/contracts/ainative-adapter.md).

## Construction

```python
class TaskBoard(Protocol):
    def get(self, task_id: str) -> BoardTask: ...
    def list(self) -> tuple[BoardTask, ...]: ...

class PivOrchestrator:
    def __init__(
        self,
        executor: AgentExecutor,
        workspaces: WorkspaceManager,
        registry: ProjectRegistry,
        task_board: TaskBoard,
    ) -> None: ...

    @classmethod
    def from_config(
        cls,
        config_path: Path,
        *,
        model_service: ModelService | None = None,
        task_board: TaskBoard,
    ) -> PivOrchestrator: ...
```

**Trust boundary (construction)**: `from_config` builds the executor (and thereby adapter, registry, workspace manager, execution settings) from the same path. `model_service` omitted → live OpenAI-compatible client (existing 004 rule). Checks MUST pass a stand-in. `task_board` is required. Omitted / `None` → `MissingTaskBoardError`. MUST NOT invent a `kanban.db` path, `$HOME`, or `HERMES_HOME`.

`TaskBoard.get` raises `UnknownTaskError` (or the orchestrator maps a board-specific miss to that type). The orchestrator MUST NOT write `BoardTask` fields.

## Run / next / resume

```python
def run_workflow(self, project_id: str, task_id: str) -> WorkflowRecord: ...

def run_next_workflow(self) -> WorkflowRecord: ...

def resume_workflow(
    self,
    project_id: str,
    task_id: str,
    option: str,
) -> WorkflowRecord: ...
```

All three MUST wait until `COMPLETED`, `FAILED`, or `HUMAN_DECISION_REQUIRED` and return that record. They MUST NOT start a background worker. They MUST write `QUEUED` (or leave parked until a valid resume option is accepted) before the first agent run of that call, then update the record after every step.

### Shared gates (`run_workflow`)

Before the first agent run:

- Slot occupied (`QUEUED` / `RUNNING` / `VALIDATING` / `HUMAN_DECISION_REQUIRED`) → `WorkflowBusyError`. First workflow unchanged.
- `task_id` empty or path-like → existing `InvalidTaskIdError`.
- `resolve_eligible_project` then `load_project_context`. Unknown / disabled / invalid location / missing project configuration → existing registry errors. MUST NOT invent a project path.
- Board `get(task_id)`. Missing → `UnknownTaskError`. MUST NOT invent problem / expected-result / acceptance-criteria text.
- Task `project_id` ≠ caller `project_id` → `TaskProjectMismatchError`.
- Priority not `P0`/`P1`/`P2`/`P3` → `InvalidPriorityError`. MUST NOT invent a priority.
- Unmet dependencies → `UnmetDependenciesError`. Discovery MUST NOT start.
- `prepare_workspace(project_id, task_id)`. Missing copy is created. Dirty reuse → existing `DirtyWorkspaceError` (MUST NOT discard dirty files). Protected work branch → existing `ProtectedBranchError`.
- Live methodology missing a mapped agent → existing `UnknownAgentError`. MUST NOT add agents to methodology.

### `run_next_workflow`

- Same slot gate.
- Selection pool: `task_board.list()`, all enrolled projects.
- Skip (do not fail the scan): ineligible project, unmet dependencies, missing/invalid priority.
- Among remaining: `P0` then `P1` then `P2` then `P3`, then oldest `created_at`.
- None remaining → `NoReadyTaskError`. MUST NOT invent a task or start discovery.
- Then behave as `run_workflow` using the task’s recorded `project_id`.

### `resume_workflow`

- Workflow not `HUMAN_DECISION_REQUIRED` for that `project_id`+`task_id` → `ResumeNotParkedError`. MUST NOT restart a completed or failed run as a side effect.
- `option` empty, not a listed letter, or the option’s text instead of the letter → `InvalidDecisionError`. Stay parked. Isolated copy not published.
- Listed letter (case-insensitive): leave parked state, write `QUEUED`, re-run the parked discovery or planning role with `Human decision: {letter} — {option_text}` appended to execute `description`, then auto-continue if that re-run has an empty questions list. Wait until terminal. Attempt stays `1`. `run_id` unchanged.

## Chain

Order: discovery, planning, implementation, validation. Each step is one existing `execute_role`. After success with an empty questions list, the next step MUST start automatically. There MUST NOT be a plan-approval gate.

Previous-step outputs:

- Discovery context is whatever that role wrote (usually no `PLAN.md`).
- Successful planning: read `PLAN.md` from the isolated copy and pass as `ExecutePayload.plan` into implementation and validation. MUST NOT invent a plan.
- Planning `status=failure` (including missing eight sections) → `FAILED`; implementation MUST NOT start.
- Chosen letter + option text available to the re-run parked step and to later steps (description suffix).

Questions:

- Discovery/planning, non-empty list → `HUMAN_DECISION_REQUIRED` + decision brief. Do not start the next phase. Do not send a message.
- Discovery/planning, empty list → continue. Risks without questions are not a pause.
- `blocked` with questions → park (questions win). `blocked` without questions → `FAILED`.
- Implementation or validation questions → `FAILED` (not a new decision protocol).
- `failure` → `FAILED`. No diagnosis, retry, debug, or attempt increment.

Prepare once at start. Missing copy *during* a later step → visible execute/workspace error → `FAILED`. MUST NOT prepare a second copy for the same task.

## Record

On return (and after every step internally):

- `state` is exactly one of the six values
- `workflow_name`, `current_phase`, `current_worker`, `attempt == 1`
- workspace location and branch after prepare
- `validation_status` pending until validation runs, then pass/fail/blocked from the executor (project commands, not summary prose)
- `blockers` empty when none
- `next_action` as in the data model (never `retry`, never `wait for plan approval`)
- `pull_request` empty/`None`
- `decision` set only when parked
- `steps` includes the `QUEUED` write and each role outcome
- MUST NOT include private reasoning, transcript text, or secrets
- MUST NOT rewrite `BoardTask` problem / expected result / platform / AC / notes / deps / owner / reviewer / priority

PIV-complete (`COMPLETED`): validation passed in the isolated copy on the task work branch; 0 publishes; enrolled location unchanged; no PR required.

## Isolation / editor / methodology

MUST NOT depend on a specific editor. MUST NOT execute instruction documents as programs. MUST NOT publish, merge, deploy, or write methodology. Work branch MUST NOT be `main`, `master`, or the project default.

## Stand-in seams

Checks inject `ModelService` and `TaskBoard`. A live model account, live `kanban.db`, live hosting account, and live messaging bot MUST NOT be required to prove this contract.

## Errors

| Exception | Condition |
|---|---|
| `MissingTaskBoardError` | Construction without an injected board |
| `UnknownTaskError` | Task not on the board |
| `TaskProjectMismatchError` | Named `project_id` ≠ task’s recorded project |
| `InvalidPriorityError` | Named start missing or invalid priority |
| `UnmetDependenciesError` | Named start with unsatisfied dependencies |
| `NoReadyTaskError` | Next-ready found nothing ready |
| `WorkflowBusyError` | Slot occupied |
| `ResumeNotParkedError` | Resume when not parked for that project+task |
| `InvalidDecisionError` | Resume option not a listed letter |
| `OrchestratorError` | Base |
| `InvalidTaskIdError` | Empty or path-like task id (existing) |
| `DirtyWorkspaceError` | Dirty copy at start (existing) |
| `MissingWorkspaceError` | Copy missing during a later step (existing) |
| `ProtectedBranchError` | Work branch protected (existing) |
| `ReadOnlyError` | Methodology write (existing) |
| Registry / executor errors | Unknown project, disabled, bad location, missing project configuration, unknown agent, missing model assignment/credentials |

Boundary failures raise and MUST NOT return a guessed task, project, plan, or validation result.

## Out of contract

- Failure classification, bounded retry, diagnosis, debug loop
- Re-running a `FAILED` workflow
- `git push`, pull requests, merge, deploy
- Writing Hermes `kanban.db` / `projects.db` (no second task table either)
- Telegram / notifications
- Container restart / interrupted-run recovery
- Concurrent execution of more than one workflow
- Adding agents to live methodology
- Installing an external planning framework
- Editor-specific command files
- Critic / plan-reviewer / debugger as required extra steps
