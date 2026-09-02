---

description: "Task list for GitHub Integration (orchestrator-owned publish after PIV-complete)"
---

# Tasks: GitHub Integration

**Input**: Design documents from `/specs/007-github-integration/`

**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/github-publish.md, quickstart.md

**Tests**: Required. Spec SC-007 and FR-015 demand one pytest contract file (`personalAgent/tests/test_github_publish.py`) that fails if the seven GitHub behaviors break. Constitution IV. Tests listed below MUST be written to fail before the matching implementation.

**Organization**: Tasks are grouped by user story so each story can be implemented, tested, and delivered independently.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (US1–US4)
- Include exact file paths in descriptions

## Path Conventions

Package lives under `personalAgent/`. Source: `personalAgent/src/hermes_kanban/`. Tests: `personalAgent/tests/`.

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Confirm existing package/config; no new dependencies, no second database, no Telegram.

- [x] T001 Confirm `personalAgent/config/default.yaml` keeps `github.auth: ssh`, `allow_push: true`, `allow_pr: true`, `allow_merge: false`, and `projects: []` (do not invent a production remote or honor merge)

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: GitHost seam, overlay PR identity, orchestrator injection. MUST complete before any user story.

**⚠️ CRITICAL**: No user story work can begin until this phase is complete

- [x] T002 Add `PullRequestIdentity` (`number: int`, `html_url: str`), `ForbiddenGitHubActionError`, `GitHost` protocol (`ensure_commit`, `push_feature_branch`, `upsert_pull_request`, `forbidden`, `assert_remote_allowed`), and five PR body section labels in `personalAgent/src/hermes_kanban/github.py`
- [x] T003 Implement `MemoryGitHost` in `personalAgent/src/hermes_kanban/github.py` (in-process pushes/PRs; MUST NOT contact github.com; skip live URL enforcement)
- [x] T004 Implement github.com SSH-only URL gate (`git@github.com:…` / `ssh://git@github.com/…`; refuse HTTPS, GHES, GitLab, other hosts; do not rewrite URLs) in `personalAgent/src/hermes_kanban/github.py`
- [x] T005 Extend `WorkflowRecord` in `personalAgent/src/hermes_kanban/orchestrator.py`: type `pull_request` as `PullRequestIdentity | None`, add `publish_attempt: int = 0`, allow `current_phase=="github"`; mark overlay PR identity with a `ponytail:` comment (not a `pull_requests` table)
- [x] T006 Inject `git_host: GitHost | None = None` on `PivOrchestrator.__init__` and `from_config` in `personalAgent/src/hermes_kanban/orchestrator.py` (`from_config` omitted host → `LiveGitHost`; checks inject `MemoryGitHost`; MUST NOT default a github.com repo or `GH_TOKEN`)
- [x] T007 [P] Re-export `PullRequestIdentity`, `GitHost`, `MemoryGitHost`, `LiveGitHost`, `ForbiddenGitHubActionError` from `personalAgent/src/hermes_kanban/__init__.py`

**Checkpoint**: Foundation ready — `GitHost` can be injected; record can hold PR identity; user stories can proceed

---

## Phase 3: User Story 1 - Publish a validated feature branch as a pull request (Priority: P1) 🎯 MVP

**Goal**: After PIV-complete, the orchestrator ensures one new commit if needed, publishes the task feature branch, creates or reuses a PR against the default branch with five body sections + task reference, and wait-returns `PR_CREATED` with number + HTML URL.

**Independent Test**: Drive an eligible fixture to validation pass with `MemoryGitHost`. Start waits through publish and returns `PR_CREATED` with identity; PR targets default; body has the five sections; published branch is `feature/task-*`; enrolled location unchanged; history is `COMPLETED` then `PR_CREATED`. Second publish with more commits reuses the same PR and rewrites title/body.

### Tests for User Story 1

> **NOTE: Write these tests FIRST, ensure they FAIL before implementation**

- [x] T008 [US1] Add failing contract checks in `personalAgent/tests/test_github_publish.py` for PIV-complete then `PR_CREATED` (number + `html_url`, feature branch published, PR base = default, five body sections + task id, enrolled location unchanged, history `COMPLETED` then `PR_CREATED`, simulated remote only)
- [x] T009 [US1] Add failing checks in `personalAgent/tests/test_github_publish.py` for idempotent PR update (same number, rewritten title/body, no second PR), empty branch (0 ahead + clean → visible fail, 0 PRs), ensure-commit (dirty reviewable, 0 ahead → exactly one new commit, no `--amend`/`--force` in git argv), secrets absent from record/PR body, and `PR_CREATED` slot release

