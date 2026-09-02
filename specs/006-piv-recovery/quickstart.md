# Quickstart: PIV Recovery

**Feature**: `006-piv-recovery`

Validation guide for classification, bounded diagnosis→debug→re-validate, `BLOCKED`, and A/B resume. Implementation stays in `personalAgent/`. Do not start GitHub push/PR, Telegram, a live model account, or native `kanban.db` writes to run these checks.

Types and signatures: [data-model.md](./data-model.md), [contracts/piv-orchestrator.md](./contracts/piv-orchestrator.md). Prior chain: [005 quickstart](../../005-piv-orchestrator/quickstart.md).

## Prerequisites

Same as 005: Python 3.12, uv, git, `personalAgent/` checkout. Live managed project, live `kanban.db`, GitHub, Telegram, and `OPENAI_API_KEY` are **not** required. `config/default.yaml` MUST keep `projects: []`. Tests MUST NOT bind host home paths.

## Setup

```bash
cd personalAgent
uv python install 3.12
uv sync --extra dev
```

Tests reuse 005 helpers: temp methodology (fixture `scout` / `specs-planner` / `builder` / `tester`), temp enrolled git project, `MemoryTaskBoard`, stand-in `ModelService`. For recover-to-complete, point project validation at a script **inside the workspace** that the debug stand-in can rewrite. For cannot-start, use a missing binary command. For TRANSIENT, subclass `AgentExecutor` to return `validation="blocked"`, `status="blocked"`, `next_action="retry"`.

## Run checks

```bash
cd personalAgent
uv run pytest tests/test_piv_orchestrator.py tests/test_agent_executor.py
uv run ruff check src tests
```

Keep 001–004 tests passing. The missing-binary executor case MUST now expect `validation="blocked"` and `status="failure"` (cannot-start encoding).

## Expected outcomes (SC-007)

The pytest file MUST fail if any of these break:

| Check | Passes when |
|---|---|
| Recover first validation fail to `COMPLETED` | Checks fail once, diagnosis runs (tester agent, **not** as validation-role checks), debug edits only the isolated copy, same declared checks pass, start returns `COMPLETED`, `attempt==2`, enrolled location unchanged, 0 publishes |
| Classify transient vs retryable vs non-retryable | `false` command → `RETRYABLE` then diagnosis; injected blocked+retry → `TRANSIENT` (0 diagnosis, 0 debug edits); missing binary → `NON_RETRYABLE` → `BLOCKED` with 0 diagnosis, 0 debug, attempt `1` |
| Three-cycle limit then `BLOCKED` | Always-fail checks: three recovery cycles then `BLOCKED`, `attempt==4`, no fourth automatic cycle |
| Abandon from `BLOCKED` | Resume `A` → `FAILED`, slot free, later start allowed (new run, attempt `1`) |
| Grant `B` | Last class retryable → one diagnosis→debug→validate; last class non-retryable → validate only (0 diagnosis, 0 debug) |
| Park/resume diagnosis or validation questions | Non-empty questions → `HUMAN_DECISION_REQUIRED`, attempt unchanged; resume listed letter re-runs that step; validation resume then classifies (not `FAILED` from the questions themselves) |
| Refuse second workflow while `BLOCKED` | Second `run_workflow` / `run_next_workflow` → `WorkflowBusyError`; first record unchanged |

Also required (same file is fine):

- Discovery / planning / original implementation failure still `FAILED`, attempt `1`, 0 diagnosis
- Implementation questions still `FAILED`
- Task body fields unchanged; secrets absent from record, diagnostic, and escalation brief
- Invalid blocked letter → `InvalidDecisionError`, still `BLOCKED`
- Resume when completed/failed → `ResumeNotParkedError`

## Live run (optional)

Same constraints as 005. Do not point at a production repository. Do not send Telegram. Do not push.

## Out of scope for this guide

Docker e2e, writing `kanban.db` retry columns, `git push`, pull requests, Telegram, adding agents to live AiNative, recovering discovery/planning/implementation failures.
