# Research: Restart Recovery

**Feature**: `009-restart-recovery` | **Date**: 2026-09-02

Phase 0 resolves every Technical Context choice against `spec.md` (clarify session 2026-09-02; remaining questions skipped by the parent), the constitution, V0 plan Phase 7 (§50 Interrupted Execution Test, §60 Phase 7, §61 Reliability DoD), prior specs `003`–`008`, and the live `personalAgent` overlay (in-memory `WorkflowRecord` slot, `ponytail:` ceiling named in 005 T006 / 008 plan). No `[NEEDS CLARIFICATION]` remains.

This is **not** Phase 4 (`006-piv-recovery` check-retry) and **not** Phase 8 Docker E2E.

## 1. Where persistence and reclaim live

**Decision**: Keep the three public start/resume operations on `PivOrchestrator`. Add `become_ready()` as the start-up gate. Durable snapshot + alive signal live in a new small module `personalAgent/src/hermes_kanban/persist.py`. Workspace attach/recreate lives on `WorkspaceManager.recover_workspace` in `workspace.py`. Contract checks in `personalAgent/tests/test_restart_recovery.py`. Existing 005–008 tests stay green.

`from_config` MUST call `become_ready()` before returning a usable orchestrator (tests MAY construct with an injected store, then call `become_ready`).

**Rationale**: 005 stored the slot only in process memory; a container stop drops it. Spec FR-017: reclaim is automatic at start-up, before any new start. Constitution II: do not add a second orchestrator. One persist module keeps atomic write + heartbeat off the already-large orchestrator file.

**Alternatives considered**:
- Only `run_workflow` rehydrates if the caller remembers to start again — forbidden (no Resume press; FR-017).
- Overload `resume_workflow` for process death — that API is the parked/blocked letter path; mixing it would require a person.
- Native Hermes worker heartbeat columns as the only store — overlay fields (`execution_id`, `steps`, `diagnostic`, `sends`, `pull_request`) are not Kanban card status (005: `state` does not map onto native `status`).
- Background worker after start-up — forbidden since 005 (wait-return; no fire-and-forget). Reclaim of an in-progress run continues the same blocking chain as `run_workflow`.

## 2. Language, tooling, dependencies

**Decision**: Unchanged. Python 3.12 (`>=3.12,<3.14`) via uv. pytest + ruff. **No new runtime libraries.** Stdlib: `json`, `os.replace`, `pathlib`, `dataclasses`, `time`, `threading`. Git via existing CLI helpers in `workspace.py`. Tests inject a clock (`time.time` equivalent); they MUST NOT `sleep` 60 seconds.

**Rationale**: Constitution hard constraints. Spec assumes native control-plane persistence, not a new database product.

**Alternatives considered**: sqlite3 overlay file — still a second DB file beside `kanban.db`; JSON snapshot is enough for one V0 slot. PyYAML for the snapshot — unapproved dep; JSON is stdlib.

## 3. Durable overlay is not a second task store

**Decision**: Persist **one** operational snapshot of the current `WorkflowRecord` (plus last-finished when the slot is free) as `overlay.json` under a required config directory `execution.overlay_dir`. Atomic write: write `overlay.json.tmp` then `os.replace` onto `overlay.json`. A crash mid-write leaves the previous complete file. NEVER merge two JSON fragments.

Do **not** create `execution.db`. Do **not** write Hermes `kanban.db` / `projects.db`. Do **not** write a sidecar inside the task worktree. `TaskBoard` / human-readable task body remain read-only.

`ponytail:` overlay file, not native Kanban rows. Ceiling: one JSON document for the single V0 slot; upgrade: map identities onto existing Kanban `workspace_path` / `branch_name` / `current_step_key` without a second task table when a later spec wires `SqliteTaskBoard`.

**Rationale**: FR-001/FR-002/SC-001. Constitution III forbids a second **task** database; it does not require stuffing PIV overlay into card `status`. 005 deferred native column writes because they cannot represent `RETRYABLE_FAILURE`, park briefs, or PR identity. Phase 7’s job is restart truth, not a Kanban schema project.

**Alternatives considered**:
- Write native retry/workspace columns now — incomplete, would still need a blob for `steps` / `decision` / `sends`.
- Sidecar in the worktree — dirties the copy; forbidden by 003.
- In-memory only — this feature’s failure mode.

## 4. Overlay directory (trust boundary)

