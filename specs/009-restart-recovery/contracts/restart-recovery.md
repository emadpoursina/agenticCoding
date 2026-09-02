# Contract: Restart Recovery (in-process)

**Feature**: `009-restart-recovery` | **Packages**: `hermes_kanban.orchestrator`, `hermes_kanban.persist`, `hermes_kanban.workspace`

Extends [008 Telegram messaging](../../008-telegram/contracts/telegram-messaging.md). Same three public start/resume operations. Phase 4 check-retry rules unchanged. Phase 8 Docker E2E, merge, a second task store, and native `kanban.db` writes remain out of contract.

Types: [data-model.md](../data-model.md). Reuse overlay, GitHost, messaging, executor, registry, board. **Surgical changes**: persist the slot; `become_ready()` before starts; `recover_workspace` instead of `prepare_workspace` on reclaim.

## Construction

```python
class PivOrchestrator:
    def __init__(
        self,
        executor: AgentExecutor,
        workspaces: WorkspaceManager,
        registry: ProjectRegistry,
        task_board: TaskBoard,
        git_host: GitHost | None = None,
        messaging: MessagingChannel | None = None,
        overlay_dir: Path | None = None,
        *,
        clock: Callable[[], float] | None = None,
    ) -> None: ...

    @classmethod
    def from_config(cls, config_path: Path, **kwargs) -> PivOrchestrator: ...

    def become_ready(self) -> WorkflowRecord | None: ...
```

`from_config` loads `execution.overlay_dir`, constructs as today, then MUST call `become_ready()` before the instance accepts `run_workflow` / `run_next_workflow`.

Checks MUST pass a temp `overlay_dir`. MUST NOT bind `$HOME` / `HERMES_HOME`. `clock` omitted → `time.time`. Tests jump `clock` rather than sleeping 60s.

Missing/invalid overlay dir → `InvalidOverlayDirError`. MUST NOT invent a directory.

## Wait / slot

Unchanged wait-returns: `PR_CREATED`, `FAILED`, `HUMAN_DECISION_REQUIRED`, `BLOCKED`. No background worker.

`become_ready` on an in-progress snapshot MUST continue until one of those wait-returns (same blocking chain as `run_workflow`). Parked/blocked snapshots return that record without a worker.

Occupied slot after reclaim: second `run_workflow` / `run_next_workflow` → `WorkflowBusyError` (same as 008).

Fresh alive signal from another copy → `SlotHeldError`. MUST NOT start a worker. MUST NOT reclaim.

`resume_workflow` remains the parked/blocked **letter** path. It is NOT the process-death path.

## Reclaim

Keep `task_id`, `execution_id`, `project_id`, `workspace_id`, `run_id`. Do not allocate a new execution identity.

- Phase completed → resume next phase.
- Phase in progress → safe-restart that phase once; do not increment recovery `attempt` or `publish_attempt` because the process died.
- `QUEUED` → start the pending phase on the existing identity.
- Terminal → no automatic work.
- Two `become_ready` calls on the same held instance → MUST NOT start a second chain.

Publish in progress: same `GitHost.upsert` head; 0 second PRs caused by restart alone.

## Workspace

```python
def recover_workspace(
    self,
    project_id: str,
    task_id: str,
    *,
    workspace_id: str,
    execution_id: str,
    branch: str,
) -> PreparedWorkspace: ...
```

MUST NOT `git fetch`. MUST NOT mint a new `execution_id` or `workspace_id`. Dirty copy of **this** task is allowed. Foreign path → `InvalidWorkspaceError`. Missing copy + local `feature/task-<id>` → worktree add on that branch. Missing both → error the orchestrator maps to `BLOCKED`. MUST NOT call `prepare_workspace` for reclaim.

`inspect_workspace` after recover still returns branch, dirty, changes.

`prepare_workspace` for a **new** start is unchanged (still `DirtyWorkspaceError` on dirty reuse).

## Persist helper

```python
def write_overlay(directory: Path, snapshot: OverlaySnapshot) -> None: ...
def read_overlay(directory: Path) -> OverlaySnapshot | None: ...
def touch_alive(directory: Path, *, clock: Callable[[], float]) -> None: ...
def alive_is_fresh(directory: Path, *, clock: Callable[[], float], ttl_s: float = 60.0) -> bool: ...
```

`write_overlay` MUST be atomic (`os.replace`). `read_overlay` MUST NOT parse `.tmp` as truth.

## Isolation / stand-in

Checks inject `ModelService`, `MemoryTaskBoard`, `MemoryGitHost`, optional `MemoryMessagingChannel`, temp workspace root, temp overlay dir, injected `clock`. MUST NOT require a live model, live `kanban.db`, github.com, Telegram, or Docker.

Simulate restart: write snapshot + stop heartbeat (or jump clock ≥ 60s), construct a **new** `PivOrchestrator` on the same dirs, `become_ready`.

Simulate two copies: first keeps `alive` fresh; second `become_ready` → `SlotHeldError`.

Simulate offline: recover with no network; existing copy continues; missing copy with only a remote branch → `BLOCKED` without hanging.

## Errors

| Error | When |
|---|---|
| `InvalidOverlayDirError` | Overlay dir missing / not writable |
| `SlotHeldError` | Another copy’s alive signal is fresh |
| `WorkflowBusyError` | Start while this process holds the slot |
| Existing workspace / registry / board errors | Unchanged |

## Out of contract

- Phase 8 full E2E parade and required live container kill
- Writing `kanban.db` / `projects.db` / a second task SQLite
- New Telegram event kind `restarted`
- Incrementing Phase 4 budget because the process died
- Opening a second PR because the process died
- Concurrent workers (`max_concurrent_tasks` stays 1)
- Operator Resume for process death
- Merge / deploy / protected push
