# Data Model: Restart Recovery

**Feature**: `009-restart-recovery` | **Date**: 2026-09-02

Extends the 008 overlay. No second task store. No native Kanban writes. Types remain frozen dataclasses. Restart truth lives on the operational snapshot, not on `BoardTask`.

## Board task (unchanged)

`BoardTask` stays read-only. Reclaim MUST NOT overwrite problem, expected result, platform, acceptance criteria, technical notes, dependencies, owner, reviewer, or priority. Execution details MUST NOT be copied into that body to “repair” them.

## Overlay directory (trust-boundary input)

**Entity**: `execution.overlay_dir` from operational YAML

| Field | Type | Rules |
|---|---|---|
| `overlay_dir` | `Path` | Required. Non-empty. Must exist as a writable directory at construction / `from_config`. |

**Validation**: Failure → `InvalidOverlayDirError`. No fallback (`$HOME`, `~/.hermes`, `/tmp`, workspace root).

**Files inside** (control-plane owned; not a task board):

| File | Role |
|---|---|
| `overlay.json` | Last complete snapshot (see Overlay snapshot) |
| `overlay.json.tmp` | In-flight write; never read as truth |
| `alive` | Alive signal while the slot is held |

## Overlay snapshot

**Entity**: durable copy of the single V0 slot

| Field | Type | Rules |
|---|---|---|
| `record` | `WorkflowRecord \| None` | Current or last-finished run. `None` when never started |
| `slot` | `str` | `occupied` \| `free` |
| `schema` | `str` | Literal `v0` for this phase |

Write rule: serialize only after a **complete** record mutation. Use temp file + `os.replace`. Readers MUST ignore `.tmp`. A mixed or truncated `overlay.json` MUST NOT be treated as two runs.

Identities on `record` that MUST round-trip unchanged across restart: `run_id` (existing), `task_id`, `execution_id`, `project_id`, `workspace_id`. `worker_id` MAY change after reclaim. `attempt` / `publish_attempt` MUST NOT increase solely because the process died.

Paths on the record: store `workspace_path` as a string; load back to `Path`.

Secrets, tokens, `SSH_AUTH_SOCK`, private keys MUST NOT appear in the snapshot.

## Alive signal

**Entity**: proof a live copy holds the slot

| Field | Type | Rules |
|---|---|---|
| `written_at` | `float` | `clock()` seconds when last refreshed |
| `fresh_for` | `float` | **60** seconds (spec). Not operator-configurable this phase |

Fresh (`clock() - written_at < 60`) → other copies refuse. Silent ≥ 60s → holder dead; reclaim allowed. Crash does not require deleting this file.

Held states: `QUEUED`, `RUNNING`, `VALIDATING`, `RETRYABLE_FAILURE`, `HUMAN_DECISION_REQUIRED`, `BLOCKED`.

Not held: idle, `PR_CREATED`, `FAILED` (slot free). Stale `alive` after a terminal snapshot MUST NOT block a new start.

## Phase (step) — reclaim grain

Closed set (unchanged values; reclaim operates here, not per tool):

| Phase | Notes |
|---|---|
| `discovery` | Scout |
| `planning` | Planner |
| `implementation` | Builder |
| `validation` | Tester / re-check |
| `diagnosis` | Phase 4 |
| `debug` | Phase 4 |
| `github` | Publish |

**In progress**: snapshot `state` in `{RUNNING, VALIDATING, RETRYABLE_FAILURE}` and no completed result for `current_phase` in `steps`.

**Phase completed**: last complete snapshot has a finished result for that phase (`execute_status` success/fail recorded, or publish outcome recorded) and `next_action` names the following phase (or `QUEUED` with work not started).

## Reclaim action (derived, not a stored enum)

| Snapshot | Action |
|---|---|
| No file / `record is None` | Idle. Do not invent a task |
| `PR_CREATED` / `FAILED` | Last-finished only. No worker |
| `HUMAN_DECISION_REQUIRED` / `BLOCKED` | Occupy slot. No automatic worker |
| In progress, phase completed | **Resume** next phase. Same identities |
| In progress, phase in progress | **Safe-restart** that phase once. Same identities. Same `attempt` / `publish_attempt` |
| `QUEUED`, phase not started | Start first/next phase. Same identities |
| Path missing + local feature branch | Recreate copy; same `workspace_id` / `execution_id` |
| Path missing + no local branch | `BLOCKED`, visible reason, slot occupied |
| Path exists but other task | `BLOCKED`. Do not adopt |

## Isolated working copy (recover)

Existing `PreparedWorkspace` fields. Recover **keeps** `execution_id` and `workspace_id`. Dirty on this path is allowed. `prepare_workspace` rules for **new** runs are unchanged (`DirtyWorkspaceError`).

Layout unchanged: `{workspace_root}/{project_id}/{task_id}/`. Branch unchanged: `feature/task-<task_id>`.

## In-progress slot

One occupancy. After restart it is the reclaimed run, a parked decision, or a blocked run — never two. Held by at most one live control-plane copy.

`WorkflowBusyError` still refuses a second `run_workflow` / `run_next_workflow` while occupied (including after reclaim, including parked/blocked).

`SlotHeldError` refuses a **second process** while `alive` is fresh.

## Execution state (closed set, unchanged)

`QUEUED`, `RUNNING`, `VALIDATING`, `RETRYABLE_FAILURE`, `HUMAN_DECISION_REQUIRED`, `BLOCKED`, `COMPLETED` (history), `FAILED`, `PR_CREATED`.

Reclaim MUST NOT invent a new state name.

## Workflow record (no new business fields)

Existing 008 fields remain. Persistence is the same record, not a parallel schema.

`sends` round-trip so 008 occurrence keys stay unique (`task_start` once per `run_id`).

## State transitions (restart-specific)

```text
process stop  -->  last complete overlay.json remains
become_ready + fresh alive (other copy)  -->  SlotHeldError (no worker)
become_ready + idle                     -->  ready, slot free
become_ready + terminal                 -->  last-finished, slot free
become_ready + parked/blocked           -->  occupy, wait for existing resume
become_ready + in-progress              -->  recover workspace --> resume|safe-restart
recover: copy present (dirty OK)        -->  same path
recover: copy gone, local branch        -->  worktree add, same ids
recover: copy gone, no local branch     -->  BLOCKED
recover: wrong task path                -->  BLOCKED
GitHub/network down + local copy        -->  continue (no fetch)
safe-restart github                     -->  same execution, upsert same head (0 second PRs from crash alone)
safe-restart diagnosis|debug|validation -->  attempt unchanged
```

| Event | Slot | `execution_id` | `attempt` |
|---|---|---|---|
| Crash / container restart | as last snapshot | unchanged | unchanged |
| Reclaim resume/safe-restart | occupied | unchanged | unchanged |
| Second start while occupied | refuse | unchanged | unchanged |
| Second live copy, fresh alive | refuse (`SlotHeldError`) | unchanged | unchanged |
| New start after `FAILED`/`PR_CREATED` | new run | new (existing prepare rule) | `1` |

## Validation summary (trust boundaries)

| Boundary | What fails |
|---|---|
| `overlay_dir` | Missing, not a directory, not writable |
| `alive` fresh, other process | `SlotHeldError` |
| Snapshot read | Use last complete file; never a mixed record |
| `recover_workspace` | Eligibility, task id, protected branch, foreign path, missing local copy **and** missing local branch |
| `run_workflow` after ready | Same 008 busy/eligibility errors; MUST NOT run before `become_ready` |