**Decision**: Load `execution.overlay_dir` from the caller-supplied operational YAML (same file as `workspace.root`). Required, non-empty, must exist as a writable directory at `from_config`. MUST NOT default to `$HOME`, `~/.hermes`, `/tmp`, or the workspace root. Production Compose mounts a volume onto that path so a container restart keeps the file. Tests pass a `tmp_path` directory.

Missing/unreadable/not-a-directory → `InvalidOverlayDirError` at construction. MUST NOT invent a path.

Add to `personalAgent/config/default.yaml`:

```yaml
execution:
  max_concurrent_tasks: 1
  overlay_dir: /var/lib/hermes-kanban
```

`docker-compose.yml` MUST bind a named or host volume to `/var/lib/hermes-kanban` (application still reads the YAML path, not `HOME`).

**Rationale**: Isolated Hermes home rule forbids writing `~/.hermes` root; tests already forbid binding host home. Container restart (spec US1) needs a volume that is not the process memory.

**Alternatives considered**: Store under `workspace.root` — mixes control-plane files with task copies. Unnamed `/tmp` — lost on many container restarts.

## 5. Alive signal (heartbeat)

**Decision**: While a copy **holds** the slot (`QUEUED` / `RUNNING` / `VALIDATING` / `RETRYABLE_FAILURE` / `HUMAN_DECISION_REQUIRED` / `BLOCKED`), it keeps `alive` (ISO-8601 UTC or epoch seconds JSON) fresh in `execution.overlay_dir`. Refresh at least every **15 seconds** (daemon thread while held) and on every successful snapshot write. Silence of **60 seconds** (spec) → holder is dead; another copy MAY reclaim. Fresh signal → other copies MUST refuse (`SlotHeldError`); MUST NOT start a worker; MUST NOT steal.

Crash MUST NOT require deleting `alive` or `overlay.json`. Stale file is enough.

Terminal `PR_CREATED` / `FAILED` (slot free): stop refreshing; leave snapshot as last-finished; do not treat a stale heartbeat as an in-progress hold.

Inject `clock` (callable → float seconds) on the persist helper for tests.

`ponytail:` 15s file heartbeat, not Hermes worker heartbeats in `kanban.db`. Ceiling: one V0 process; a model call longer than 60s without a tick would look dead — the ticker thread exists so that cannot happen while the process is alive. Upgrade: native worker heartbeat if a later spec runs real Hermes workers.

**Rationale**: FR-014/FR-015; clarify Q (heartbeat; 60s silence). Constitution III: prefer platform heartbeat **if it already exists for this overlay**. Discovery/prior phases never wired overlay onto Kanban heartbeats.

**Alternatives considered**:
- Lock file that survives crash until a person deletes it — forbidden.
- Steal immediately if PID is dead — unreliable across containers; PID namespaces differ.
- Two-phase commit in `kanban.db` — second schema project.

## 6. become_ready and reclaim grain

**Decision**: `become_ready()` order:

1. If `alive` is fresh (< 60s) and this process is not the holder → `SlotHeldError`. Slot unchanged. No worker.
2. Load last complete `overlay.json` (missing file → idle, ready).
3. Partial/unreadable JSON → treat as missing last complete snapshot only if no prior file; if replace never landed, previous file remains. Corrupt sole file → visible error, do not invent a run.
4. Terminal `PR_CREATED` / `FAILED` → last-finished retained; slot free; ready; 0 workers.
5. `HUMAN_DECISION_REQUIRED` / `BLOCKED` → occupy slot, start heartbeat, **no** automatic worker; ready. Existing resume / chat letter path unchanged.
6. In-progress `QUEUED` / `RUNNING` / `VALIDATING` / `RETRYABLE_FAILURE` → occupy slot, start heartbeat, **continue or safely restart** (below) on the **same** `run_id` / `execution_id` / `workspace_id`. Wait until the same wait-returns as 008 (`PR_CREATED`, `FAILED`, `HUMAN_DECISION_REQUIRED`, `BLOCKED`).
7. Only then may `run_workflow` / `run_next_workflow` be accepted (still `WorkflowBusyError` while occupied).

**Phase (step)** = discovery, planning, implementation, validation, diagnosis, debug, re-check (validation after recovery), or publish (`github`). Not a model call.

Resume vs safe-restart:

- Last **complete** snapshot shows the current phase **finished** (a `steps` row with a completed execute/publish result for that phase, `next_action` pointing at the next phase, or `QUEUED` with phase not started) → **resume** the next (or first) phase. Do not rewind the whole workflow. Do not allocate a new `execution_id`.
- Last complete snapshot shows that phase **in progress** (state in `{RUNNING, VALIDATING, RETRYABLE_FAILURE}` with `current_phase` set and no completed result for that phase in `steps`) → **safe-restart that phase once** on the same copy. Do **not** increment Phase 4 `attempt` or `publish_attempt` solely because the process died.
- `QUEUED` accepted, phase not started → start that next/first phase on the existing identity.

Two `become_ready` calls with the slot already reclaimed by this process: no-op (do not spawn a second chain).

**Rationale**: FR-003–FR-006, FR-010–FR-011, FR-017, US2, edge cases (publish, Phase 4 cycle, QUEUED).

**Alternatives considered**: Replay from discovery every restart — duplicates work and can fork PRs. Per-tool idempotency — out of grain. Incrementing `attempt` on crash — forbidden (not a validation failure).

## 7. Workspace recover (not prepare)

**Decision**: Reclaim MUST NOT call `prepare_workspace` (that path errors on dirty copies and mints a new `execution_id`). Add:

```text
recover_workspace(project_id, task_id, *, workspace_id, execution_id, branch)
```

Rules:

1. Identity checks same as prepare (eligible project, non-path-like task id). Work branch MUST be `feature/task-<task_id>` and MUST NOT be protected.
2. **MUST NOT `git fetch`.** Local copy and local refs only (FR-016). Unreachable GitHub MUST NOT block if the copy exists.
3. If `{root}/{project_id}/{task_id}` exists and is this task’s copy on the recorded feature branch: return it with the **same** `workspace_id` and **same** `execution_id`, even if dirty. MUST NOT reset, clean, or delete. MUST NOT prepare a second directory.
4. If the path belongs to another task / unexpected branch / non-git: `InvalidWorkspaceError` → orchestrator `BLOCKED` (visible reason). MUST NOT adopt it.
5. If the path is missing and the feature branch exists as a **local** ref on the enrolled repo: `git worktree add` that path onto that local branch; same identities. Never `main` / `master` / default.
6. If the path is missing and the branch is only on a remote (or missing): do not wait; orchestrator `BLOCKED`.
7. Unrelated copies under the workspace root are untouched.
8. After recover, `inspect_workspace` still reports branch, dirty, changes.

**Rationale**: FR-007–FR-009, FR-012, FR-016, US3. 003 “never reuse dirty” applies to **new** prepare; spec explicitly allows the interrupted run’s own dirty files.

**Alternatives considered**: `git clone` from GitHub when local copy is gone — waits on network; forbidden. `prepare_workspace` with `force=True` — would mint `execution_id` and collide with dirty rules.

## 8. Dual copy, GitHub, messaging, Phase 8

**Decision**:

- Second live control-plane copy: refuse via fresh `alive` (section 5). V0 does not steal.
- Restart during `github`: same execution; `GitHost.upsert` already rewrites the same head; MUST NOT open a second PR as a restart side effect. `publish_attempt` unchanged by the crash itself; a safe-restart of publish is the same attempt in progress.
- Restart during diagnosis/debug/re-check: same `attempt`; safe-restart that overlay phase; 0 extra Phase 4 budget.
- Messaging: no new event kind. Existing occurrence keys stay once-per-run (`task_start` MUST NOT fire again on reclaim). Later park/block/PR may still emit as 008.
- Phase 8 full fixture parade and live Docker kill are **out of this plan**. Pytest simulates restart by a new orchestrator instance on the same `overlay_dir` + workspace root. Optional Compose restart remains a later proof, not the contract.

**Rationale**: FR-010, FR-013, SC-005, SC-006.

**Alternatives considered**: Dedicated `restarted` Telegram event — spec forbids. Docker-only proof — not hermetic; constitution IV wants one pytest check.

## 9. Public surface delta

**Decision**: Existing `run_workflow` / `run_next_workflow` / `resume_workflow` unchanged in names and wait-returns. Add `become_ready()` (and persist/recover internals). `SlotHeldError` for a living second copy. `InvalidOverlayDirError` for bad overlay dir. Occupied-slot starts still `WorkflowBusyError`.

`from_config(..., clock=None)` may pass a test clock through to persist; omitted → `time.time`.

**Rationale**: Smallest contract extension that makes start-up automatic.

**Alternatives considered**: New CLI `hermes reclaim` — extra surface; start-up is enough.
