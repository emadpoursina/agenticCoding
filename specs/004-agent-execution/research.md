# Research: Agent Execution

**Feature**: `004-agent-execution` | **Date**: 2026-08-30

Phase 0 resolves every Technical Context choice against the spec, constitution, V0 plan §18–20 / §55–56 / Phase 2, discovery, and the live `personalAgent` tree. No `[NEEDS CLARIFICATION]` remains.

## 1. Where the executor lives

**Decision**: One module in the existing control-plane package: `personalAgent/src/hermes_kanban/executor.py`. Re-export public types from `hermes_kanban/__init__.py`. Checks in `personalAgent/tests/test_agent_executor.py`. Fixture agents `specs-planner` and `builder` live under `personalAgent/tests/fixtures/ainative-full/docs/agents/` only.

**Rationale**: `src/hermes_kanban/` already holds `ainative.py`, `projects.py`, and `workspace.py`. Constitution III forbids a second control plane. Spec FR-016 / assumptions: reuse the existing package; do not add a second task store. One module until the file is no longer readable — do not pre-split into context/model/result files.

**Alternatives considered**:
- New top-level package `agent_executor/` — extra install surface, unused.
- `hermes_kanban/executor/` package with several modules — premature; this phase is one execute call.
- A Hermes skill instead of this package — would skip the in-process contract later workers need.
- Adding `builder` / `specs-planner` to live AiNative — forbidden (FR-016 edge case; methodology is not owned here).

## 2. Language, tooling, dependencies

**Decision**: Python 3.12 (`>=3.12,<3.14`) via uv. pytest + ruff already in `[project.optional-dependencies] dev`. **No new runtime dependencies.** Stdlib: `pathlib`, `dataclasses`, `subprocess`, `json`, `urllib.request`, `shlex`, `os`, `re`. Version-control operations use the `git` CLI already on PATH. Duplicate a small `_git` helper in `executor.py` for commit/status rather than extracting a shared git module.

**Rationale**: Constitution hard constraints. Spec assumption: no new third-party libraries. Asking a model MUST use capabilities already present (`urllib.request` + OpenAI-compatible env names already in `config/default.yaml`). `workspace.py` already decided not to share a git helper with `ainative.py`.

**Alternatives considered**:
- `openai` SDK / httpx / pydantic — new deps, owner did not approve.
- A shared `hermes_kanban/git.py` — extra layer; adapter/workspace/executor errors stay distinct.
- Adding the executor to the Hermes image — would fork Hermes (forbidden).

## 3. Public operations and trust boundary

**Decision**: `AgentExecutor` exposes exactly the spec names:

| Operation | Success when |
|---|---|
| `execute_agent(name, project_id, task_id, *, payload=None)` | Listed agent, eligible project, prepared workspace, model assignment present, one run, structured result |
| `execute_role(role, project_id, task_id, *, payload=None)` | Role is one of the four; mapped agent is listed; same gates as `execute_agent` |

`execute_role` resolves the agent name from operational configuration (defaults below) then calls the same path as `execute_agent`. An unknown role name fails before mapping. An unknown mapped agent name fails with existing `UnknownAgentError`.

Before the model is asked, execute MUST, in order:

1. Validate `task_id` identity (reuse workspace/registry path-like rules; empty/path-like → existing `InvalidTaskIdError`).
2. `registry.resolve_eligible_project(project_id)` then `load_project_context(project_id)`.
3. `workspaces.inspect_workspace(project_id, task_id)` — MUST NOT call `prepare_workspace`. Missing/invalid → `MissingWorkspaceError` (wraps inspect failure so the contract is a visible missing-workspace error). Dirty is allowed.
4. Refuse if the inspected branch is protected (`assert_publish_allowed`).
5. Load agent (`get_agent`) and `resolve_agent_dependencies` (existing errors, including unknown/reserved/path-like names).
6. `capture_revision` / `build_execution_context` with `workflow_phase` = the role (or `"agent"` when `execute_agent` was used without a role).
7. Resolve model assignment for the role (discovery uses planning). Missing/empty → `MissingModelAssignmentError`.
8. For a live model service: missing location or secret env value → `MissingModelCredentialsError`. A stand-in MUST NOT require credentials.

Any of those failures MUST fail execute with that visible error and MUST NOT create a working copy, publish, or write methodology.

**Rationale**: FR-001–FR-004, FR-011–FR-012, FR-017, US3.

**Alternatives considered**:
- Calling `prepare_workspace` when inspect fails — forbidden (FR-001).
- Returning `None` or a `blocked` result for missing workspace — weaker than distinct errors used elsewhere.
- Loading task fields from `kanban.db` — this phase does not read the host task store.

## 4. Role mapping and workflow identity

**Decision**: Load from caller-supplied operational YAML. Defaults when a role key is omitted:

| Role | Default agent |
|---|---|
| `discovery` | `scout` |
| `planning` | `specs-planner` |
| `implementation` | `builder` |
| `validation` | `tester` |

An operator MAY remap any role to any listed agent name. Construction does not require the `roles:` block. Execute still fails if the mapped name is not in the methodology roster (`UnknownAgentError`).

Workflow name on context: `workflow.default` from the same YAML, default `piv` when omitted (already the production value). Phase on context: the role being executed. `execute_agent` without a role uses phase `"agent"` and the **planning** model assignment unless the caller used `execute_role`.

**Rationale**: FR-002, spec assumptions on defaults and live-tree gaps. Checks use a fixture roster that includes all four names so unknown-agent is a deliberate remap test, not the happy path.

**Alternatives considered**:
- Failing construction when `roles:` is absent — would break production `default.yaml` which has no such block yet; defaults cover it.
- Adding the missing folders to live AiNative — forbidden.
- Mapping `execute_agent("scout")` through discovery automatically — spec keeps name and role as separate entry points.

## 5. Model assignment and the model service seam

**Decision**: Per-role model id strings live in operational config (`model.roles.planning`, `implementation`, `validation`). Discovery uses the planning slot. Debugging is not read this phase. Agent documents are never parsed for provider/model names.

Two implementations of one Protocol:

```text
ModelService.complete(assignment, context) -> ModelResponse
```

1. **Stand-in** (required for checks): a test double that returns a predetermined `ModelResponse`. No network. No env.
2. **Live** (optional): stdlib `urllib.request` POST to `{base_url}/v1/chat/completions` using env vars named by `model.openai_compatible.base_url_env` / `api_key_env` (already `OPENAI_BASE_URL` / `OPENAI_API_KEY`). The request content is the assembled context rendered as JSON plus agent instruction text. The model MUST return a JSON object matching `ModelResponse`. Parse failure → result `status=failure`, not an invented success.

`from_config` builds the live client when `model_service` is omitted. Checks always inject the stand-in.

Missing role model id → fail at execute, do not invent. Missing live base URL or API key when the live client would be used → fail at execute. Stand-in runs MUST succeed without those env vars.

Tag the result with the role’s model id (`model_assignment`), never with the secret, never with a name copied from agent Markdown.

**Rationale**: FR-011–FR-013, constitution “model routing is configured inside Hermes”, discovery “optional OpenAI-compatible override”, V0 §19–20. Hermes-native routing remains the operator’s source of truth; this package reads the same style of config rather than spawning a Hermes worker this phase (no running gateway required for contract checks).

`ponytail:` single-shot chat completion, no tool loop, no streaming. Ceiling: implementation can only change files the model listed in `ModelResponse.files`. Upgrade: Hermes-native tool-using worker when Phase 3 orchestration needs iterative edits.

**Alternatives considered**:
- Hardcoding OpenRouter / 9router / a model id — forbidden.
- Calling the Hermes gateway from pytest — requires a live daemon and couples the contract to gateway JSON.
- A ReAct / function-call loop — extra code, not required to prove one execute.
- Skipping the model on validation — US3 requires the validation role to use its assignment; status still comes from commands.

## 6. Execute payload and assembled context

**Decision**: Optional `ExecutePayload` on the same call:

| Slot | Rule |
|---|---|
| `title`, `description`, `acceptance_criteria`, `priority` | Optional. Omitted → empty on context. MUST NOT invent. MUST NOT read Kanban. |
| `plan`, `validation` | Previous-step outputs. Omitted → absent on context (`None`). Passed through unchanged. |

`task.id` is the `task_id` argument and MUST match the prepared workspace’s task identity (already implied by inspect).

`AssembledContext` is a new dataclass (do not break the methodology-only `ExecutionContext` from Phase 1). It includes:

- task id + optional payload fields
- project id, name, repository, default branch
- full `ProjectContext` from `load_project_context`
- workspace path and branch from inspect
- methodology path + `Revision` (non-empty `sha`)
- workflow name + phase
- `AgentDefinition` + resolved `AgentDependency` list (same contents `resolve_agent_dependencies` already returns)
- previous `plan` / `validation` only when supplied
- `model_assignment` (the configured id string)

Reuse `get_agent`, `resolve_agent_dependencies`, `build_execution_context`, `load_project_context`, `inspect_workspace`. Do not duplicate discovery, context load, or Git safety.

**Rationale**: FR-005, FR-006, US1. Extending `ExecutionContext` in place would mix methodology identity with task/workspace and break the 001 contract tests’ “must not invent task metadata” shape.

**Alternatives considered**:
- Mutating `ExecutionContext` — breaking change to Phase 1.
- Reading task title from `kanban.db` — out of scope.
- Copying methodology files into the workspace — forbidden (FR-014).