### Implementation for User Story 1

- [x] T010 [US1] Implement `ensure_commit` in `personalAgent/src/hermes_kanban/github.py`: call existing `WorkspaceManager.assert_publish_allowed`; at most one new commit; never `--amend`; skip extra commit if already ahead; empty (0 ahead + clean) and dirty-no-intent fail visibly without discard
- [x] T011 [US1] Implement `push_feature_branch` on `MemoryGitHost` in `personalAgent/src/hermes_kanban/github.py` (history-preserving; feature branch only; never `--force` / `--force-with-lease`)
- [x] T012 [US1] Implement `upsert_pull_request` on `MemoryGitHost` in `personalAgent/src/hermes_kanban/github.py` (reuse by head branch; rewrite title and body every time; return complete `PullRequestIdentity`; missing body section → `NON_RETRYABLE`)
- [x] T013 [US1] Implement PR title/body builder (Summary, Changes, Validation performed, Known limitations, Task reference) in `personalAgent/src/hermes_kanban/github.py`; incomplete body MUST fail the step, not ship
- [x] T014 [US1] After validation pass in `personalAgent/src/hermes_kanban/orchestrator.py`: append history `COMPLETED` (PIV-complete, not wait-return), set `current_phase="github"`, `assert_publish_allowed`, then `ensure_commit` → `push_feature_branch` → `upsert_pull_request`; wait-return `PR_CREATED` only when identity is complete; `_ACTIVE_STATES` treat `PR_CREATED` like former success for slot release
- [x] T015 [US1] Update success wait-return assertions from `COMPLETED` to `PR_CREATED` (inject `MemoryGitHost`) in `personalAgent/tests/test_piv_orchestrator.py`; keep parked/failed/recovery cases that never pass validation at 0 GitHost calls

**Checkpoint**: User Story 1 is independently testable: start → `PR_CREATED` with a reviewable PR on the simulated host

---

## Phase 4: User Story 2 - Orchestrator owns GitHub; builder never publishes; merge stays impossible (Priority: P1)

**Goal**: Only the orchestrator GitHub step may push or upsert a PR. Implementation/debug may still local-commit. Merge, approve-as-human, deploy, protected/default push, amend, and force-push are refused even if `allow_merge` is true.

**Independent Test**: Implementation-role local commit leaves remote unchanged (0 `push_feature_branch` / upsert). After PIV-complete, only the orchestrator GitHub step records the push. Merge/approve/deploy/push-to-default through the workflow raises; state is not `PR_CREATED`.

### Tests for User Story 2

- [x] T016 [US2] Add failing contract checks in `personalAgent/tests/test_github_publish.py` for builder-never-publish (implementation/debug: 0 GitHost push/upsert until validation pass) and merge/protected-push refuse (`forbidden` / orchestrator guards; `assert_publish_allowed` still blocks `main`/`master`/default)

### Implementation for User Story 2

- [x] T017 [US2] Implement `GitHost.forbidden(merge|approve|deploy|protected-push)` raising `ForbiddenGitHubActionError` in `personalAgent/src/hermes_kanban/github.py`; `LiveGitHost` git argv MUST omit `--force`, `--force-with-lease`, `--amend`
- [x] T018 [US2] Refuse merge/approve/deploy/protected-push at the orchestrator boundary in `personalAgent/src/hermes_kanban/orchestrator.py` even if YAML `allow_merge` is true; do not add a public `merge` method on `PivOrchestrator`
- [x] T019 [US2] Confirm implementation/debug still never publish in `personalAgent/tests/test_agent_executor.py` (local `commit=True` allowed; 0 remotes updated; builder does not call `GitHost`)

**Checkpoint**: User Stories 1 and 2: publish is orchestrator-only; merge/protected-push cannot produce `PR_CREATED`

---

## Phase 5: User Story 3 - Authenticate from the container runtime without baking secrets (Priority: P2)

**Goal**: Shipped compose forwards the host SSH agent. Live git is SSH to github.com. No private keys in the image. Contract checks still pass with `MemoryGitHost` (no live account). Live container handshake/fetch/push is a documented operator done-check.

**Independent Test**: Pytest passes without `SSH_AUTH_SOCK`. Unit gate refuses non-github.com remotes. Compose/docs define agent forwarding. 0 keys in image/docs; 0 secrets on records.

### Tests for User Story 3

- [x] T020 [US3] Add failing unit checks in `personalAgent/tests/test_github_publish.py` for `LiveGitHost` / URL gate (non-github.com and HTTPS refused before push) and `MemoryGitHost` never opening a network path to github.com

### Implementation for User Story 3

