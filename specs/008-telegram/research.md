# Research: Telegram Integration

**Feature**: `008-telegram` | **Date**: 2026-09-02

Phase 0 resolves Technical Context against `spec.md` (clarify session 2026-09-02), the constitution, V0 plan Phase 6 (§32–34, §60, §61 Telegram DoD), `personalAgent/src/hermes_kanban/orchestrator.py`, `personalAgent/config/default.yaml`, `personalAgent/docs/discovery.md`, and the live `hermes-agent:local` Telegram plugin (`hermes_cli/telegram_notifier.py`, `hermes_cli/telegram_ops.py`, `gateway/slash_commands.py`, `plugins/platforms/telegram`). No `[NEEDS CLARIFICATION]` remains.

## 1. Where messaging lives

**Decision**: Keep the three public operations on `PivOrchestrator`. The orchestrator **emits** a closed set of orchestration events at existing state transitions. Delivery and inbound dispatch live in a new module `personalAgent/src/hermes_kanban/messaging.py` (`MessagingChannel` protocol + `MemoryMessagingChannel` + live wrapper). Do not add a second orchestrator, a second bot, a second `getUpdates` loop, or a background worker.

Live outbound **reuses** Hermes `TelegramNotifier.from_gateway_adapter` (already-connected adapter `.send`) to the **home channel** (`TELEGRAM_HOME_CHANNEL` / already-connected chat). Contract checks inject `MemoryMessagingChannel`. Re-export public types from `hermes_kanban/__init__.py`.

Contract checks for this phase live in `personalAgent/tests/test_telegram_messaging.py`. Existing 007 tests stay green (send-skip when no channel / disabled is the default for tests that omit the seam).

**Rationale**: Spec FR-008/FR-014: extend *what* is sent, not *how* the chat exists. Constitution II/III: GitHost analogue; do not rebuild Telegram; do not fork Hermes. Discovery already recorded `platform_toolsets.telegram: hermes-telegram`.

**Alternatives considered**:
- Write native `kanban_notify_subs` and let the Kanban poller notify — native Kanban events include worker chatter; overlay `PR_CREATED` / parked briefs are not Kanban task_events. Would mix noisy internals with Phase 6 events.
- Call unwired `hermes_cli.telegram_ops.format_status` — it reads `kanban.db`, is not imported anywhere in this Hermes install, and is the wrong source of truth.
- Second python-telegram-bot process on the same token — conflicts with gateway polling; forbidden duplicate transport.
- Emit from `execute_agent` / executor — would notify on file/command/think internals; forbidden.

## 2. Language, tooling, dependencies

**Decision**: Unchanged. Python 3.12 via uv. pytest + ruff. **No new runtime libraries** (no `python-telegram-bot` in `personalAgent`). Live send: wrap Hermes notifier already in the image. Simulated path: in-memory channel, no network, no bot token.

**Rationale**: Constitution hard constraint; FR-015.

**Alternatives considered**: Add `httpx`/`python-telegram-bot` to the package — duplicate stack. REST `sendMessage` from personalAgent — second transport.

## 3. MessagingChannel seam (simulated vs live)

**Decision**:

```text
MessagingChannel
  deliver(kind, payload, *, occurrence)  # skip / retry-3 / record; never fail the run
  reply(text)                            # status, correction, nothing-waiting
```

Plus package functions (trust boundary for chat):

```text
parse_option_letter(text) -> str | None
handle_inbound(orchestrator, chat_id, text, channel) -> InboundResult
format_status / format_projects / format_tasks / format_blockers / format_prs
```

`MemoryMessagingChannel` records deliveries, skips, failures, and replies in process. Tests inject it. It MUST NOT open a Telegram session.

`HermesTelegramChannel` (live): `TelegramNotifier.from_gateway_adapter(adapter, chat_id=home)`. Retry **that same** formatted notice up to **three attempts total** in our wrapper (Hermes notifier is one try). `notifications.telegram.enabled: false` or empty home chat → skip-send, `SendStatus.SKIPPED`, wait-return unchanged.

