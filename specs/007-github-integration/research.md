# Research: GitHub Integration

**Feature**: `007-github-integration` | **Date**: 2026-09-01

Phase 0 resolves Technical Context against the spec, constitution, V0 plan Phase 5, the 006 orchestrator contract, `personalAgent/src/hermes_kanban/{orchestrator,workspace,executor}.py`, and `personalAgent/docker-compose.yml`. Clarify session 2026-09-01 is closed. No `[NEEDS CLARIFICATION]` remains.

## 1. Where publish lives

**Decision**: Keep the three public operations on `PivOrchestrator`. After validation pass, the orchestrator writes a history `COMPLETED` (PIV-complete) row, then runs a GitHub sequence it owns. Do not add a second orchestrator, a Hermes GitHub skill invocation, or a background worker.

Put the hosting seam in a new module `personalAgent/src/hermes_kanban/github.py` (`GitHost` protocol + `MemoryGitHost` + `LiveGitHost`). The orchestrator calls that seam; it does not reimplement worktree safety. Re-export public types from `hermes_kanban/__init__.py`.

Contract checks for this phase live in `personalAgent/tests/test_github_publish.py`. Update `test_piv_orchestrator.py` so former wait-return `COMPLETED` success paths now continue through a simulated host and return `PR_CREATED`.

**Rationale**: Spec FR-001/FR-002/FR-014: orchestrator-owned publish, builder never publishes, reuse Git safety. Constitution II: `orchestrator.py` is already the recovery loop; a second file for git-push/PR is the smaller diff than stuffing `gh`/`git push` into the same module. Constitution III “prefer GitHub skills” does **not** apply as the publish actor — skills run as workers and would violate US2.

**Alternatives considered**:
- Publish inside `orchestrator.py` only — file already owns chain + recovery; hosting I/O would bury the state machine.
- Call Hermes `github-pr-workflow` skill via `execute_agent` — builder/worker-owned; forbidden.
- New HTTP service — extra process; V0 is in-process.

## 2. Language, tooling, dependencies

**Decision**: Unchanged. Python 3.12 via uv. pytest + ruff. **No new runtime libraries** (no PyGithub, no GitPython). Live git transport: stdlib `subprocess` + `git`. Live pull-request create/update: `gh` CLI (`gh pr create` / `gh pr edit` / `gh pr list`) when present. Simulated path: in-memory host, no `gh`, no network.

**Rationale**: Constitution hard constraint; spec assumption; FR-015.

**Alternatives considered**: PyGithub / httpx — new dependency. REST-only urllib + token — extra code when `gh` is the platform CLI already assumed by Hermes GitHub skills; keep urllib out unless `gh` is missing and an owner later asks.

## 3. GitHost seam (simulated vs live)

**Decision**:

```text
GitHost
  assert_remote_allowed(remote_url)     # github.com SSH only on live
  ensure_commit(copy, branch, default)  # at most one new commit; never amend
  push_feature_branch(copy, branch)     # history-preserving; never --force
  upsert_pull_request(...)              # create or reuse by head branch; rewrite title+body
  forbidden(...)                        # merge / approve / deploy / protected push → error
```

`MemoryGitHost` records pushes and pull requests in process. Contract checks inject it. It MUST NOT enroll or call github.com.

`LiveGitHost` uses the isolated copy’s git: `git push <remote> HEAD:refs/heads/<feature>` (no `--force`, no `--force-with-lease`). PR identity from `gh`. Auth for git is SSH agent (`git@github.com`). `gh` may use host-forwarded auth or `GH_TOKEN` / `GH_HOST` from **environment or a mounted runtime secret**, never from git config written by this workflow, never copied into the image, never stored on `WorkflowRecord` or PR body.

**Rationale**: FR-005 (SSH git + runtime secrets allowed); FR-015 (simulated remote for checks); clarification (github.com only).

**Alternatives considered**: Always hit github.com in pytest — requires a live account; forbidden for contract checks. HTTPS git remotes — out of scope; fail at the trust boundary.

## 4. github.com remote gate

**Decision**: Live publish MAY proceed only when the enrolled copy’s push URL is SSH to github.com:

- `git@github.com:owner/repo.git`
- `ssh://git@github.com/owner/repo.git`

GitHub Enterprise Server, GitLab, HTTPS `https://github.com/...`, and any other host → visible error at the orchestrator/GitHost trust boundary **before** push. Do not silently rewrite the URL to github.com.

`MemoryGitHost` skips live URL enforcement so fixture remotes (or no remote) still prove the state machine.

Declared YAML `repository: github.com/owner/repo` remains a human label; the **git remote URL** is the live gate.

**Rationale**: Clarification Q5; FR-005.

**Alternatives considered**: Accept HTTPS github.com — contradicts SSH-only V0. Parse only the YAML `repository` field — would not catch a wrong `origin`.

## 5. Ensure-commit and history

**Decision**: Orchestrator (via GitHost), never the builder:

1. Confirm HEAD branch is the task feature branch (`feature/task-<id>`). Call existing `WorkspaceManager.assert_publish_allowed`.
2. Count commits ahead of the project default: `git rev-list --count <default>..HEAD`.
3. Inspect porcelain (existing inspect / `_porcelain` equivalent).
4. Ahead ≥ 1 and clean (or only intentional artifacts) → do not add a commit.
5. Ahead 0 and reviewable dirty files → **one** `git commit` (no `--amend`, no rebase). Conventional message; wording is an implementation choice; MUST include the task id.
6. Ahead 0 and clean → fail visibly (`NON_RETRYABLE` publish); do not open an empty PR.
7. Dirty with no reviewable intent → fail visibly; MUST NOT `reset --hard` / discard.
8. Ahead ≥ 1 and reviewable dirty → one **new** commit to make the tree publishable (not an empty ensure-commit). Still never amend.