## 7. Structured result

**Decision**: Every execute returns `ExecuteResult`:

| Field | Rule |
|---|---|
| `status` | `success` \| `failure` \| `blocked` — explicit enum/literal, never inferred only from `summary` |
| `summary` | Short string from the model response (may be empty on boundary failures that raise instead) |
| `artifacts` | Tuple of paths; empty if none |
| `next_action` | String or `None` |
| `questions` | Tuple of strings; empty if none |
| `identity` | Prepare correlation fields from inspect/prepare record: `task_id`, `execution_id`, `project_id`, `workspace_id`, `worker_id` = the agent that ran |
| `model_assignment` | Role’s configured model id |
| `validation` | Present only for the validation role: `pass` \| `fail` \| `blocked` from command outcomes |

Boundary failures **raise** (same pattern as registry/workspace). A completed run that asked the model returns a result even when `status` is `failure` or `blocked`.

MUST NOT include private reasoning, chain-of-thought, model transcript text, or secrets.

`worker_id` is the agent name (`scout`, …), not a Hermes worker PID.

Inspect does not currently return `execution_id` / `workspace_id`. **Decision**: derive `workspace_id` as `ws-{project_id}-{task_id}` (same formula as prepare). For `execution_id`, generate a new UUID hex per successful execute (this run), distinct from prepare’s id. Document on the result that `execution_id` identifies **this execute**, not the prepare. Callers still correlate via `workspace_id` + `task_id` + `project_id`.

**Rationale**: FR-007, V0 §55, US2. Prepare’s `execution_id` is not stored on disk (Phase 1 research: no sidecar). Inventing a prepare id we no longer have would lie. A per-execute id is honest and still unique.

**Alternatives considered**:
- Requiring the caller to pass the prepare record into execute — extra API surface the spec did not add.
- Writing a sidecar identity file — dirties the copy; Phase 1 rejected it.
- Putting status only in `summary` — forbidden.

## 8. Planning artifact

**Decision**: A successful planning-role run writes `{workspace}/PLAN.md` (isolated copy root) and lists that absolute path on `result.artifacts`. The file MUST contain these headings (ATX `## `, case-insensitive match after stripping punctuation/whitespace for the check):

1. Problem understanding
2. Scope
3. Likely affected parts
4. Implementation approach
5. Acceptance-criteria mapping
6. Validation strategy
7. Risks
8. Open questions

The model (or stand-in) supplies the Markdown body. The executor writes the file and verifies sections. Claimed success without all eight → `status=failure` (file may still exist; do not treat as success). Discovery MUST NOT be required to produce this file.

Planner how-to text that mentions an external planning framework is passed through as document text. The control plane MUST NOT install that framework.

**Rationale**: FR-008, FR-015, clarification that only planning writes the eight-section plan. Root `PLAN.md` needs no extra directories.

**Alternatives considered**:
- `.hermes/plan.md` — extra folder in the project tree.
- Requiring discovery to write the same artifact — clarification says no.
- Rewriting specs.md FIRE steps into executor code — forbidden.

## 9. Implementation: files, local commit, isolation

**Decision**: `ModelResponse.files` is a map of **workspace-relative** paths → UTF-8 content. The executor applies writes only after resolving each path and confirming:

- the resolved path is inside the isolated working copy
- the resolved path is **not** inside the methodology location
- the resolved path is **not** the enrolled project location

Violation → `ReadOnlyError` (methodology) or `UnsafeWorkspaceWriteError` (escape / enrolled tree); no partial publish. Apply remaining files only after the full path check (all-or-nothing).

Optional `ModelResponse.commit` (bool). If true, after writes: `assert_publish_allowed(inspect.branch, default_branch=...)`, then `git add -A` and `git commit` **in the isolated copy only**. Commit MUST NOT run in the enrolled location. Forbidden in this module: `push`, `reset --hard`, `clean`, `clone`, merge, checkout of enrolled HEAD.

The enrolled project location MUST remain unchanged (same HEAD, same branch, no new files). Methodology MUST remain unchanged.

Dirty copies are valid inputs; implementation is expected to leave changes. This feature does not call prepare.

**Rationale**: FR-009, FR-014, US2/US3, clarification that local commit is allowed.

**Alternatives considered**:
- Letting the model shell out freely — no isolation guarantee.
- Applying patches with `git apply` only — extra format; whole-file writes are enough for the stand-in and the single-shot ceiling.
- Auto-push after commit — hosting is a later phase; executor never publishes.

## 10. Validation from project commands

**Decision**: For `validation` role, after context assembly and after the model assignment gate, run `ProjectContext.validation_commands` in order with `cwd` = isolated working copy path, `shlex.split` each command string, `subprocess.run` (no `shell=True`). Do not invent commands. Empty/missing commands already fail at `load_project_context` (`MissingProjectConfigurationError`).