- [x] T021 [US3] Enable host SSH agent forwarding in `personalAgent/docker-compose.yml` (mount `${SSH_AUTH_SOCK}` into `hermes-personal-agent`, set `SSH_AUTH_SOCK` in the container; never COPY `id_*` or add a `~/.ssh/id_*` volume)
- [x] T022 [P] [US3] Document `SSH_AUTH_SOCK` (Docker Desktop `/run/host-services/ssh-auth.sock` vs Linux host socket) in `personalAgent/.env.example`
- [x] T023 [P] [US3] Document SSH-from-container handshake, fetch, and feature-branch push (disposable or operator-named non-critical repo only) in `personalAgent/README.md`
- [x] T024 [US3] Implement `LiveGitHost` in `personalAgent/src/hermes_kanban/github.py` via stdlib `subprocess` + `git` push of feature ref and `gh pr create` / `gh pr edit` / `gh pr list`; auth from forwarded agent or runtime env (`GH_TOKEN` never written to git config, image, `WorkflowRecord`, or PR body)
- [x] T025 [US3] Assert secrets (`SSH_AUTH_SOCK` paths, tokens, key material) are absent from `WorkflowRecord`, briefs, and PR bodies in `personalAgent/tests/test_github_publish.py`

**Checkpoint**: Runtime can authenticate when the operator forwards the agent; pytest still green without a live GitHub account

---

## Phase 6: User Story 4 - Fail publish without merging it into validation recovery (Priority: P2)

**Goal**: Publish runs only after validation pass. Auth/permission failures `BLOCKED` with 0 diagnosis/debug. Transient hosting/network retries publish only, max 3 automatic attempts, then `BLOCKED`. Blocked-publish resume `B` retries publish once (`current_phase=="github"`); recovery resume `B` stays the 006 cycle.

**Independent Test**: After validation pass, inject auth failure → `BLOCKED`, `current_phase=="github"`, 0 diagnosis, 0 debug. Two transients then success → `PR_CREATED`, 0 diagnosis. Three transients → `BLOCKED`, no fourth automatic publish. Parked/failed/recovery-blocked never PIV-complete: 0 pushes. Resume `A` → `FAILED`; resume `B` on github → one publish retry.

### Tests for User Story 4

- [x] T026 [US4] Add failing contract checks in `personalAgent/tests/test_github_publish.py` for auth-fail → `BLOCKED` without diagnosis/debug, transient two-then-success vs three-then-block, no publish before validation pass, blocked-publish resume `A`/`B`, and second start while `BLOCKED` still `WorkflowBusyError`

### Implementation for User Story 4

- [x] T027 [US4] Classify publish outcomes (`TRANSIENT` vs `NON_RETRYABLE`) separately from `classify_validation` in `personalAgent/src/hermes_kanban/orchestrator.py`; store class on the overlay when `current_phase=="github"`; increment `publish_attempt` independently of recovery `attempt`
- [x] T028 [US4] Automatic GitHub retry: transient only, `publish_attempt` at most 3, then `BLOCKED`; auth/permission/non-github.com/empty/incomplete-body → immediate `BLOCKED`; NEVER call diagnosis/debug/`execute_role` because of a GitHub failure in `personalAgent/src/hermes_kanban/orchestrator.py`
- [x] T029 [US4] Split `resume_workflow` in `personalAgent/src/hermes_kanban/orchestrator.py`: `BLOCKED` + `current_phase=="github"` + `B` → one GitHub retry (ensure → push → upsert); recovery `BLOCKED` + `B` → existing `_start_recovery_cycle(..., granted=True)`; `A` still `FAILED` + release slot; invalid letter → `InvalidDecisionError`
- [x] T030 [US4] Skip all `GitHost` calls for `HUMAN_DECISION_REQUIRED`, `FAILED`, and recovery-`BLOCKED` runs that never reached validation pass in `personalAgent/src/hermes_kanban/orchestrator.py`

**Checkpoint**: All four stories independently functional; wait-returns are `PR_CREATED` | `FAILED` | `HUMAN_DECISION_REQUIRED` | `BLOCKED` (never `COMPLETED` or `RETRYABLE_FAILURE`)

---

## Phase 7: Polish & Cross-Cutting Concerns

**Purpose**: Suite green, docs match compose, no Telegram, no production enroll

