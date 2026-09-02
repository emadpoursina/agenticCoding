# Quickstart: Agent Execution

**Feature**: `004-agent-execution`

Validation guide for the execute, role-mapping, model-assignment, context, and structured-result contract. Implementation lives in `personalAgent/` (existing control-plane package). Do not start PIV orchestration, GitHub push/PR, Telegram, or a live model account to run these checks.

Types and signatures: [data-model.md](./data-model.md), [contracts/agent-executor.md](./contracts/agent-executor.md). Methodology: [AiNative adapter contract](../../001-ainative-adapter/contracts/ainative-adapter.md). Eligibility and project context: [project registry contract](../../002-project-registry/contracts/project-registry.md). Workspaces: [workspace manager contract](../../003-workspace-manager/contracts/workspace-manager.md).

## Prerequisites

- Python 3.12 and uv (see `personalAgent/.python-version`)
- `git` on PATH
- This repo’s `personalAgent` checkout

A live managed project, a GitHub account, and a live model account are **not** required. Contract tests build disposable git repositories and a disposable methodology tree under pytest’s `tmp_path`, inject a stand-in `ModelService`, and call `prepare_workspace` **in the test** before `execute_*`. Production `config/default.yaml` MUST keep `projects: []` until the owner names a non-critical repo. Tests MUST NOT bind workspace or methodology paths to a hardcoded workstation layout, and MUST NOT require `OPENAI_API_KEY`.

## Setup

```bash
cd personalAgent
uv python install 3.12
uv sync --extra dev
```

Tests construct:

1. A temp methodology (copy `tests/fixtures/ainative/`, which includes fixture `scout`, `tester`, `specs-planner`, `builder`).
2. A temp enrolled git project (copy `tests/fixtures/projects/standard/`, `git init` + commit). Override validation commands in that copy when the check needs a cheap `true` / `false` / missing binary.
3. A temp `workspace.root` and operational YAML with role map + **test** model assignment strings (not production model names).
4. `WorkspaceManager.prepare_workspace` for a known task id, then `AgentExecutor(..., model_service=stand_in)`.

Docker already mounts `/ainative:ro` and `/workspaces`; application code reads **configured** paths, not host env substitutes.

## Run checks

```bash
cd personalAgent
uv run pytest tests/test_agent_executor.py
uv run ruff check src tests
```

Keep existing tests passing (`tests/test_import.py`, `tests/test_ainative_adapter.py`, `tests/test_project_registry.py`, `tests/test_workspace_manager.py`).

## Expected outcomes (SC-007)

The pytest file MUST fail if any of these break:

| Check | Passes when |
|---|---|
| Execute listed agent with full context from payload | Eligible fixture + prepared workspace + fixture `scout` returns a result; assembled context has non-empty task, project, workspace, methodology revision SHA, and scout definition; `worker_id` is `scout`; omitted previous outputs stay empty; supplied plan is present unchanged |
| Structured result shape | Result has explicit `success`/`failure`/`blocked`, summary, artifacts list, next-action, questions; no reasoning/transcript/secrets |
| Planning artifact in the isolated copy | Planning role writes `PLAN.md` in the worktree with all eight required sections and lists that path on `artifacts`; discovery succeeds without that file |
| Implementation changes only the isolated copy | Builder writes/commits only under the worktree on `feature/task-<id>`; enrolled location unchanged; 0 publishes |
| Validation status from project commands | Tester run invokes the enrolled manifest’s commands in the isolated copy; `validation`/`status` follow those exits, not stand-in prose; no invented generic checks |
| Refuse unknown/missing inputs | Unknown agent, ineligible project, missing workspace, missing role model assignment each raise a visible error; missing workspace does not create a copy |
| Refuse methodology write / publish | Model-requested write under methodology raises and methodology is unchanged; work branch is never `main`/`master`/default; executor performs 0 publishes |

Also required by the spec (same test file is fine):

- Path-like / reserved agent names → `UnknownAgentError`; no filesystem join of the raw name
- Unresolved agent dependencies → `UnresolvedDependencyError`; no partial run
- Role mapped to a name not in the fixture roster → `UnknownAgentError`
- Live client with empty env → `MissingModelCredentialsError`; stand-in without env still works
- Planning success without eight sections does not count as success
- Validation cannot-start → `blocked`; non-zero → `failure`

## Live run (optional, not required for the contract)

A real execute needs `model.roles.*` filled, `OPENAI_BASE_URL` / `OPENAI_API_KEY` (or the configured env names) set **outside git**, an enrolled project, and a prepared workspace. Missing secret/location MUST fail at execute rather than skipping the model. Do not point this at a production repository until the owner names a non-critical repo.

## Out of scope for this guide

Docker e2e, writing `kanban.db`, `git push`, pull requests, PIV chaining, Telegram, retry/debug, adding agents to live AiNative, and installing a planning framework into this control plane. Those wait for later specs.