| Command outcome | `validation` field | `result.status` |
|---|---|---|
| All exit 0 | `pass` | `success` |
| First executable missing / cannot start | `blocked` | `blocked` |
| First non-zero exit | `fail` | `failure` |

Stop at the first non-success. Capture stdout/stderr only for feeding the model summary prompt; do not put full transcripts on the result.

Still call `ModelService.complete` with the command outcomes in context so the validation role uses its model assignment (summary/questions). **Overwrite** any status the model claimed with the command-derived values.

`ponytail:` no subprocess timeout. Upgrade: bounded timeout when a project check hangs.

**Rationale**: FR-010, clarification that status is not model prose, US2 scenario 4.

**Alternatives considered**:
- Inferring pass/fail from model text — forbidden.
- Running commands in the enrolled location — would mutate the wrong tree.
- `shell=True` — avoid; `shlex.split` is enough for the fixture `uv run pytest`.

## 11. Configuration loading

**Decision**: `ExecutionSettings.from_config(config_path)` reuses `projects._parse_document` (already a nested YAML subset used by the registry). Read only:

- `workflow.default` (optional, default `piv`)
- `roles.*` (optional, apply table defaults)
- `model.roles.{planning,implementation,validation}` (required at execute, not at construction)
- `model.openai_compatible.base_url_env` / `api_key_env` (optional until a live client is used)

Other keys ignored. Do not default model ids. Do not read `WORKSPACE_ROOT` / `AINATIVE_PATH` / developer home as substitutes. Do not put live model name literals in `executor.py` or in production `default.yaml` as required values.

**Rationale**: In-repo reuse of the existing subset parser (workspace already imports `_path_like_id` from `projects`). Construction of the executor still requires valid adapter + registry + workspace root (those classes validate themselves).

**Alternatives considered**:
- A third line-oriented scanner — worse for nested `model.roles`.
- PyYAML — new dependency.
- Requiring model ids in production config now — would force invented names; fail at execute instead.

## 12. Errors

**Decision**: Distinct exception types, all subclasses of `ExecutorError`. Existing adapter / registry / workspace errors propagate unchanged except missing workspace (mapped to `MissingWorkspaceError`).

| Type | When |
|---|---|
| `UnknownRoleError` | Role not in `{discovery, planning, implementation, validation}` |
| `MissingWorkspaceError` | Inspect failed (missing or invalid copy). MUST NOT prepare |
| `MissingModelAssignmentError` | Role’s model id missing or empty |
| `MissingModelCredentialsError` | Live client selected and base URL or API key env is missing/empty |
| `InvalidExecutePayloadError` | Payload present but malformed (wrong types); optional |
| `UnsafeWorkspaceWriteError` | Model-requested path escapes the isolated copy or targets the enrolled tree |
| `ExecutorError` | Base |

Reuse: `UnknownAgentError`, `UnresolvedDependencyError`, `IncompleteAgentError`, `ReadOnlyError`, `UnknownProjectError`, `DisabledProjectError`, `InvalidProjectLocationError`, `MissingProjectConfigurationError`, `InvalidTaskIdError`, `ProtectedBranchError`, `InvalidWorkspaceError` (only if not wrapped).

**Rationale**: Spec wants visible, distinct failures. Tests assert types.

**Alternatives considered**: One `ExecutorError` with a code enum — worse call-site checks. Swallowing registry errors — would hide unknown vs disabled vs bad location.

## 13. Checks and fixtures

**Decision**: One pytest file covering the seven SC-007 contract behaviors plus: payload omit vs supply, discovery without `PLAN.md`, remap to unknown agent, missing model assignment, missing credentials on live client, methodology write refuse, missing workspace does not prepare, enrolled location unchanged, no publish, validation from fixture commands, planning sections required for success, `worker_id` equals agent name, secrets absent from result.

Fixture methodology: copy existing `tests/fixtures/ainative-full/`, whose current agent root is `docs/agents/` and already includes `specs-planner/` and `builder/` (minimal AGENTS.md + SKILL.md). Do not modify live AiNative.

Fixture project: existing `tests/fixtures/projects/standard/` git-inited in `tmp_path`; prepare via `WorkspaceManager` **in the test**, then execute. Validation command in the fixture is `uv run pytest` — tests MAY override the enrolled copy’s manifest to a cheap command (`true` / `false` / missing binary) so the contract does not require the fixture to be a Python package.

Stand-in model: in-test class. Production `projects: []` unchanged. Tests MUST NOT use a live production checkout or a live model account.

**Rationale**: Constitution IV; spec SC-007; V0 disposable fixture.

**Alternatives considered**: Only Docker e2e — slower, not required. Hitting OpenRouter in CI — forbidden by FR-013.