- [x] T031 [P] Run `uv run pytest tests/test_github_publish.py tests/test_piv_orchestrator.py tests/test_agent_executor.py` and `uv run ruff check src tests` in `personalAgent/`; keep 001–006 tests passing
- [x] T032 [P] Align live-container proof steps in `specs/007-github-integration/quickstart.md` with the enabled compose SSH mount (operator-named/disposable repo; pytest MUST NOT require the socket)
- [x] T033 Confirm `personalAgent/config/default.yaml` still has `projects: []` and `allow_merge: false`; do not start Telegram, restart persistence, or a second task table

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies — can start immediately
- **Foundational (Phase 2)**: Depends on Setup — BLOCKS all user stories
- **User Story 1 (Phase 3)**: Depends on Foundational — MVP
- **User Story 2 (Phase 4)**: Depends on Foundational; uses US1 GitHub sequence to prove “only orchestrator publishes”
- **User Story 3 (Phase 5)**: Depends on Foundational; LiveGitHost can land after MemoryGitHost (US1); compose/docs are independent of US4
- **User Story 4 (Phase 6)**: Depends on Foundational and the US1 publish path (must exist to fail/retry it)
- **Polish (Phase 7)**: Depends on stories intended to ship

### User Story Dependencies

- **User Story 1 (P1)**: After Phase 2 — no other story required
- **User Story 2 (P1)**: After Phase 2 — independently testable via GitHost spies; shares orchestrator publish with US1
- **User Story 3 (P2)**: After Phase 2 — compose/docs parallelizable; `LiveGitHost` after URL gate (T004)
- **User Story 4 (P2)**: After US1 publish path exists — resume `B` split must not change 006 recovery `B`

### Within Each User Story

- Tests MUST be written and FAIL before implementation
- Types/protocol before MemoryGitHost
- MemoryGitHost before orchestrator publish loop
- Core publish before retry/resume split
- Story complete before moving to next priority when staffing sequentially

### Parallel Opportunities

- T007 vs T005/T006 after T002 exists (`__init__.py` vs `orchestrator.py`)
- T022 and T023 after T021 (`.env.example` and `README.md`)
- T031 and T032 (pytest/ruff vs quickstart) once implementation is in
- US2 tests (T016) can be drafted in parallel with US1 implementation only if they do not fight `test_github_publish.py` hunks — sequential in one file is safer
- Do not parallelize multiple tasks that edit the same file (`github.py`, `orchestrator.py`, `test_github_publish.py`)

---

## Parallel Example: User Story 1

```bash
# After T008 fails (contract file exists), implementation is sequential on github.py then orchestrator.py:
Task: "Implement ensure_commit in personalAgent/src/hermes_kanban/github.py"
# then
Task: "Implement push_feature_branch / upsert_pull_request in personalAgent/src/hermes_kanban/github.py"
# then
Task: "Wire validation-pass → github → PR_CREATED in personalAgent/src/hermes_kanban/orchestrator.py"
```

## Parallel Example: User Story 3

```bash
Task: "Document SSH_AUTH_SOCK in personalAgent/.env.example"
Task: "Document SSH-from-container in personalAgent/README.md"
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Complete Phase 1: Setup
2. Complete Phase 2: Foundational (CRITICAL — blocks all stories)
3. Complete Phase 3: User Story 1 (`MemoryGitHost` + wait-return `PR_CREATED`)
4. **STOP and VALIDATE**: `uv run pytest tests/test_github_publish.py` for the PR_CREATED / body / identity / idempotent cases
5. Demo: start call returns a reviewable simulated PR — not unpublished `COMPLETED`

### Incremental Delivery

1. Setup + Foundational → GitHost injectable
2. US1 → simulated publish + `PR_CREATED` (MVP)
3. US2 → builder-never-publish + merge refuse
4. US3 → compose SSH + `LiveGitHost` + operator live proof
5. US4 → blocked publish + resume `B` split by `current_phase=="github"`
6. Each story must not break prior wait-returns or 006 recovery

### Parallel Team Strategy

With multiple developers after Phase 2:

1. Developer A: US1 (`github.py` MemoryGitHost + orchestrator publish)
2. Developer B: US2 guards + `test_agent_executor.py` (coordinate on `orchestrator.py` after US1 publish lands)
3. Developer C: US3 compose + README + `.env.example` (little overlap)
4. US4 last on `resume_workflow` so recovery `B` stays intact

---

## Notes

- Public operations stay `run_workflow` / `run_next_workflow` / `resume_workflow`
- Wait-return success is `PR_CREATED`; `COMPLETED` is history-only after validation pass
- No PyGithub, GitPython, second SQLite, Hermes GitHub skills as publisher, Telegram, or restart persistence
- Live SSH proof is operator/done-check, not required for `uv run pytest`
- github.com SSH only; never silently enroll a production repository
- [P] = different files, no incomplete-task dependency
- [US1]–[US4] map to spec user stories
- Commit after each task or logical group (when asked)