Home chat id is the **already-connected** operator chat. Other `chat_id` values: no deliver, no reply, no resume.

**Rationale**: FR-008, FR-009; clarify Q1 (only connected chat); Q3 (retry 3 then record).

**Alternatives considered**: Rely on notifier’s single attempt — contradicts three-attempt requirement. Fork adapter.py to add retries — forbidden.

## 4. Event catalog (push, not poll)

**Decision**: Closed set. One emit per occurrence. Not per executor tool call.

| Kind | When (orchestrator hook) | Occurrence key |
|---|---|---|
| `task_start` | First transition into active work for the run (after prepare, before/at first role execute) | `{run_id}:task_start` |
| `human_decision` | `_park` writes `HUMAN_DECISION_REQUIRED` | `{run_id}:human_decision:{phase}:{len(steps)}` |
| `major_recovery` | `_start_recovery_cycle` begins (including granted blocked `B`) | `{run_id}:major_recovery:{attempt}` |
| `validation_recovery_failure` | Recovery re-validation still fails (`_after_validation` miss after a cycle) | `{run_id}:validation_recovery_failure:{attempt}` |
| `blocked` | `_block` (recovery or github) | `{run_id}:blocked:{phase}:{attempt}` |
| `pr_created` | wait-return `PR_CREATED` | `{run_id}:pr_created` |
| `unexpected_failure` | `_fail` when error is **not** `abandoned` | `{run_id}:unexpected_failure` |

Last-retry overlap: validation_recovery_failure **and** blocked are both required.

Do **not** emit: file read, command run, thinking, per-file edit, per-test line, `QUEUED` alone, PIV-complete history `COMPLETED`, operator abandon (`abandoned` → `FAILED`).

Re-reading the same overlay MUST NOT send a second copy: skip if `sends` already has that occurrence with `SENT`, `SKIPPED`, or `FAILED` (failed may retry until three attempts on the **same** occurrence, then stay `FAILED`).

**Rationale**: FR-001–FR-007; SC-001–SC-005; §32.

**Alternatives considered**: Subscribe to Hermes session progress bubbles — those are internals. Native `/status` poll instead of push — events are push.

## 5. Decision protocol body

**Decision**: Human-decision and blocked messages are formatted from existing `DecisionBrief` / `DecisionOption`. Extend options with optional `consequence: str | None`. Do **not** invent recommendation or consequences; missing → “not stated” (recommendation may be omitted when `None`). Blocked brief already has `A` abandon / `B` retry and a recommended letter.

Fields: project, task, phase, decision required, why it matters, labeled options, recommended (when known), consequence per option (or not stated), how to reply with the letter.

**Rationale**: FR-002, FR-003, US3; spec assumptions.

**Alternatives considered**: One-line “paused” — forbidden. LLM-written consequences — forbidden.

## 6. Status commands vs native slash

**Decision**: Status commands **are in scope**. The gateway already has a clean slash architecture (`COMMAND_REGISTRY`, `slash_exec`, Telegram `CommandHandler`). Inspection result:

| Spec command | Native Hermes 0.20 | PIV meaning |
|---|---|---|
| `/status` | Session cockpit (model, tokens, agent running) | Overlay: project, task, phase, next action; idle = nothing running + last finished |
| `/tasks` | Alias of `/agents` (session agents) | Board + execution overlay |
| `/projects` | Not registered | `ProjectRegistry.list_projects()` (no disk walk) |
| `/blockers` | Not registered | Parked or `BLOCKED` runs |
| `/prs` | Not registered | Recorded `PullRequestIdentity` waiting for human review |

**Home-channel override**: On the **already-connected** chat only, inbound dispatcher answers the spec commands from overlay **before** Hermes native slash/agent. That is an intentional override of native `/status` and `/tasks` in that one chat. Other chats: ignore (no answer). Do not patch `hermes_cli/commands.py`. Do not add a second interpreter.

