# Implementation Plan: Telegram Integration

**Branch**: `008-telegram` | **Date**: 2026-09-02 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `/specs/008-telegram/spec.md`

**Note**: This template is filled in by the `/speckit-plan` command; its definition describes the execution workflow.

## Summary

Phases 0–5 already record start, park, recovery, blocked, `PR_CREATED`, and `FAILED` on the overlay. Those outcomes are not yet operator-facing. This phase connects a **closed set of orchestration events** to the **existing** Hermes Telegram gateway (home channel only), answers `/status` `/projects` `/tasks` `/blockers` `/prs` from overlay/registry/board when asked in that chat, and treats a listed option letter as a second **entrance** to existing `resume_workflow`. Do not duplicate the bot, do not write `kanban.db` notify rows, do not add NLU, do not fail the run because a send failed.

Technical approach: `messaging.py` seam (GitHost analogue) + surgical emit/inbound hooks in `orchestrator.py`; pytest module `test_telegram_messaging.py`; wrap Hermes `TelegramNotifier` live. See [research.md](./research.md).

## Technical Context

**Language/Version**: Python 3.12 (`>=3.12,<3.14`) via uv — already pinned in `personalAgent/pyproject.toml`

**Primary Dependencies**: None new. Stdlib + existing orchestrator/registry/board/GitHost. Live: Hermes `TelegramNotifier` already in `hermes-agent:local`. Dev: pytest, ruff (already listed)

**Storage**: Same in-memory `WorkflowRecord` overlay plus `sends`. No second SQLite file. Hermes `kanban.db` / `projects.db` unwritten. `kanban_notify_subs` unused for PIV events

**Testing**: pytest + ruff; new `personalAgent/tests/test_telegram_messaging.py`; `MemoryMessagingChannel` + stand-in model + `MemoryTaskBoard` + `MemoryGitHost`

**Target Platform**: Host pytest (macOS/Linux). Live optional proof on existing Docker Compose gateway + already-connected chat. Live Telegram not required for contract checks

**Project Type**: Library (in-process orchestrator inside `hermes_kanban`)

**Performance Goals**: One notice per occurrence; at most 3 send attempts per notice. Status is one round-trip from overlay. No throughput target

**Constraints**: No new third-party libraries. No second bot or `getUpdates` loop. Home chat only. Send failure must not undo publish. No NLU. No methodology writes. No merge/deploy. No background worker. Phase 7 persistence out of scope. Do not fork Hermes adapter/command registry

**Scale/Scope**: Messaging module + orchestrator emit/inbound + one contract file. Production `projects: []` unchanged. Native `/status` and `/tasks` overridden **only** on the home chat by our dispatcher

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

### Pre-research (PASS)

| Principle / constraint | Verdict | Notes |
|---|---|---|
| I. Spec-first | PASS | `spec.md` complete; clarify 2026-09-02 recorded; checklist ready; no `[NEEDS CLARIFICATION]` |
| II. Least Code | PASS | Reuse overlay, `resume_workflow`, `DecisionBrief`, Hermes notifier. One new module. No second bot |
| III. Platform-native | PASS | Existing Telegram plugin + home channel. Do not rebuild transport. Do not write a second task DB. Home-channel `/status` override is documented, not a Hermes fork |
| IV. Trust-boundary tests | PASS | Same three public calls + `handle_inbound`; one pytest contract file; simulated channel |
| V. Human authority | PASS | Merge still impossible; letters only; secrets not in messages |
| Python 3.12 + uv | PASS | Existing package |
| No new deps without approval | PASS | Explicit non-goal |
| Secrets / isolated Hermes home | PASS | Token stays in Hermes env; not on records |
| Model routing | PASS | Messaging does not call models |
| Out-of-scope list | PASS | Persistence, daily-report console, NLU, Obsidian, concurrency: not in this plan |
| Surgical edits | PASS | Orchestrator emit points + messaging.py + tests; do not rewrite GitHost/executor |

### Post-design (PASS)

Design stays in-process. `MemoryMessagingChannel` is the contract ceiling. Live wrap of `TelegramNotifier` is reuse, not a second stack. Native slash collision is an operator-chat override, not a constitution violation (Hermes source untouched). Retry-3 lives in our wrapper because the native notifier is one-shot. Complexity Tracking remains empty.

## Project Structure

### Documentation (this feature)

```text
specs/008-telegram/
├── plan.md
├── spec.md
├── research.md
├── data-model.md
├── quickstart.md
├── contracts/
│   └── telegram-messaging.md
├── checklists/
│   └── requirements.md
└── tasks.md             # Phase 2 (/speckit-tasks) — not created here
```

### Source Code (repository)

```text
personalAgent/
├── src/hermes_kanban/
│   ├── __init__.py          # re-export messaging types + handle_inbound
│   ├── orchestrator.py      # emit events; optional messaging=; DecisionOption.consequence
│   ├── messaging.py         # MessagingChannel, Memory, live wrap, inbound, formatters, letter parse
│   ├── github.py            # unchanged
│   ├── executor.py          # unchanged (no per-tool notify)
│   └── projects.py          # list_projects already sufficient for /projects
├── tests/
│   └── test_telegram_messaging.py
├── config/default.yaml      # notifications.telegram.enabled already present
└── docker-compose.yml       # unchanged bot command; optional pre-dispatch wrapper later if live inbound is wired
```

**Structure Decision**: Add `messaging.py` for the delivery/inbound seam. Do not add a Telegram package. Do not open `kanban.db`. Do not vendor the Hermes telegram adapter. Do not add agents to live `AiNative`.

## Complexity Tracking

> No constitution violations requiring justification.

## Phase 0 / Phase 1 outputs

| Artifact | Path |
|---|---|
| Research | [research.md](./research.md) |
| Data Model | [data-model.md](./data-model.md) |
| Contracts | [contracts/telegram-messaging.md](./contracts/telegram-messaging.md) |
| Quickstart | [quickstart.md](./quickstart.md) |

## Implementation notes (for `/speckit-tasks`, not this command)

- Public names unchanged: `run_workflow`, `run_next_workflow`, `resume_workflow`. Chat adds `handle_inbound` + `parse_option_letter`.
- Inject `messaging` like `git_host`; tests use `MemoryMessagingChannel`.
- Emit only the closed event set; skip internals.
- Home chat only; wrong chat ignores.
- Retry same occurrence 3 times; skip-send does not fail the run.
- `/status` idle = nothing running + last finished `PR_CREATED`/`FAILED` on overlay.
- Valid letter: single letter + optional spaces + optional trailing `.` or `)`.
- Idle letter → nothing waiting, not `ResumeNotParkedError` to the operator.
- Do not call `telegram_ops.format_status` (unwired; wrong store).
- Do not add NLU.
- `ponytail:` overlay send log and last-finished record (process-local). Upgrade: persist with Phase 7 runtime without a second task DB.
- Stop after Telegram contract checks + optional live home-chat proof; do not start Phase 7.
