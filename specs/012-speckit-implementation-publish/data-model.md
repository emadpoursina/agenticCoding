# Data Model: Spec Kit Implementation and Publish

**Feature**: `012-speckit-implementation-publish` | **Date**: 2026-09-07

This feature extends the existing in-process Hermes records. It adds no
task table, Kanban write, second overlay, or provider-owned control plane.

## Active external framework

The runtime-selected provider remains one immutable identity:

| Field | Type | Rules |
|---|---|---|
| `id` | `str` | Exact V0 value: `github-spec-kit`. |
| `version` | `str` | Non-empty configured pin; V0 value: `1.0.1`. |
| `framework_revision` | `str` | Non-empty exact revision from the runtime manifest. |

The same identity and revision must govern `plan`, `tasks`, `implement`, and
implementation-fix calls. A changed active provider, version, runtime
revision, or setup marker fails before a model call.

## Native implementation handoff

The existing combined `ExternalFrameworkResult` is the handoff carried by
the workflow:

| Field | Type | Rules |
|---|---|---|
| `artifacts["plan"]` | `Path` | Readable regular native plan file below the task worktree. |
| `artifacts["tasks"]` | `Path` | Readable regular native task-list file below the task worktree. |
| `artifacts[implementation key]` | `Path` | Optional validated provider-native implementation output or changed file. |
| `provider_id` | `str` | Matches the active provider exactly. |
| `provider_version` | `str` | Matches the active pin exactly. |
| `framework_revision` | `str` | Matches the runtime manifest exactly. |
| `status` | `Literal["success", "failure", "blocked"]` | Explicit provider outcome. |
| `questions` | `tuple[str, ...]` | Safe human questions only; no private reasoning. |
| `next_action` | `str` | Safe resume/operator action. |
| `summary` | `str` | Bounded operator-facing summary without secrets/transcripts. |

Plan/tasks paths remain unchanged when passed to implement, validation, and
recovery. Hermes does not rename, mirror, or replace them with `PLAN.md`,
`TASKS.md`, a second task list, or a second feature directory.

An implementation success must be explicit. If the provider returns no
changed file, the adapter may retain the validated prior handoff as the
success evidence only when the provider explicitly reports success; it must
not infer success from files alone. Failure and blocked results contain no
guessed artifact paths.

## External framework context

`ExternalFrameworkContext` remains the stable input to one lifecycle call:

| Field | Type | Rules |
|---|---|---|
| `lifecycle_step` | `str` | One of `specify`, `clarify`, `plan`, `tasks`, `implement`; V0 executes only the last three. |
| `task` | `BoardTask` | Current board identity and human task body. |
| `project` | `ProjectContext` | Current enrolled project context. |
| `workspace_path` | `Path` | Prepared task worktree, never enrolled root. |
| `workspace_branch` | `str` | Current non-protected feature branch. |
| `provider` | `FrameworkIdentity` | Active identity shared across all steps. |
| `framework_revision` | `str` | Exact manifest revision. |
| `model_assignment` | `str` | Planning slot for plan/tasks; implementation slot for implement/fixes. |
| `discovery_summary` | `str` | Safe result from AiNative `scout`. |
| `previous_artifacts` | `dict[str, Path]` | Validated native paths, required for implement after planning. |
| `validation_summary` | `str` | Last validation result when implementing a recovery fix. |
| `diagnostic_summary` | `str` | Existing diagnostic report when implementing a recovery fix. |
| `decision` | `str \| None` | Human choice when resuming a parked framework step. |
| `framework_instructions` | `str` | Provider instructions, never an AiNative builder prompt. |
| `workspace_files` | `tuple[ContextFile, ...]` | Bounded read-only project snapshot. |

No context field stores credentials, model transcripts, private reasoning, or
unbounded command output.

## Model response for implementation

The existing `ModelResponse` remains the model-service result:

| Field | Type | Rules |
|---|---|---|
| `status` | `str \| None` | Must explicitly be `success`, `failure`, or `blocked` when normalized. |
| `summary` | `str` | Safe bounded summary. |
| `files` | `dict[str, str]` | Relative worktree paths and UTF-8 contents; validated before writing. |
| `commit` | `bool` | Local commit request only; never a push or PR request. |
| `questions` | `tuple[str, ...]` | Parks through existing human-decision handling. |
| `next_action` | `str \| None` | Safe resume action. |

