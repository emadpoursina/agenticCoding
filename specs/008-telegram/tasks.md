---

description: "Task list for Telegram Integration (closed-set orchestration events on the existing home channel)"
---

# Tasks: Telegram Integration

**Input**: Design documents from `/specs/008-telegram/`

**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/telegram-messaging.md, quickstart.md

**Tests**: Required. Spec FR-015 / SC-001–SC-008 and constitution IV demand one pytest contract file (`personalAgent/tests/test_telegram_messaging.py`) that fails if event delivery, skip/retry, status answers, or chat resume break. Tests listed below MUST be written to fail before the matching implementation.

**Organization**: Tasks are grouped by user story so each story can be implemented, tested, and delivered independently.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (US1–US3)
- Include exact file paths in descriptions

## Path Conventions

Package lives under `personalAgent/`. Source: `personalAgent/src/hermes_kanban/`. Tests: `personalAgent/tests/`. New seam: `personalAgent/src/hermes_kanban/messaging.py`. Do not edit Hermes `adapter.py` / `commands.py`. Do not write `kanban.db`. Do not add a second bot.

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Confirm existing package/config; no new dependencies, no second bot, no `kanban.db` notify writes.

- [X] T001 Confirm `personalAgent/config/default.yaml` keeps `notifications.telegram.enabled` (reuse; disabled → skip-send) and `projects: []`; do not add a production chat id, bot token, or second notify stack
- [X] T002 Confirm `personalAgent/pyproject.toml` adds **no** new runtime libraries (no `python-telegram-bot` / extra HTTP client); live send stays Hermes `TelegramNotifier` already in `hermes-agent:local`

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Messaging seam, overlay send log, optional `consequence`, orchestrator injection. MUST complete before any user story.

**⚠️ CRITICAL**: No user story work can begin until this phase is complete

- [X] T003 Create `personalAgent/src/hermes_kanban/messaging.py` with closed event kinds (`task_start`, `human_decision`, `major_recovery`, `validation_recovery_failure`, `blocked`, `pr_created`, `unexpected_failure`), `SendStatus` (`SENT`/`SKIPPED`/`FAILED`), frozen `SendRecord` (`occurrence`, `kind`, `status`, `attempts`, `error`), `InboundResult` (`handled`, `kind`), and `MessagingChannel` protocol (`deliver(kind, payload, *, occurrence)`, `reply(text)`)
- [X] T004 Implement `MemoryMessagingChannel` in `personalAgent/src/hermes_kanban/messaging.py`: in-process deliveries/replies; MUST NOT open a Telegram session; support skip, fail-N-then-succeed, fail-all-three, and occurrence idempotency (`SENT`/`SKIPPED`/`FAILED` after 3 attempts is not a second event kind)
- [X] T005 Implement `parse_option_letter` in `personalAgent/src/hermes_kanban/messaging.py`: entire text is one ASCII letter, case-insensitive, optional surrounding whitespace, optional single trailing `.` or `)`; return uppercase letter or `None` (`Option A`, sentences, empty, two letters → `None`)
- [X] T006 Extend overlay in `personalAgent/src/hermes_kanban/orchestrator.py`: add `DecisionOption.consequence: str | None = None` (never invent); add `WorkflowRecord.sends: tuple[SendRecord, ...]` append-only; mark overlay send log + last-finished record with a `ponytail:` comment (process-local; Phase 7 persist without a second task DB)
- [X] T007 Inject `messaging: MessagingChannel | None = None` on `PivOrchestrator.__init__` and `from_config` in `personalAgent/src/hermes_kanban/orchestrator.py` (like `git_host`); omitted/disabled/empty home chat → skip-send, wait-returns unchanged; MUST NOT invent a bot token or second chat; existing tests that omit `messaging` stay skip-send
- [X] T008 Re-export messaging types plus `handle_inbound` / `parse_option_letter` from `personalAgent/src/hermes_kanban/__init__.py` (stub `handle_inbound` until US3 if needed so the name exists)

**Checkpoint**: Foundation ready — `MessagingChannel` can be injected; record can hold sends; user stories can proceed

---

## Phase 3: User Story 1 - Meaningful events reach the operator (Priority: P1) 🎯 MVP

**Goal**: Orchestrator emits the closed event set once per occurrence to the injected channel (home chat only). Quiet internals stay silent. Skip-send and send-fail do not change wait-return or pull-request identity.

**Independent Test**: Drive fixture runs through start, park, recovery-start, recovery still-fail, blocked, publish, unexpected fail, and abandon with `MemoryMessagingChannel`. Exactly one message per required event; 0 file/command/think-only messages; disabled path still `PR_CREATED` with 0 sent.

