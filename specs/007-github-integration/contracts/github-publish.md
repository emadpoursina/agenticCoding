# Contract: GitHub Publish (in-process)

**Feature**: `007-github-integration` | **Packages**: `hermes_kanban.orchestrator`, `hermes_kanban.github`

Extends [006 PIV recovery](../../006-piv-recovery/contracts/piv-orchestrator.md). Same three public operations. Telegram, restart persistence, a background worker, merge, and non-github.com hosts remain out of contract.

Types: [data-model.md](../data-model.md). Reuse workspace publish gate, executor (builder still MUST NOT push), registry, adapter. **Surgical orchestrator change**: after validation pass, do not return `COMPLETED`; run GitHub then return `PR_CREATED` or `BLOCKED`.

## Construction

```python
class GitHost(Protocol):
    def ensure_commit(self, copy: Path, branch: str, default_branch: str, task_id: str) -> None: ...
    def push_feature_branch(self, copy: Path, branch: str, remote_url: str | None) -> None: ...
    def upsert_pull_request(
        self,
        *,
        copy: Path,
        head: str,
        base: str,
        title: str,
        body: str,
    ) -> PullRequestIdentity: ...

class PivOrchestrator:
    def __init__(
        self,
        executor: AgentExecutor,
        workspaces: WorkspaceManager,
        registry: ProjectRegistry,
        task_board: TaskBoard,
        git_host: GitHost | None = None,
    ) -> None: ...
```

Checks MUST inject `MemoryGitHost` (or equivalent). Omitted `git_host` in `from_config` → `LiveGitHost`. MUST NOT invent a github.com repo or `GH_TOKEN` default.

`allow_merge` is never honored as permission to merge.

## Wait / slot

`run_workflow` / `run_next_workflow` / `resume_workflow` MUST wait until `PR_CREATED`, `FAILED`, `HUMAN_DECISION_REQUIRED`, or `BLOCKED`. They MUST NOT return `COMPLETED` or `RETRYABLE_FAILURE`. They MUST NOT start a background worker.

Occupied slot: previous 006 set (including `BLOCKED`). `PR_CREATED` and `FAILED` release. Second start → `WorkflowBusyError`.

## Chain (delta from 006)

Discovery → planning → implementation → validation → (recovery as 006) unchanged until **validation pass**.

On validation pass:

1. Append history `COMPLETED` (PIV-complete).
2. Set `current_phase="github"`.
3. `workspaces.assert_publish_allowed(work_branch, default_branch=...)`.
4. `git_host.ensure_commit` → `push_feature_branch` → `upsert_pull_request` with five body sections and task reference.
5. Require `PullRequestIdentity.number` and `html_url` → `state="PR_CREATED"`.

Builder / diagnosis / debug / validation `execute_role` / `execute_agent` MUST NOT call `GitHost`. Implementation local `commit=True` remains allowed and MUST leave the remote unchanged until step 4.

## GitHost rules

- Push ref MUST be the task feature branch. Default/protected → `ProtectedBranchError` / `ForbiddenGitHubActionError`; not `PR_CREATED`.
- `git push` MUST NOT use `--force` or `--force-with-lease`. Commit MUST NOT use `--amend`.
- Live remote URL MUST be SSH github.com (see [research.md](../research.md) §4). Other hosts fail at the boundary (`NON_RETRYABLE`).
- `MemoryGitHost` MUST NOT contact github.com.
- Upsert: reuse PR for the same head branch; rewrite title and body every time; never open a second PR for that head.
- Body missing any of Summary, Changes, Validation performed, Known limitations, Task reference → fail (`NON_RETRYABLE`).
- Empty: no commit ahead of default and no reviewable changes → fail; 0 PRs opened.
- `forbidden(merge|approve|deploy|protected-push)` → error; state not `PR_CREATED`.

## Publish retry / blocked resume

Auth/permission/non-github.com/empty/incomplete-body → `BLOCKED`, `failure_class=NON_RETRYABLE`, `current_phase=github`, 0 diagnosis, 0 debug, 0 extra validation.

Transient hosting/network → retry GitHub only, `publish_attempt` at most 3, then `BLOCKED`.

**Resume when `BLOCKED` and `current_phase=="github"`**:

- `A` → `FAILED`, release slot, 0 extra publish.
- `B` → one GitHub retry (ensure → push → upsert), not diagnosis/debug.

**Resume when `BLOCKED` from recovery** (phase not `github`): 006 `B` cycle unchanged.

Invalid letter → `InvalidDecisionError`; stay `BLOCKED`. Not parked and not blocked → `ResumeNotParkedError`.

## Record

- `pull_request` set only on `PR_CREATED`
- `publish_attempt` as in the data model
- `steps` include PIV-complete `COMPLETED` then GitHub outcome
- Board task body unchanged; methodology unread-write; enrolled location unchanged
- 0 secrets on record, briefs, or PR body

## Isolation / stand-in

Checks inject `ModelService` + `MemoryTaskBoard` + `MemoryGitHost`. MUST NOT require a live model, `kanban.db`, github.com account, or Telegram. MUST NOT silently enroll a production repository.

## Errors

Existing orchestrator/workspace/registry/executor errors unchanged. Add `ForbiddenGitHubActionError` (subclass `OrchestratorError`) for merge/approve/deploy/protected-push/force/amend requested through this workflow. Live non-github.com remotes raise a visible GitHost/orchestrator error mapped to blocked publish, not a silent skip.

## Out of contract

- Telegram / PR-created messages
- Container restart persistence
- GitHub Enterprise Server / GitLab / HTTPS git
- Writing native Kanban retry columns
- Operator-configurable publish-retry limit
- Baking SSH keys into the image
- Automatic merge
