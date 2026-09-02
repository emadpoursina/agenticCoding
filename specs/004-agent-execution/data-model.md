# Data Model: Agent Execution

**Feature**: `004-agent-execution` | **Date**: 2026-08-30

In-process Python types (dataclasses). No database. Working copies remain git worktrees from Phase 1. Identity on the result is a correlation record for this execute, not a second store.

## Settings (trust-boundary input)

**Entity**: `ExecutionSettings`

Loaded from a caller-supplied operational YAML path. Other config keys are ignored here (`projects:`, `ainative:`, `workspace:` are read by their own loaders).

| Field | Type | Rules |
|---|---|---|
| `workflow_name` | `str` | From `workflow.default`. Default `piv` when omitted. Non-empty. |
| `role_agents` | `dict[Role, str]` | Four keys after defaults applied. Values are agent folder names, not paths. |
| `model_roles` | `dict[str, str]` | Keys `planning`, `implementation`, `validation`. Values may be empty at construction; empty at execute → `MissingModelAssignmentError`. |
| `base_url_env` | `str \| None` | Env **name** for live OpenAI-compatible base URL. |
| `api_key_env` | `str \| None` | Env **name** for live API key. |

**Validation**: File unreadable → construction fails with `ExecutorError` (or reuse a config error). Do not substitute host paths or model ids. Role names other than the four are not stored.

**Defaults for `role_agents`**: discovery→`scout`, planning→`specs-planner`, implementation→`builder`, validation→`tester`.

## Role

**Entity**: role name (closed set)

| Value | Maps to (default) | Model slot | Plan artifact required |
|---|---|---|---|
| `discovery` | `scout` | planning | No |
| `planning` | `specs-planner` | planning | Yes (`PLAN.md`) |
| `implementation` | `builder` | implementation | No |
| `validation` | `tester` | validation | No |

Unknown role → `UnknownRoleError`. Mapped agent not in roster → `UnknownAgentError` (existing).

## Execute payload

**Entity**: `ExecutePayload`

Optional structured input on `execute_agent` / `execute_role`. Not loaded from the host task store.

| Field | Type | Rules |
|---|---|---|
| `title` | `str \| None` | Optional. Empty/omitted stays empty. |
| `description` | `str \| None` | Optional. |
| `acceptance_criteria` | `str \| None` | Optional. |
| `priority` | `str \| None` | Optional. Not validated against a Kanban enum this phase. |
| `plan` | `str \| None` | Previous-step plan text. `None` if omitted. MUST NOT be invented. |
| `validation` | `str \| None` | Previous-step validation text. `None` if omitted. MUST NOT be invented. |

**Identity**: `task_id` is a required argument on execute, not a payload field. It MUST be the same identity used to prepare the workspace.

## Task slice (on assembled context)

| Field | Type | Rules |
|---|---|---|
| `id` | `str` | Required. Same as execute `task_id`. Not path-like. |
| `title` | `str` | From payload or `""`. |
| `description` | `str` | From payload or `""`. |
| `acceptance_criteria` | `str` | From payload or `""`. |
| `priority` | `str` | From payload or `""`. |

## Assembled context

**Entity**: `AssembledContext`

The bundle given to `ModelService.complete`. Not a transcript. Not persisted.

| Field | Type | Rules |
|---|---|---|
| `task` | task slice | `id` non-empty; optional fields as above. |
| `project_id` | `str` | Enrolled id after `resolve_eligible_project`. |
| `project_name` | `str` | From loaded `ProjectContext.name`. |
| `repository` | `str` | From `ProjectContext.repository`. |
| `default_branch` | `str` | From `ProjectContext.default_branch`. |
| `project_context` | `ProjectContext` | Existing type; already-loaded project files and `validation_commands`. |
| `workspace_path` | `Path` | Isolated copy from inspect. Absolute. |
| `workspace_branch` | `str` | Current branch; not protected. |
| `methodology_path` | `Path` | Configured AiNative path. |
| `revision` | `Revision` | Existing type; `sha` non-empty. |
| `workflow_name` | `str` | From settings. |
| `workflow_phase` | `str` | Role, or `"agent"` for bare `execute_agent`. |
| `agent` | `AgentDefinition` | Existing type. |
| `dependencies` | `tuple[AgentDependency, ...]` | Same contents as `resolve_agent_dependencies`. |
| `previous_plan` | `str \| None` | Payload `plan` or `None`. |
| `previous_validation` | `str \| None` | Payload `validation` or `None`. |
| `model_assignment` | `str` | Role’s configured model id. Never a secret. Never from agent documents. |

**Forbidden contents**: private reasoning, API keys, full model transcripts.

**Relationships**: One context per execute. Methodology documents are referenced in place (definition + dependency text already loaded by the adapter), not copied onto disk in the workspace.