Implementation file keys are resolved relative to the task worktree and
rejected if absolute, traversal-based, symlinked, outside the worktree, or
secret-bearing. The enrolled project root, AiNative, runtime source,
control-plane state, and sibling worktrees are outside the write set.

## Validation context

The existing validation/tester context is extended with the handoff rather
than a Hermes plan alias:

| Field | Type | Rules |
|---|---|---|
| `framework_artifacts` | `dict[str, Path]` | Same validated plan/tasks and implementation paths. |
| `previous_validation` | `str \| None` | Existing bounded validation summary. |
| `workflow_phase` | `str` | Existing `validation`, `diagnosis`, or `debug` phase. |

Project validation commands remain authoritative. The external provider does
not run validation or classify failures.

## Workflow record extension

`WorkflowRecord` continues to be the operational source of truth in
`overlay.json`:

| Field | Type | Rules |
|---|---|---|
| `external_result` | `ExternalFrameworkResult \| None` | Round-trips for old and new overlays; preserves native paths and provider identity. |
| `steps` | `tuple[StepRecord, ...]` | Records planning checkpoint, implement outcome, validation, recovery, and publish. |
| `validation_status` | `str` | Remains `pending` through planning and implementation; becomes `pass` only after checks pass. |
| `pull_request` | `PullRequestIdentity \| None` | Remains `None` until existing GitHub publish succeeds. |
| `attempt` / `failure_class` / `diagnostic` | Existing fields | Recovery budget and classification remain unchanged. |

`PLANNING_COMPLETE` is represented in two compatible ways:

1. A new full run appends a `StepRecord` with state `PLANNING_COMPLETE`,
   keeps the record active in implementation, and keeps the slot occupied.
2. A historical planning-only overlay may have record state
   `PLANNING_COMPLETE` and slot `free`. It is not PIV-complete and is eligible
   for strict handoff resume when the task is next selected.

Neither form is `COMPLETED` or `PR_CREATED`. A valid continuation uses the
same worktree, branch, plan/tasks paths, provider identity, and runtime
revision. An invalid handoff becomes visible failure/blocked before any
implementation, validation, or publish call.

## State transitions

```text
new/ready task
  -> QUEUED
  -> RUNNING / discovery (AiNative scout)
  -> RUNNING / plan (Spec Kit)
  -> RUNNING / tasks (Spec Kit)
  -> RUNNING / PLANNING_COMPLETE checkpoint
  -> RUNNING / implementation (Spec Kit)
  -> VALIDATING / existing checks
  -> RUNNING / github
  -> PR_CREATED

validation retryable
  -> RETRYABLE_FAILURE / diagnosis
  -> RETRYABLE_FAILURE / debug
  -> RUNNING / implementation (Spec Kit fix)
  -> VALIDATING

validation transient
  -> RETRYABLE_FAILURE
  -> VALIDATING

validation non-retryable
  -> BLOCKED

historical PLANNING_COMPLETE + valid handoff
  -> RUNNING / implementation

invalid saved handoff
  -> FAILED or BLOCKED
```

Questions at discovery, plan, tasks, implement, diagnosis, or validation
enter the existing `HUMAN_DECISION_REQUIRED` state. Publish is unreachable
until validation has passed.

## Handoff validation rules

Before continuing a saved planning record:

1. The task and project ids must match the current board and registry.
2. The saved workspace must equal
   `workspace_root/<project_id>/<task_id>`, be a valid worktree of the
   enrolled repository, and be on `feature/task-<task_id>`.
3. The active adapter identity and manifest revision must match the saved
   result exactly.
4. `.specify/integrations/speckit.manifest.json` must match the active
   provider, version, and revision.
5. `plan` and `tasks` must be readable regular files under the same worktree,
   with no symlink or secret-bearing path/content.
6. No implementation, validation, or publish call may occur if any rule
   fails.

## Safety invariants

- One active provider and one task worktree.
- No AiNative planner/builder lookup or write.
- No second task store, workspace, or canonical plan/task alias.
- No adapter-local retry loop.
- No transcript, private reasoning, token, or credential in artifacts,
  overlays, notices, pull requests, or version history.
- No push, PR create/update, merge, deploy, amend, force-push, or protected
  branch write before the existing post-validation GitHub step.
