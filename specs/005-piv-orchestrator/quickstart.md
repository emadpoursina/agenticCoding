# Quickstart: PIV Orchestrator

**Feature**: `005-piv-orchestrator`

Validation guide for the plan → implement → validate chain, execution-state overlay, human-decision pause/resume, and one-at-a-time next-ready selection. Implementation lives in `personalAgent/` (existing control-plane package). Do not start GitHub push/PR, Telegram, retry/debug, or a live model account to run these checks.

Types and signatures: [data-model.md](./data-model.md), [contracts/piv-orchestrator.md](./contracts/piv-orchestrator.md). Execute: [agent executor contract](../../004-agent-execution/contracts/agent-executor.md). Workspaces: [workspace manager contract](../../003-workspace-manager/contracts/workspace-manager.md). Eligibility: [project registry contract](../../002-project-registry/contracts/project-registry.md). Methodology: [AiNative adapter contract](../../001-ainative-adapter/contracts/ainative-adapter.md).

## Prerequisites

- Python 3.12 and uv (see `personalAgent/.python-version`)
- `git` on PATH
- This repo’s `personalAgent` checkout

A live managed project, a live `kanban.db`, a GitHub account, Telegram, and a live model account are **not** required. Contract tests build disposable git repositories and a disposable methodology tree under pytest’s `tmp_path`, inject a stand-in `ModelService` and a `MemoryTaskBoard`, and let the orchestrator call `prepare_workspace`. Production `config/default.yaml` MUST keep `projects: []` until the owner names a non-critical repo. Tests MUST NOT bind workspace or methodology paths to a hardcoded workstation layout, and MUST NOT require `OPENAI_API_KEY`.

## Setup

```bash
cd personalAgent
uv python install 3.12
uv sync --extra dev
```

Tests construct:

1. A temp methodology (copy `tests/fixtures/ainative-full/`, whose current agent root is `docs/agents/` and includes fixture `scout`, `specs-planner`, `builder`, and `tester`).
2. A temp enrolled git project (copy `tests/fixtures/projects/standard/`, `git init` + commit). Override validation commands in that copy when the check needs a cheap `true` / `false`.
3. A temp `workspace.root` and operational YAML with role map + **test** model assignment strings (not production model names).
4. A `MemoryTaskBoard` with fixture tasks (identity, project, problem, expected result, acceptance criteria, priority, `created_at`, optional dependencies).
5. `PivOrchestrator.from_config(..., model_service=stand_in, task_board=board)`.

Docker already mounts `/ainative:ro` and `/workspaces`; application code reads **configured** paths, not host env substitutes.

## Run checks

```bash
cd personalAgent
uv run pytest tests/test_piv_orchestrator.py
uv run ruff check src tests
```

Keep existing tests passing (`tests/test_import.py`, `tests/test_ainative_adapter.py`, `tests/test_project_registry.py`, `tests/test_workspace_manager.py`, `tests/test_agent_executor.py`).

## Expected outcomes (SC-007)

The pytest file MUST fail if any of these break:

| Check | Passes when |
|---|---|
| Full chain to `COMPLETED` | Eligible fixture + board task `123`; start waits and returns `COMPLETED` after discovery → planning (`PLAN.md` with eight sections) → implementation (isolated copy only) → validation pass from project commands; no plan-approval stop; enrolled location unchanged; 0 publishes |
| Auto-continue after planning | Planning success with empty questions starts implementation on the same call; `next_action` is never `wait for plan approval` |
| Park on questions | Planning (or discovery) questions list of two strings → `HUMAN_DECISION_REQUIRED`; options labeled `A`/`B`; implementation files unchanged after planning; decision brief uses the step summary as decision text |
| Resume with a listed letter | Resume `A` re-runs planning with `A` and option text available; empty questions on that re-run auto-continues through validation; attempt stays `1`. Unknown letter / option text / empty → boundary error, still parked |
| Fail validation without retry | Validation commands fail → `FAILED`, `validation_status=fail`, next action is not `retry`, implementation is not re-run, attempt `1` |
| Refuse a second active workflow | Parked (or reentrant stand-in during `RUNNING`) second `run_workflow` / `run_next_workflow` raises `WorkflowBusyError`; first record unchanged |
| Next ready by priority across projects | Board with unmet-dependency task, older lower-priority ready task, newer higher-priority ready task on another eligible project → higher-priority task starts. Empty/unready board → `NoReadyTaskError`, no agent run |

Also required by the spec (same test file is fine):

- Named start loads problem / expected result / AC / priority from the board (caller does not paste them)
- Named start with missing/invalid priority or unmet deps fails at the boundary; discovery does not run
- Task body owner/reviewer/priority/problem/expected-result/AC unchanged after state changes
- Resume when not parked → `ResumeNotParkedError`; completed/failed slot can start a new workflow
- Dirty copy at start → `DirtyWorkspaceError`; files not discarded
- Secrets absent from the workflow record and decision brief
- `steps` on the returned record includes `QUEUED` then running phases then terminal state

## Live run (optional, not required for the contract)

A real chain needs `model.roles.*` filled, `OPENAI_BASE_URL` / `OPENAI_API_KEY` (or the configured env names) set **outside git**, an enrolled project, and a `TaskBoard` wired to the isolated Hermes `kanban.db` (not implemented in this phase’s checks). Missing secret/location MUST fail at execute rather than skipping the model. Do not point this at a production repository until the owner names a non-critical repo. Do not send Telegram. Do not push.

## Out of scope for this guide

Docker e2e, writing `kanban.db`, `git push`, pull requests, Telegram, retry/debug, adding agents to live AiNative, and installing a planning framework into this control plane. Those wait for later specs.