`git push` MUST NOT include `--force` / `--force-with-lease`. Amend flags MUST NOT be passed.

**Rationale**: FR-011; clarify Q2.

**Alternatives considered**: `git commit --amend` when HEAD is unpublished — rejected in clarify. Force-push to “fix” the remote — forbidden.

## 6. Pull request upsert and identity

**Decision**: Identity of “the” PR is **head branch = work branch** on github.com, base = project default branch.

- No open/closed-duplicate policy beyond: find existing PR for that head; if found, **edit title and body**; if not, **create**. MUST NOT open a second PR for the same head.
- Every successful publish, including updates, rewrites title and body. Push without rewrite is a failed update (`NON_RETRYABLE` control-plane bug, not a hosting retry).
- Body MUST contain five labeled sections: Summary, Changes, Validation performed, Known limitations, Task reference. Missing section → fail the step (do not ship).
- `WorkflowRecord.pull_request` becomes `PullRequestIdentity | None` with `number: int` and `html_url: str`. Either missing → must not return `PR_CREATED`.

**Rationale**: FR-004, FR-008; clarify Q1 and Q4.

**Alternatives considered**: Push-only update — rejected in clarify. Store identity only in summary prose — forbidden.

## 7. Success wait-return and PIV-complete history

**Decision**: Replace wait-return `COMPLETED` on the success path with `PR_CREATED`. After validation pass, append a `COMPLETED` **history** `StepRecord` (PIV-complete), then publish. Start/resume MUST NOT return `COMPLETED` once this phase is in effect.

Slot: `PR_CREATED` releases (same as former `COMPLETED`). `FAILED` releases. Parked and `BLOCKED` occupy.

**Rationale**: FR-001, FR-009, FR-010; spec assumptions.

**Alternatives considered**: Keep returning `COMPLETED` and add `pull_request` as a side field — contradicts SC-001 / wait-return rules.

## 8. Publish failures vs recovery

**Decision**: Publish runs only after validation pass. Classify **publish** outcomes separately from `classify_validation`:

| Signal | Class | Orchestrator |
|---|---|---|
| Auth / permission / non-github.com remote / protected push attempt / merge request / incomplete PR body / empty branch / dirty-no-intent | `NON_RETRYABLE` | `BLOCKED`, 0 diagnosis, 0 debug, 0 extra validation |
| Network timeout / hosting unavailable | `TRANSIENT` | Retry **publish only**, max 3 automatic attempts, then `BLOCKED` |
| Incomplete body generated by us | `NON_RETRYABLE` | Fail/block; do not treat as hosting blip |

`publish_attempt` on the overlay counts automatic publish tries (1-based on first try). Independent of recovery `attempt`. After three transient publish failures → `BLOCKED`, no fourth automatic publish.

`current_phase` during publish / blocked-publish is `github`. Resume `B` when `current_phase=="github"` retries **publish once**. Resume `B` when blocked from recovery keeps the 006 cycle shape. Resume `A` still `FAILED` + release.

Parked / `FAILED` / recovery-`BLOCKED` that never passed validation MUST NOT call GitHost.

**Rationale**: FR-006, FR-007, US4; blocked letter protocol reused.

**Alternatives considered**: Feeding push failures into diagnosis/debug — forbidden. Sharing recovery `attempt` for publish — would corrupt the validation budget.

## 9. Config and forbidden actions

**Decision**: Read existing `github:` keys from the same YAML (`auth: ssh`, `allow_push`, `allow_pr`, `allow_merge`). V0 requires `allow_push` and `allow_pr` true to publish. `allow_merge` MUST remain false; even if an operator sets it true, merge/approve/deploy/protected-push MUST still raise `ForbiddenGitHubActionError` at the boundary (constitution V wins). No public `merge` method on `PivOrchestrator`. Tests call `GitHost.forbidden` / orchestrator guards to prove refuse.

**Rationale**: `config/default.yaml` already has the flags; constitution V; FR-003/FR-016.

**Alternatives considered**: Honor `allow_merge: true` — violates Human Authority.

## 10. SSH runtime (compose)

**Decision**: This phase **does** change shipped compose/docs (clarify Q3). Enable host SSH agent forwarding in `personalAgent/docker-compose.yml`:

- Mount `${SSH_AUTH_SOCK}` into the container
- Set `SSH_AUTH_SOCK` inside the container to the mount path
- Do not `COPY` keys into the image; do not add a key volume of `~/.ssh/id_*`

Document Docker Desktop (`/run/host-services/ssh-auth.sock`) vs Linux (`SSH_AUTH_SOCK` from the host). Operator done-check: `ssh -T git@github.com`, then fetch, then feature-branch push from **inside** `hermes-personal-agent`. Contract pytest MUST NOT require that socket.

**Rationale**: FR-005; US3; previous compose freeze does not apply to this SSH change.

**Alternatives considered**: Operator-only undocumented bind-mount — rejected in clarify. Baking keys — forbidden.

## 11. Checks

**Decision**: One new pytest module for SC-007’s seven GitHub behaviors, using `MemoryGitHost` (and optionally a local bare git remote as the “simulated remote”). Live container SSH proof is documented in quickstart, gated by operator-named/disposable repo — not required to pass `uv run pytest`. `config/default.yaml` stays `projects: []`.

006 tests that asserted wait-return `COMPLETED` MUST be updated in the same implementation so the suite stays green.

**Rationale**: FR-015, SC-007, constitution IV/V.

**Alternatives considered**: Live GitHub in CI — silent production risk and account requirement.
