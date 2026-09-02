# Data Model: Telegram Integration

**Feature**: `008-telegram` | **Date**: 2026-09-02

Extends the 007 overlay. No new database. No native Kanban writes. Types remain frozen dataclasses. Notifications are operator visibility on `WorkflowRecord`, not mutations of `BoardTask`.

## Board task (unchanged)

`BoardTask` stays read-only. Messaging MUST NOT overwrite problem, expected result, platform, acceptance criteria, technical notes, dependencies, owner, reviewer, or priority.

## Messaging connection

**Entity**: already-connected operator chat (Hermes home channel).

| Field | Rules |
|---|---|
| `chat_id` | Non-empty string from runtime home channel. Sole allowed source and destination. |
| `enabled` | `notifications.telegram.enabled`. False → skip-send. |
| `adapter` | Existing gateway Telegram adapter. Not constructed by this package as a second bot. |

Wrong `chat_id`: no event, no status answer, no resume, no correction.

## Orchestration event kinds (closed set)

| Kind | Operator meaning |
|---|---|
| `task_start` | Run left idle and began work (once per run) |
| `human_decision` | Parked; body is the decision protocol |
| `major_recovery` | A recovery cycle started (once per cycle) |
| `validation_recovery_failure` | That cycle’s re-validation still failed |
| `blocked` | Entered `BLOCKED` (includes A/B escalation brief) |
| `pr_created` | Wait-return `PR_CREATED`; includes `number` + `html_url` already on the record. MUST NOT offer merge. |
| `unexpected_failure` | Terminal `FAILED` that is not operator abandon |

No other kinds. Internals are not events.

## Send record

**Entity**: `SendRecord` on `WorkflowRecord.sends`

| Field | Type | Rules |
|---|---|---|
| `occurrence` | `str` | Stable id (see research §4). Idempotency key. |
| `kind` | `str` | Closed set above. |
| `status` | `str` | `SENT` \| `SKIPPED` \| `FAILED` |
| `attempts` | `int` | 1–3 for a failed/retried notice. Skip counts as 0 send attempts. |
| `error` | `str \| None` | Last transport error; no tokens. |

Skip when disabled or no delivery target. Fail after three attempts of the **same** occurrence. MUST NOT change execution state or pull-request identity because of send status.

## Decision protocol

Existing `DecisionBrief` / `DecisionOption`. This phase adds:

| Field | Type | Rules |
|---|---|---|
| `DecisionOption.consequence` | `str \| None` | From parked brief when present; else `None` → message shows not stated. MUST NOT invent. |
| `DecisionBrief.recommended` | `str \| None` | Already present. Omit or mark not stated when `None`. MUST NOT invent. |

Blocked options remain `A` Abandon / `B` Retry once.

## Chat letter

Valid inbound decision text: one ASCII letter, optional surrounding whitespace, optional single trailing `.` or `)`. Stored/resumed as uppercase letter without punctuation.

Invalid as a letter: empty, multi-character (except the optional trailer), `Option A`, sentences.

## Status snapshot (read-only)

Derived; not stored as a second board.

| Command | Source | Idle / empty |
|---|---|---|
| `/status` | Overlay record if active (`QUEUED`/`RUNNING`/`VALIDATING`/`HUMAN_DECISION_REQUIRED`/`RETRYABLE_FAILURE`/`BLOCKED`) | “Nothing running” + last finished (`PR_CREATED` / last `BLOCKED` only if somehow retained after release — V0 last finished is `PR_CREATED` or `FAILED` on `_record` when slot free). No finished item → only nothing running. |
| `/status <project>` | Same, scoped; unknown id → chat error | Same empty language scoped or error |
| `/projects` | `ProjectRegistry.list_projects()` enabled/disabled as recorded | “(none)” |
| `/tasks` | `TaskBoard.list()` + overlay state for matching ids | Board empty → say so; do not invent tasks |
| `/blockers` | Overlay `HUMAN_DECISION_REQUIRED` or `BLOCKED` | “Nothing blocked or waiting” |
| `/prs` | Overlay `pull_request` when `PR_CREATED` (and any retained identity) | “No pull requests waiting for review”. Merge not offered. |

MUST NOT clone or fully re-scan enrolled working copies to answer.

## Workflow record (additions)

Existing fields remain.

| Field | Type | Rules |
|---|---|---|
| `sends` | `tuple[SendRecord, ...]` | Append-only for this run. Not copied into the task body. |
| `decision.options[].consequence` | optional | See above. |

`state`, wait-returns, slot occupancy, `pull_request`, `publish_attempt`, recovery `attempt`: unchanged from 007.

Secrets, bot tokens, and private URLs MUST NOT appear on the record, briefs, status text, or send errors beyond what 007 already forbids.

## Inbound result (not persisted)

| Field | Meaning |
|---|---|
| `handled` | True → do not pass the message to Hermes agent/native slash |
| `kind` | `status` \| `resume` \| `correction` \| `nothing_waiting` \| `ignored` \| `error` |

`ignored` is for wrong chat or non-PIV text (pass-through live).