## Model assignment

**Entity**: configured model id for one role

| Field | Type | Rules |
|---|---|---|
| `role_slot` | `planning` \| `implementation` \| `validation` | Discovery uses `planning`. |
| `model_id` | `str` | Non-empty at execute. Configuration value, not a code literal. |

Secrets are env values named by settings, never fields on this entity.

## Model response (service → executor)

**Entity**: `ModelResponse`

Closed structured object. The live client parses model JSON into this type. The stand-in returns it directly.

| Field | Type | Rules |
|---|---|---|
| `summary` | `str` | Short public summary. |
| `files` | `dict[str, str]` | Workspace-relative paths → file contents. Empty if none. |
| `commit` | `bool` | If true, executor may create a local commit after applying files. Ignored unless implementation role. |
| `plan_markdown` | `str \| None` | Planning body. Executor writes `PLAN.md`. |
| `next_action` | `str \| None` | |
| `questions` | `tuple[str, ...]` | Empty if none. |
| `status` | `str \| None` | **Ignored** for validation (commands win). For other roles MAY inform executor status only if it is one of `success`/`failure`/`blocked`; invalid/omitted → `success` when writes/plan checks pass, else `failure`. |

No chain-of-thought field.

## Plan artifact

**Entity**: Markdown file in the isolated working copy

| Field | Type | Rules |
|---|---|---|
| `path` | `Path` | `{workspace_path}/PLAN.md`. Listed on `result.artifacts` on planning success. |
| `body` | `str` | Must contain eight `## ` sections: Problem understanding; Scope; Likely affected parts; Implementation approach; Acceptance-criteria mapping; Validation strategy; Risks; Open questions. |

**State**: Created only by a planning-role run. Discovery success does not require this file. Missing sections on a would-be success → `ExecuteResult.status=failure`.

## Structured result

**Entity**: `ExecuteResult`

| Field | Type | Rules |
|---|---|---|
| `status` | `success` \| `failure` \| `blocked` | Explicit. Not inferred only from `summary`. |
| `summary` | `str` | Public. No secrets. |
| `artifacts` | `tuple[Path, ...]` | Empty if none. Planning success includes `PLAN.md`. |
| `next_action` | `str \| None` | |
| `questions` | `tuple[str, ...]` | Empty if none. This phase does not pause or notify. |
| `identity` | `CorrelationIdentity` | `worker_id` set to the agent that ran. `workspace_id` = `ws-{project_id}-{task_id}`. `execution_id` = new UUID hex for **this execute**. |
| `model_assignment` | `str` | Role’s model id. |
| `validation` | `pass` \| `fail` \| `blocked` \| omitted | Present only for validation role. From command outcomes. |

**Forbidden contents**: private reasoning, model transcript, API keys, env values.

## Validation outcome

**Entity**: command-derived status (not a stored row)

Run `ProjectContext.validation_commands` in the isolated copy.

| Commands | `validation` | `status` |
|---|---|---|
| All exit 0 | `pass` | `success` |
| Cannot start | `blocked` | `blocked` |
| Non-zero exit | `fail` | `failure` |

## Correlation identity (reuse)

**Entity**: existing `CorrelationIdentity` from `workspace.py`

| Field | This phase |
|---|---|
| `task_id` | Execute argument |
| `execution_id` | New per execute (not the prepare id, which is not on disk) |
| `project_id` | Enrolled id |
| `workspace_id` | `ws-{project_id}-{task_id}` |
| `worker_id` | Agent name that ran |

## Relationships

```text
config YAML  -->  ExecutionSettings
AiNativeAdapter.get_agent / resolve / revision
ProjectRegistry.resolve_eligible_project + load_project_context
WorkspaceManager.inspect_workspace
ExecutePayload (optional)
    -->  AssembledContext
    -->  ModelService.complete
    -->  ModelResponse
    -->  writes/commit in isolated copy (implementation)
    -->  PLAN.md (planning)
    -->  validation commands (validation)
    -->  ExecuteResult
```

- One executor instance per constructed adapter + registry + workspace manager + settings + model service.
- One assembled context and one result per execute call.
- Methodology and enrolled project location are never write targets.

## State transitions

Execute is not a workflow. There is no stored phase machine this phase.

| Run | Workspace after | Result |
|---|---|---|
| discovery | unchanged except what the model wrote (usually none) | structured result; `PLAN.md` not required |
| planning | `PLAN.md` present on success | artifacts lists that path |
| implementation | files and optional local commit on work branch | enrolled tree unchanged |
| validation | no publish; commands ran in copy | `validation` field set from exits |

Boundary errors raise and leave the workspace as inspect found it (except they never create it).