### Tests for User Story 1

> **NOTE: Write these tests FIRST, ensure they FAIL before implementation**

- [X] T009 [US1] Add failing contract checks in `personalAgent/tests/test_telegram_messaging.py` for one `task_start` (project + task) when work begins and 0 messages whose only content is a file read, command run, or thinking/reasoning
- [X] T010 [US1] Add failing checks in `personalAgent/tests/test_telegram_messaging.py` for one `human_decision` on park (US3 protocol fields; missing consequence/recommendation → not stated), one `major_recovery` per cycle start, one `validation_recovery_failure` on still-fail, both that failure **and** `blocked` on budget exhaust, one `pr_created` (number + HTML URL, merge not offered), one `unexpected_failure` on non-abandon `FAILED`, and 0 `unexpected_failure` on blocked `A` abandon
- [X] T011 [US1] Add failing checks in `personalAgent/tests/test_telegram_messaging.py` for skip-send (disabled or no target → same wait-return as 007, 0 sent, skip on `sends`), send retry after publish (fail then succeed within 3 → still `PR_CREATED`, one occurrence, attempts ≤ 3; all 3 fail → `PR_CREATED`, send `FAILED`, PR identity unchanged), and re-read of the same overlay not duplicating a `SENT` event

### Implementation for User Story 1

- [X] T012 [US1] Implement event body formatters in `personalAgent/src/hermes_kanban/messaging.py` for the closed set (no secrets; `pr_created` includes number + `html_url` already on the record; blocked uses existing A/B brief; do **not** call `hermes_cli.telegram_ops.format_status`)
- [X] T013 [US1] Add a single orchestrator emit helper in `personalAgent/src/hermes_kanban/orchestrator.py` that calls `messaging.deliver` with research.md §4 occurrence keys, appends `SendRecord` to `WorkflowRecord.sends`, and **never** raises into the run on send failure
- [X] T014 [US1] Emit `task_start` once per run on first transition into active work (after prepare, before/at first role execute) in `personalAgent/src/hermes_kanban/orchestrator.py`; do not emit from `executor.py` / `execute_agent`
- [X] T015 [US1] Emit `human_decision` from `_park` and `blocked` from `_block` / `_block_publish` in `personalAgent/src/hermes_kanban/orchestrator.py` (one each per occurrence)
- [X] T016 [US1] Emit `major_recovery` from `_start_recovery_cycle` (including granted blocked `B`) and `validation_recovery_failure` when recovery re-validation still fails in `personalAgent/src/hermes_kanban/orchestrator.py`
- [X] T017 [US1] Emit `pr_created` on wait-return `PR_CREATED` and `unexpected_failure` from `_fail` when error is **not** `abandoned` in `personalAgent/src/hermes_kanban/orchestrator.py`
- [X] T018 [US1] Implement `HermesTelegramChannel` in `personalAgent/src/hermes_kanban/messaging.py`: wrap `TelegramNotifier.from_gateway_adapter` to the already-connected home channel; retry **that same** formatted notice up to three attempts in **our** wrapper (native notifier is one-shot); wrong/empty chat → skip; MUST NOT start `getUpdates` or construct a second bot

**Checkpoint**: User Story 1 is independently testable: fixture transitions produce the closed event set on `MemoryMessagingChannel` without a live bot

---

## Phase 4: User Story 3 - Decision message and resume after reply (Priority: P1)

**Goal**: Parked/blocked notices already carry the decision protocol (US1). Home-chat listed letters enter existing `resume_workflow`. Idle letters get “nothing is waiting.” Wrong chats are ignored. No NLU; no second state machine.

**Independent Test**: Park a fixture on a two-option question. Reply `A` / `a` / `A.` / `A)` in the simulated home chat → existing resume runs. `Z` stays parked with correction. Idle letter → nothing waiting, 0 `resume_workflow`. Other `chat_id` → 0 replies, 0 resume. Programmatic `resume_workflow` still works without chat.

### Tests for User Story 3

- [X] T019 [US3] Add failing checks in `personalAgent/tests/test_telegram_messaging.py` for `handle_inbound`: valid listed letters resume parked/blocked runs (same wait-returns as 007); unlisted letter / `Option A` / sentence stays parked or blocked with a short correction naming listed letters; idle/running/finished listed letter → nothing-waiting reply and 0 workflow starts; `chat_id != home` → `ignored`, 0 replies, 0 resume; programmatic `resume_workflow` unchanged when chat is unused

