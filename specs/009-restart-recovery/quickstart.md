# Quickstart: Restart Recovery

Validation guide for overlay persistence, automatic reclaim, workspace recover, and duplicate prevention. Implementation stays in `personalAgent/`. Do not require Docker kill, a live model, `kanban.db` writes, github.com, or Telegram to run the pytest contract.

## Prerequisites

Same as 008: Python 3.12, uv, git, `personalAgent/` checkout. Live managed project, live `kanban.db`, github.com, Telegram, and `OPENAI_API_KEY` are **not** required. `config/default.yaml` MUST keep `projects: []` and MUST set `execution.overlay_dir` to a container path (not `$HOME`). Tests MUST NOT bind host home paths.

## Setup

```bash
cd personalAgent
uv sync --extra dev
```

## Contract checks

```bash
uv run pytest tests/test_restart_recovery.py
uv run pytest tests/test_piv_orchestrator.py tests/test_workspace_manager.py tests/test_telegram_messaging.py tests/test_agent_executor.py
uv run ruff check src tests
```

Expected: all pass. Existing 003–008 behaviour unchanged except `from_config` now requires a valid `execution.overlay_dir` and calls `become_ready`.

## Scenarios (map to spec)

Use stand-in model, `MemoryTaskBoard`, `MemoryGitHost`, temp workspace root, temp overlay dir, injected clock. Restart = new orchestrator on the same directories.

1. **Readable snapshot** — Start a fixture run; persist while `RUNNING`/`VALIDATING`; new process; same `execution_id` / task / project / workspace ids; record not empty or mixed ([data-model.md](./data-model.md) overlay snapshot).
2. **Terminal / parked unchanged** — Snapshot `PR_CREATED` or `FAILED`: no automatic worker. Snapshot `HUMAN_DECISION_REQUIRED` or `BLOCKED`: slot occupied, no worker until existing letter resume.
3. **One worker** — Interrupt during implementation; `become_ready` continues or safe-restarts that phase; second `run_workflow` → `WorkflowBusyError`; no second `execution_id`; no second working copy.
4. **Resume vs safe-restart** — Completed phase in snapshot → next phase runs. In-progress phase → that phase runs once; `attempt` unchanged.
5. **Automatic start-up** — `from_config` / `become_ready` reclaims before a new start is accepted; 0 Resume calls.
6. **Two copies** — Fresh `alive` → second `become_ready` raises `SlotHeldError`. Clock +61s silence → reclaim allowed.
7. **Dirty copy** — Uncommitted files in the task copy survive; reclaim uses that path; other task copies untouched.
8. **Missing copy, local branch** — Recreate worktree on `feature/task-<id>` with the same `workspace_id`; never `main`/`master`/default.
9. **Missing copy and branch** — `BLOCKED`; no hang; no foreign copy adopted.
10. **Offline** — No fetch; local copy continues. Branch only on remote → `BLOCKED`.
11. **Publish** — Interrupt during `github`; same execution; 0 second PRs from the restart alone ([008/007 contracts](../008-telegram/contracts/telegram-messaging.md)).
12. **Board body** — Owner, reviewer, priority, problem / expected-result / AC unchanged.

Details: [contracts/restart-recovery.md](./contracts/restart-recovery.md).

## Optional later proof (not this phase)

Compose volume on `execution.overlay_dir`, start a run, `docker compose restart`, confirm one worker. That is Phase 8 / operator proof, not the pytest gate.

## Out of scope

Phase 4 classification rewrite, Phase 8 full E2E, writing `kanban.db`, new Telegram kinds, merge, concurrent workers, adding agents to live AiNative.
