# Data Model: External Framework Planning Adapter

**Feature**: `011-external-framework-planning` | **Date**: 2026-09-07

The model extends the existing in-process Hermes records. It adds no task
database, Kanban row, or parallel control-plane state. Types remain frozen
dataclasses and public Python APIs remain type-annotated.

## Active external framework

**Entity**: one runtime-selected provider identity.

| Field | Type | Rules |
|---|---|---|
| `id` | `str` | Non-empty provider id. V0 exact value: `github-spec-kit`. |
| `version` | `str` | Non-empty pinned release version. V0 default/documented pin: `1.0.1`. |
| `active` | `bool` | Exactly one configured provider is `true` on the live path. |

Configuration shape:

```yaml
external_framework:
  providers:
    - id: github-spec-kit
      version: 1.0.1
      active: true
  runtime:
    path_env: HERMES_SPECKIT_RUNTIME
```

`path_env` is a non-empty environment-variable name, not a filesystem path
or secret. The referenced runtime directory must exist and contain a
matching manifest. Zero active providers, multiple active providers,
unsupported active ids, and empty pins fail at the live trust boundary.

## Framework runtime manifest

**Entity**: immutable identity for the preinstalled provider assets.

| Field | Type | Rules |
|---|---|---|
| `provider_id` | `str` | Must equal the active provider id. |
| `version` | `str` | Must equal the active pinned version exactly. |
| `revision` | `str` | Required exact release/source revision; no invented fallback. |
| `setup_root` | `Path` | Read-only source asset directory outside the task worktree. |

The manifest is read before any model call. Runtime setup assets are copied
from `setup_root` only into the prepared task worktree. The runtime source is
never modified.

## Framework context

**Entity**: stable input to one external-framework lifecycle step.

| Field | Type | Rules |
|---|---|---|
| `lifecycle_step` | `str` | Closed boundary names: `specify`, `clarify`, `plan`, `tasks`, `implement`; V0 executes only `plan`/`tasks`. |
| `task` | `BoardTask` | Complete task identity and structured goal from the existing board read model. |
| `project` | `ProjectContext` | Existing enrolled-project context; no invented fields. |
| `workspace_path` | `Path` | Existing prepared task worktree; resolved and validated. |
| `workspace_branch` | `str` | Existing non-protected feature branch. |
| `provider` | `FrameworkIdentity` | Same active identity for every external step in the run. |
| `framework_revision` | `str` | Revision read from the runtime manifest. |
| `model_assignment` | `str` | Existing configured Hermes model slot; no provider/model hardcoding. |
| `discovery_summary` | `str` | Safe summary from the completed AiNative `scout` step; no transcript. |
| `previous_artifacts` | `dict[str, Path]` | Validated native paths from an earlier provider step, e.g. `plan`. |
| `decision` | `str \| None` | Human-selected decision text, if resuming an existing Hermes question. |
| `framework_instructions` | `str` | Provider/runtime instructions supplied to the existing model service, not AiNative agent text. |
| `workspace_files` | `tuple[ContextFile, ...]` | Existing bounded read-only project snapshot. |

The context contains no credentials, private reasoning, raw model transcript,
or AiNative planner/builder definition.

## Native framework artifact

**Entity**: one framework-owned file passed to later Hermes steps.

| Field | Type | Rules |
|---|---|---|
| `kind` | `str` | Provider-defined stable key; V0 requires `plan` and `tasks`. |
| `path` | `Path` | Existing readable regular file under the same task worktree. |

The adapter records paths returned by the provider runtime. It does not
rename, copy, or mirror them to `PLAN.md` or `TASKS.md`. Setup files and any
native feature input remain in the same worktree, but only `plan` and `tasks`
are required success artifacts for this slice.

## Normalized framework result

**Entity**: safe result of one provider lifecycle step. The orchestrator
merges the successful `plan` and `tasks` results into the combined V0
planning result stored on the workflow record.

| Field | Type | Rules |
|---|---|---|
| `status` | `Literal["success", "failure", "blocked"]` | Explicit; no implicit success from partial files. |
| `artifacts` | `dict[str, Path]` | A step returns its native paths; the combined V0 success requires readable `plan` and `tasks`; all paths stay inside the worktree. |
| `questions` | `tuple[str, ...]` | Zero or more safe human questions; no private reasoning. |
| `next_action` | `str` | Safe operator/workflow action; may be empty. |
| `provider_id` | `str` | Active provider id. |
| `provider_version` | `str` | Active pinned version. |
| `framework_revision` | `str` | Exact runtime manifest revision used. |
| `summary` | `str` | Bounded operator-facing summary; never a transcript or secret. |

Failure or blocked results must not contain guessed artifact paths. A success
result with a missing, unreadable, fabricated, or escaping path is invalid
and is converted to visible failure before reaching later steps.

## Workflow record extension

The existing `WorkflowRecord` remains the operational source of truth in
`overlay.json`. Add:

| Field | Type | Rules |
|---|---|---|
| `external_result` | `ExternalFrameworkResult \| None` | Round-trips through the existing JSON overlay; optional for old snapshots and legacy fixture runs. |

Add the terminal state `PLANNING_COMPLETE` to the existing closed state
handling. It is terminal and writes `slot: free`, but is deliberately
different from `COMPLETED`/`PR_CREATED`. Its `validation_status` remains
`pending`, `pull_request` remains `None`, and no implementation or
validation step is recorded.

The planning step's `StepRecord` identifies the provider as its worker and
stores a safe summary/status. The normalized result preserves the native
artifact paths and provider identity for a later lifecycle feature.

## State transitions

```text
new task
  -> QUEUED
  -> RUNNING / discovery (AiNative scout)
  -> RUNNING / planning (external plan)
  -> RUNNING / planning (external tasks)
  -> PLANNING_COMPLETE (slot free)

external question -> HUMAN_DECISION_REQUIRED (existing resume path)
external failure  -> FAILED or BLOCKED (existing failure/decision path)
```

On resume from a question after a plan artifact exists, the orchestrator may
reuse that validated path and continue with `tasks`; otherwise it restarts
only the incomplete provider step. Existing retry budgets, overlay heartbeat,
and workspace recovery remain unchanged.

## Isolation and validation rules

1. `workspace_path` must be the prepared copy for the current project/task
   and must not be the enrolled project root.
2. Bootstrap destinations, native input, plan output, and task output must
   resolve below that worktree.
3. Runtime assets, AiNative, the control-plane repository, sibling worktrees,
   and the enrolled root are read-only/out of scope for provider writes.
4. The provider cannot return a path outside the worktree, a directory, or an
   unreadable file.
5. Secret values and private-key markers are rejected from result metadata;
   credentials remain environment/config inputs outside artifacts and state.
6. No result or workflow record carries model transcript text or private
   reasoning.