### Implementation for User Story 3

- [X] T020 [US3] Implement `handle_inbound` in `personalAgent/src/hermes_kanban/messaging.py` (`orchestrator`, `chat_id`, `text`, `channel`, `home_chat_id=`): wrong chat → `ignored`; valid listed letter while parked/blocked → `resume_workflow(project_id, task_id, letter)` from overlay; unlisted letter while parked/blocked → stay + correction via `channel.reply`; letter while not parked/blocked → nothing waiting, do **not** call `resume_workflow` (no `ResumeNotParkedError` to the operator)
- [X] T021 [US3] Optionally share `parse_option_letter` with programmatic `resume_workflow` in `personalAgent/src/hermes_kanban/orchestrator.py` so `A.` / `A)` work on both entrances; do not add a plan-approval gate, merge, or a second resume state machine
- [X] T022 [US3] Confirm blocked chat `A` / `B` matches existing abandon / one-more-try rules in `personalAgent/tests/test_telegram_messaging.py` (and that 007 `tests/test_github_publish.py` / `tests/test_piv_orchestrator.py` still pass without requiring chat)

**Checkpoint**: User Stories 1 and 3: events fire; home-chat letters resume the same machine; idle letters are harmless

---

## Phase 5: User Story 2 - Status without scanning every repository (Priority: P2)

**Goal**: On the home chat only, `/status` `/projects` `/tasks` `/blockers` `/prs` and `/status <project>` answer from overlay/registry/board. Native `/status` and `/tasks` are overridden **only** there. No NLU. No disk walk of every enrolled repo. Status does not start a workflow or occupy the slot.

**Independent Test**: With a fixture in `RUNNING`, then parked, then `PR_CREATED`, invoke the six commands via `handle_inbound`. Answers match operational state; unknown project errors in chat; 0 extra clones; 0 workflow starts. Free-text is `ignored` (gateway treats it as an agent turn; do not add a parser).

### Tests for User Story 2

- [X] T023 [US2] Add failing checks in `personalAgent/tests/test_telegram_messaging.py` for home-chat `/status` (active: project, task, phase, in progress), idle `/status` (nothing running + last finished `PR_CREATED`/`FAILED` when present), `/projects` from `list_projects()`, `/tasks` from board + overlay, `/blockers` parked or `BLOCKED` (or “nothing blocked or waiting”), `/prs` recorded identity without merge, `/status <known>` scoped, `/status <unknown>` visible error, 0 workflow starts, 0 extra clones; other chat → 0 status replies

### Implementation for User Story 2

- [X] T024 [US2] Implement `format_status`, `format_projects`, `format_tasks`, `format_blockers`, `format_prs` in `personalAgent/src/hermes_kanban/messaging.py` from overlay/registry/board only (empty board / no PRs / none blocked say so clearly; secrets absent)
- [X] T025 [US2] Dispatch those slash commands in `handle_inbound` in `personalAgent/src/hermes_kanban/messaging.py` **before** any Hermes native slash: home chat only; `handled=True` so live pre-dispatch can swallow them; non-PIV text stays `ignored` (pass-through); do **not** patch Hermes `COMMAND_REGISTRY` / `commands.py`; do **not** add NLU
- [X] T026 [US2] Keep `personalAgent/docker-compose.yml` bot command unchanged (no second `getUpdates`); live inbound, if wired later, is a personalAgent pre-dispatch around existing `gateway run` only — not required for pytest

**Checkpoint**: All three stories independently functional on `MemoryMessagingChannel`

---

## Phase 6: Polish & Cross-Cutting Concerns

**Purpose**: Regression, lint, version history, optional live proof (not a pytest dependency)

- [X] T027 Run `uv run pytest tests/test_telegram_messaging.py tests/test_github_publish.py tests/test_piv_orchestrator.py tests/test_agent_executor.py` in `personalAgent/` and keep 001–007 tests green (omit-`messaging` paths remain skip-send)
- [X] T028 [P] Run `uv run ruff check src tests` in `personalAgent/`
- [X] T029 [P] Update `CHANGELOG.md` (and package version if this repo keeps one) for the Telegram seam: events, home-chat status override, letter resume, skip/retry-3; no Hermes fork
- [X] T030 Confirm quickstart.md checks: contract file uses only `MemoryMessagingChannel`; 0 live Telegram API calls; optional live home-chat proof documented as operator-only

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies — can start immediately
- **Foundational (Phase 2)**: Depends on Setup — BLOCKS all user stories
- **User Story 1 (Phase 3)**: Depends on Foundational — MVP events
- **User Story 3 (Phase 4)**: Depends on Foundational; uses US1 park/block emits for a realistic chat resume, but inbound can be tested against an already-parked overlay
- **User Story 2 (Phase 5)**: Depends on Foundational + `handle_inbound` from US3 (slash dispatch extends the same function)
- **Polish (Phase 6)**: Depends on the stories you are delivering

