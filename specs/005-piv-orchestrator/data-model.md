# Data Model: PIV Orchestrator

**Feature**: `005-piv-orchestrator` | **Date**: 2026-08-31

In-process Python types (dataclasses). No new database. The task board is the existing board (fixture `TaskBoard` in checks). Execution state is an overlay record on the orchestrator instance, not a second task table and not the human-readable task body. Working copies remain git worktrees from Phase 1. Agent runs remain `ExecuteResult` from Phase 2.

## Board task (read model)

**Entity**: `BoardTask`

Human-readable work item on the one existing board. Source of truth for *what* to do. The orchestrator MUST NOT overwrite these fields with phase/status churn.

| Field | Type | Rules |
|---|---|---|
| `id` | `str` | Required. Same identity rules as workspace `task_id` (non-empty, not path-like). |
| `project_id` | `str` | Required. Recorded project identity. Next-ready uses this; named start must match. |
| `problem` | `str` | Required for a runnable task. Maps to execute `title`. MUST NOT be invented. |
| `expected_result` | `str` | Required for a runnable task. Maps to execute `description` (plus resume suffix when present). |
| `platform` | `str` | Optional. Empty string if omitted. Stays on this record; not an `ExecutePayload` field. |
| `acceptance_criteria` | `str` | Required for a runnable task. Maps to execute `acceptance_criteria`. |
| `technical_notes` | `str` | Optional. Empty if omitted. |
| `dependencies` | `tuple[str, ...]` | Optional. Other task ids this task waits on. Empty means none. |
| `owner` | `str` | Optional. Preserved. Not execution state. |
| `reviewer` | `str` | Optional. Preserved. |
| `priority` | `str` | Ready / named-start require exactly `P0` / `P1` / `P2` / `P3`. Missing or any other value is invalid (not guessed). |
| `created_at` | `str` | ISO-8601 UTC. Oldest-first tie-break for next-ready. |
| `complete` | `bool` | Board-level done flag used **only** to satisfy other tasks’ dependencies. Not PIV `state`. |

**Validation**: Identity checked at the orchestrator trust boundary (reuse `InvalidTaskIdError`). Unknown id → `UnknownTaskError`. Orchestrator reads only; it does not persist this entity.

**Relationships**: Many board tasks; at most one is in an active workflow slot. `project_id` points at an enrolled `ProjectRecord`. Dependencies point at other `BoardTask.id` values.

## Ready task (derived)

**Entity**: ready task (not stored)

A `BoardTask` is ready for `run_next_workflow` when all of:

1. `resolve_eligible_project(project_id)` succeeds (enabled, location usable).
2. `priority` is `P0`/`P1`/`P2`/`P3`.
3. Every id in `dependencies` exists on the board and has `complete is True`.

Selection: among ready tasks, lowest priority rank (`P0` first) then oldest `created_at`. No ready task is not an empty success — it is `NoReadyTaskError`.

Named start does not use this derived set: unmet deps or invalid priority fail at the boundary instead of skipping.

## Execution state (closed set)

**Entity**: workflow `state` (string literal)

| Value | Meaning |
|---|---|
| `QUEUED` | Accepted; not yet running a phase |
| `RUNNING` | Discovery, planning, or implementation in progress (or just finished without park/fail) |
| `VALIDATING` | Validation phase in progress |
| `COMPLETED` | Validation passed; PIV-complete for this phase |
| `FAILED` | A phase ended in failure; this phase will not retry |
| `HUMAN_DECISION_REQUIRED` | Discovery or planning parked on a non-empty questions list |

Unknown values MUST NOT be stored. Status MUST NOT be inferred only from `summary`.

Not in this phase: `BLOCKED`, `RETRYABLE_FAILURE`, `PR_CREATED` (recovery / hosting).

## Phase (closed set)

**Entity**: `current_phase`

| Value | Role run | Default agent (004) |
|---|---|---|
| `discovery` | `execute_role("discovery")` | `scout` |
| `planning` | `execute_role("planning")` | `specs-planner` |
| `implementation` | `execute_role("implementation")` | `builder` |
| `validation` | `execute_role("validation")` | `tester` |

Workflow name on the record is `ExecutionSettings.workflow_name` (default `piv`).

## Decision option / brief

**Entity**: `DecisionOption`

| Field | Type | Rules |
|---|---|---|
| `letter` | `str` | `A`, `B`, `C`, … matching list order. Single Latin letter. |
| `text` | `str` | Exact questions-list item. MUST NOT be rewritten. |

**Entity**: `DecisionBrief`

Parked human decision. Not a Telegram message. Not written into the task body.

| Field | Type | Rules |
|---|---|---|
| `project_id` | `str` | Parked run’s project |
| `task_id` | `str` | Parked run’s task |
| `phase` | `discovery` \| `planning` | The parked step |
| `decision` | `str` | That step’s `ExecuteResult.summary` |
| `why_it_matters` | `str` | `"{phase} cannot continue without this choice."` |
| `options` | `tuple[DecisionOption, ...]` | One per questions item, labeled in order |
| `recommended` | `str \| None` | `None` this phase (`ExecuteResult` has no recommended field) |
| `reply_with` | `str` | `"option letter"` |

