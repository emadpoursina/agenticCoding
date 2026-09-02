# Quickstart: Telegram Integration

**Feature**: `008-telegram`

Validation guide for meaningful orchestration events on the existing messaging connection, status answers from overlay, and chat resume into `resume_workflow`. Implementation stays in `personalAgent/`. Do not start a live bot, a second transport, or native `kanban.db` writes to run the pytest contract.

Types and signatures: [data-model.md](./data-model.md), [contracts/telegram-messaging.md](./contracts/telegram-messaging.md). Prior chain: [007 quickstart](../../007-github-integration/quickstart.md).

## Prerequisites

Same as 007: Python 3.12, uv, git, `personalAgent/` checkout. Live Telegram account, live `kanban.db`, github.com, and `OPENAI_API_KEY` are **not** required for pytest. `config/default.yaml` MUST keep `projects: []` for production defaults. Tests MUST NOT bind host home paths or call Telegram.

## Setup

```bash
cd personalAgent
uv python install 3.12
uv sync --extra dev
```

Tests reuse 007 helpers plus `MemoryMessagingChannel`: temp methodology, temp enrolled git project, `MemoryTaskBoard`, stand-in `ModelService`, `MemoryGitHost`. Drive fixture runs through start, park, recovery-start, recovery still-fail, blocked, publish, unexpected fail, and abandon. Simulate send failure by making the memory channel raise or return failure for the first N attempts.

## Run checks

```bash
cd personalAgent
uv run pytest tests/test_telegram_messaging.py tests/test_github_publish.py tests/test_piv_orchestrator.py tests/test_agent_executor.py
uv run ruff check src tests
```

Keep 001–007 tests passing. Tests that omit `messaging` MUST still wait-return as 007 (skip-send, 0 required events in a memory log).

## Expected outcomes

`tests/test_telegram_messaging.py` MUST fail if any of these break:

| Check | Passes when |
|---|---|
| Task-start once | Start of work → exactly one `task_start`; 0 file/command/think-only messages |
| Human-decision protocol | Park → one `human_decision` with US3 fields; missing consequence/recommendation shown as not stated |
| Recovery events | Cycle start → one `major_recovery`; still-fail → one `validation_recovery_failure`; budget exhaust → that failure **and** `blocked` |
| PR-created | `PR_CREATED` → one event with number + HTML URL; merge not offered |
| Unexpected failure vs abandon | Non-abandon `FAILED` → one `unexpected_failure`; blocked `A` → 0 of that kind |
| Skip-send | Disabled or no target → wait-return `PR_CREATED`, 0 sent, skip visible on `sends` |
| Send retry | After publish, channel fails then succeeds within 3 → still `PR_CREATED`, one occurrence, attempts ≤ 3; all 3 fail → `PR_CREATED`, send `FAILED`, PR identity unchanged |
| Status commands | `/status` `/projects` `/tasks` `/blockers` `/prs` `/status <project>` match overlay/registry/board; unknown project errors in chat; 0 extra clones |
| Idle status | No active run → nothing running + last `PR_CREATED`/`FAILED` when present |
| Chat resume | `A` / `a` / `A.` / `A)` resume parked run; `Z` stays parked with correction; idle letter → nothing waiting |
| Wrong chat | Other `chat_id` → 0 replies, 0 resume |
| No second bot | Test file uses only `MemoryMessagingChannel`; 0 live API calls |

Also required: idempotent re-deliver of the same occurrence does not duplicate a `SENT` event; status does not start a workflow.

## Live chat proof (optional; not pytest)

Requires the **already-connected** Hermes Telegram gateway (same token, same home channel). MUST NOT create a second bot.

1. Gateway already running (`docker compose` `gateway run`) with `TELEGRAM_HOME_CHANNEL` set in isolated Hermes home env — never commit the token.
2. If using the personalAgent pre-dispatch wrapper, home-chat `/status` and a parked letter must hit `handle_inbound`.
3. Confirm other Telegram chats receive no PIV notices.

Contract pytest MUST still pass when the gateway is absent.

## Out of scope for this guide

Restart persistence, writing `kanban.db`, adding agents to live AiNative, NLU, daily-report console, automatic merge.