### User Story Dependencies

- **User Story 1 (P1)**: After Phase 2 — no dependency on status or inbound
- **User Story 3 (P1)**: After Phase 2 — independently testable with a parked fixture; product-complete after US1 emits `human_decision` / `blocked`
- **User Story 2 (P2)**: After `handle_inbound` exists — independently testable without live Telegram; do not block MVP events on status

### Within Each User Story

- Tests MUST be written and FAIL before implementation
- Types/seam before emit hooks
- Emit before inbound
- Inbound letters before slash dispatch (same `handle_inbound`)
- Story complete before moving to the next priority increment you intend to ship

### Parallel Opportunities

- T001 and T002 (read-only confirmations) can run together
- T009 / T010 / T011 are the **same test file** — do not parallelize (avoid merge conflicts)
- After T003–T007, T008 can proceed
- T012 (formatters in `messaging.py`) and T013 (emit helper in `orchestrator.py`) can start together once the protocol exists; later emit hooks (T014–T017) are sequential on `orchestrator.py`
- T028 and T029 can run in parallel after tests are green

---

## Parallel Example: User Story 1

```bash
# Sequential in the same test file (do not split across agents):
Task: "Failing task_start + no-internals checks in personalAgent/tests/test_telegram_messaging.py"
Task: "Failing park/recovery/blocked/PR/fail/abandon checks in personalAgent/tests/test_telegram_messaging.py"
Task: "Failing skip-send / retry-3 / idempotency checks in personalAgent/tests/test_telegram_messaging.py"

# After tests fail, formatters vs emit helper (different files):
Task: "Event formatters in personalAgent/src/hermes_kanban/messaging.py"
Task: "Emit helper in personalAgent/src/hermes_kanban/orchestrator.py"
```

---

## Parallel Example: User Story 3 then 2

```bash
# Same inbound function — sequential, one owner:
Task: "Letter resume / correction / idle / wrong chat in personalAgent/src/hermes_kanban/messaging.py"
Task: "Slash formatters + home-chat dispatch in personalAgent/src/hermes_kanban/messaging.py"
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Complete Phase 1: Setup
2. Complete Phase 2: Foundational (CRITICAL — blocks all stories)
3. Complete Phase 3: User Story 1
4. **STOP and VALIDATE**: pytest event catalog, skip-send, retry-3, no internals
5. Demo with `MemoryMessagingChannel` (live chat optional)

### Incremental Delivery

1. Setup + Foundational → seam injectable
2. US1 events → operators hear start/park/recovery/block/PR/fail
3. US3 chat resume → letters in the home chat continue the same machine
4. US2 status → `/status` and friends on that chat only
5. Each story keeps 007 wait-returns; send failure never undoes publish

### Parallel Team Strategy

With multiple developers:

1. Team completes Setup + Foundational together
2. Once Foundational is done:
   - Developer A: User Story 1 (`orchestrator.py` emit hooks + `HermesTelegramChannel`)
   - Developer B: User Story 3/2 tests **after** agreeing A owns `orchestrator.py` and B owns inbound/formatters in `messaging.py` — still serialize `test_telegram_messaging.py`

---

## Notes

- [P] tasks = different files, no dependencies
- [Story] label maps task to spec US1 (events), US2 (status), US3 (decision/resume)
- Public names unchanged: `run_workflow`, `run_next_workflow`, `resume_workflow`; chat adds `handle_inbound` + `parse_option_letter`
- Home chat only; three retries then record-fail; no NLU; no `kanban.db` notify writes; no Hermes fork
- Stop after Telegram contract checks + optional live home-chat proof; do not start Phase 7
- Verify tests fail before implementing
- Commit after each task or logical group only if the operator asks
- Avoid: second bot, native slash fork, `telegram_ops.format_status`, walking every clone for `/status`

---

## Phase 7: Convergence

- [X] T031 Expand `personalAgent/tests/test_telegram_messaging.py` so the MemoryMessagingChannel contract fails if park/recovery/blocked/PR/fail/abandon events, skip/retry-3/idempotency, home-chat status commands (including idle last `PR_CREATED`/`FAILED`), letter correction/idle-nothing-waiting, or blocked chat `A`/`B` break per FR-015