Resume `option` MUST match a `letter` case-insensitively. Matching the option `text` instead of the letter is invalid.

## Step snapshot

**Entity**: `StepRecord`

Append-only snapshot written after each role run (and a `QUEUED` marker before the first). Lets a blocking start still prove intermediate states.

| Field | Type | Rules |
|---|---|---|
| `state` | execution state | State after that write |
| `phase` | phase or `""` | Empty only for the initial `QUEUED` row |
| `worker` | `str \| None` | Mapped agent, or `None` before the first run |
| `execute_status` | `success` \| `failure` \| `blocked` \| `None` | `None` before a role has returned |
| `questions` | `tuple[str, ...]` | Empty if none |
| `summary` | `str` | Public. No secrets |

## Workflow record (operational overlay)

**Entity**: `WorkflowRecord`

Control-plane owned. Returned by `run_workflow` / `run_next_workflow` / `resume_workflow`. One active record occupies the V0 slot.

| Field | Type | Rules |
|---|---|---|
| `run_id` | `str` | UUID hex. New on start; unchanged on resume |
| `state` | execution state | Closed set above |
| `workflow_name` | `str` | From settings (`piv` default) |
| `current_phase` | phase | See table |
| `current_worker` | `str \| None` | Agent running or last ran |
| `attempt` | `int` | Always `1` on records this phase writes. MUST NOT increment on resume |
| `project_id` | `str` | Enrolled id |
| `task_id` | `str` | Board identity |
| `task` | `BoardTask` | Snapshot of human-readable fields as loaded (not mutated by state changes) |
| `workspace_path` | `Path \| None` | Isolated copy after prepare; `None` only if prepare has not succeeded |
| `workspace_branch` | `str \| None` | `feature/task-<task_id>` after prepare |
| `workspace_id` | `str \| None` | `ws-{project_id}-{task_id}` after prepare |
| `validation_status` | `pending` \| `pass` \| `fail` \| `blocked` | `pending` until validation runs |
| `blockers` | `tuple[str, ...]` | Empty when none. Park uses `decision`, not this list |
| `next_action` | `str` | `discover` / `plan` / `implement` / `validate` while advancing; `""` on `COMPLETED`/`FAILED`; on park: `reply with the option letter`. MUST NOT be `retry` or `wait for plan approval` |
| `pull_request` | `None` | Empty this phase |
| `decision` | `DecisionBrief \| None` | Set only when `HUMAN_DECISION_REQUIRED` |
| `chosen_option` | `str \| None` | Listed letter after a successful resume; `None` otherwise |
| `steps` | `tuple[StepRecord, ...]` | History of writes after each step |
| `error` | `str \| None` | Public failure message when `FAILED`; no secrets |

**Forbidden contents**: private reasoning, model transcripts, API keys, env values.

**Native mapping (unwritten this phase)**: `project_id` / `workspace_path` / `workspace_branch` / `workflow_name` / `current_phase` correspond to Kanban `project_id` / `workspace_path` / `branch_name` / `workflow_template_id` / `current_step_key`. `state` does **not** map onto native card `status`.

## PIV-complete (predicate)

**Entity**: PIV-complete (not a stored row)

True iff all of:

- `state == COMPLETED`
- discovery and planning succeeded (empty questions after the last planning run)
- implementation ran against the isolated copy
- validation passed from the project’s declared checks (`validation_status == pass`)
- work branch is `feature/task-<task_id>` (not protected)
- nothing was published
- `pull_request` is empty

A pull request MUST NOT be required.

## Relationships

```text
config YAML          -->  ExecutionSettings (existing)
TaskBoard.get/list   -->  BoardTask
ProjectRegistry      -->  eligible ProjectRecord + ProjectContext
WorkspaceManager.prepare_workspace  -->  PreparedWorkspace
BoardTask + prior ExecuteResult
    -->  ExecutePayload
    -->  AgentExecutor.execute_role
    -->  ExecuteResult
    -->  WorkflowRecord (updated after every step)
```

- One orchestrator instance holds at most one active `WorkflowRecord`.
- One `WorkflowRecord` is one project + one task + one attempt (`1`).
- `BoardTask` is read-only from the orchestrator’s point of view.
- Methodology and enrolled project location are never write targets.

## State transitions

```text
(start) --> QUEUED
QUEUED --> RUNNING (discovery)
RUNNING + discovery success, empty questions --> RUNNING (planning)
RUNNING + planning success, empty questions --> RUNNING (implementation)
RUNNING + implementation success, empty questions --> VALIDATING
VALIDATING + validation pass --> COMPLETED
discovery|planning + non-empty questions --> HUMAN_DECISION_REQUIRED
HUMAN_DECISION_REQUIRED + resume letter --> QUEUED then re-run parked phase
any step failure | blocked without questions
  | implementation/validation questions
  | missing copy during a later step
  --> FAILED
COMPLETED | FAILED --> slot free (new start allowed)
```

Resume when not parked does not transition (raises). Invalid resume option does not transition (stays parked).

| Event | Slot | Attempt |
|---|---|---|
| `run_workflow` / `run_next_workflow` while occupied | refuse | unchanged |
| Park | occupied | `1` |
| Resume re-run parks again | occupied | `1` |
| `COMPLETED` / `FAILED` | released | `1` |