Natural language: free-text in this gateway is an **agent turn**, not a command table. **Do not** add NLU. Slash (and letter protocol) only.

Unknown `/status <name>`: visible chat error; no workflow start.

Empty board / none blocked / no PRs: say so clearly.

Idle `/status`: nothing running + most recent finished item when `_record` is `PR_CREATED` or `FAILED` (slot already released; overlay still holds last record until the next start). Overlay is process-local (`ponytail:` same ceiling as the slot).

**Rationale**: Spec assumption “commands in scope if hook exists”; FR-010, FR-011; constitution III (do not fork Hermes registry).

**Alternatives considered**: Skip status commands because native `/status` collides — spec default is to implement them and record the collision. Call `telegram_ops.format_status` — wrong store. Walk every worktree — forbidden.

## 7. Chat resume (one state machine, two entrances)

**Decision**: `handle_inbound` is the chat entrance to **existing** `resume_workflow`. Not a second state machine.

`parse_option_letter`: entire text is one letter, case-insensitive, optional surrounding whitespace, optional **single** trailing `.` or `)`. `A`, `a`, ` A. `, `A)` match. `Option A`, `I pick A`, sentences, empty, two letters → not a letter.

- Listed letter + parked/blocked + home chat → `resume_workflow(project_id, task_id, letter)` (project/task from overlay record).
- Unlisted letter while parked/blocked → stay; short correction naming listed letters; do not publish.
- Letter while nothing parked/blocked (idle, running, finished) → “nothing is waiting”; start 0 workflows; do not call `resume_workflow` (avoids raising `ResumeNotParkedError` at the operator).
- Other chat → ignore (no resume, no correction there).
- Programmatic `resume_workflow` unchanged as a public API; optionally share `parse_option_letter` so `A.` works in both entrances (compatible expansion).

Invalid slash/project still fails at the boundary with a visible chat error.

**Rationale**: FR-012, FR-016; clarify Q2, Q5.

**Alternatives considered**: Let the LLM parse A/B — second interpreter; forbidden. Require programmatic resume only — fails US3.

## 8. Live inbound without a second bot

**Decision**: Pytest never starts the gateway. Live inbound MUST share the **existing** gateway poller (one token).

Ship `handle_inbound` as the only inbound API. Live compose MAY wrap `gateway run` with a **personalAgent pre-dispatch** that, for the home chat, calls `handle_inbound` and swallows the event when it was a PIV command or letter; all other messages pass through to Hermes unchanged. Do **not** copy adapter.py. Do **not** start a second updater.

If that wrapper is absent, contract checks still pass; live chat resume is an operator proof, not a pytest dependency (same pattern as live SSH in 007).

**Rationale**: FR-008, FR-015; constitution “do not fork Hermes”.

**Alternatives considered**: Second bot token — forbidden. Patch `gateway/run.py` in the image — fork. Plugin `on_message` — this install has no Telegram inbound plugin hook.

## 9. Config and secrets

**Decision**: Reuse `notifications.telegram.enabled` in `personalAgent/config/default.yaml` (already `true`). Disabled → skip-send. Home chat from runtime env already used by Hermes (`TELEGRAM_HOME_CHANNEL`), not committed. Tokens MUST NOT appear on `WorkflowRecord`, send records, status replies, or message bodies.

**Rationale**: FR-013; constitution secrets.

**Alternatives considered**: Store chat id in git YAML — avoid; env is already the platform home channel.

## 10. Wait-returns, slot, methodology

**Decision**: Unchanged wait-returns: `PR_CREATED`, `FAILED`, `HUMAN_DECISION_REQUIRED`, `BLOCKED`. No background worker. Chat cannot start a second workflow while the slot is occupied. Status does not occupy the slot. Merge/deploy/protected-push still impossible. AiNative read-only. No `kanban.db` writes for this feature.

**Rationale**: FR-014; Phase 7 persistence still out of scope.
