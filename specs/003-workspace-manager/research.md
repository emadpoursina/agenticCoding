# Research: Workspace Manager

**Feature**: `003-workspace-manager` | **Date**: 2026-08-30

Phase 0 resolves every Technical Context choice against the spec, constitution, V0 plan §15–16 and §53, discovery, and the live `personalAgent` tree. No `[NEEDS CLARIFICATION]` remains.

## 1. Where the manager lives

**Decision**: One module in the existing control-plane package: `personalAgent/src/hermes_kanban/workspace.py`. Re-export public types from `hermes_kanban/__init__.py`. Checks in `personalAgent/tests/test_workspace_manager.py`. Git fixture repositories are built in pytest `tmp_path` (same pattern as the AiNative adapter tests), not committed as `.git` trees.

**Rationale**: `src/hermes_kanban/` already holds `ainative.py` and `projects.py`. Constitution III forbids a second control plane. Spec FR-013: reuse the existing package; do not add a second workspace or task store. One module until the file is no longer readable — do not pre-split into git/safety/identity files.

**Alternatives considered**:
- New top-level package `workspace_manager/` — extra install surface, unused.
- `hermes_kanban/workspace/` package with several modules — premature; this phase is prepare / inspect / publish-gate.
- Writing worktrees from a Hermes skill instead of this package — would skip the in-process contract later workers need.

## 2. Language, tooling, dependencies

**Decision**: Python 3.12 (`>=3.12,<3.14`) via uv. pytest + ruff already in `[project.optional-dependencies] dev`. **No new runtime dependencies.** Stdlib: `pathlib`, `dataclasses`, `subprocess`, `uuid`, `os`, `re`. Version-control operations use the `git` CLI already on PATH (host pytest and the Hermes image). No GitPython, Dulwich, or PyYAML.

**Rationale**: Constitution hard constraints. Spec assumption: no new third-party libraries. `ainative.py` already captures revision with `subprocess.run(["git", "-C", ...])`. Duplicate a small `_git` helper in `workspace.py` rather than extracting a shared git module (no unrequested abstraction).

**Alternatives considered**:
- GitPython / pygit2 — new deps, owner did not approve.
- A shared `hermes_kanban/git.py` used by adapter and manager — extra layer; adapter errors are `RevisionError`, manager errors are workspace errors.
- Adding the manager to the Hermes image — would fork Hermes (forbidden).

## 3. Isolated copy: worktree, not clone

**Decision**: Create each task working copy with `git worktree add` from the **enrolled project location**. Do not `git clone` (local or network). Do not copy the tree with `shutil`. Do not `git init` a new repository.

Layout:

```text
{workspace_root}/{project_id}/{task_id}/
```

`project_id` is the enrolled record’s `id` after `resolve_eligible_project`. `task_id` is used as a path segment only after it passes the same non-path-like identity check as project ids. The manager MUST NOT join a raw caller string onto a path before those checks.

**Rationale**: Constitution III and V0 §15 ask for isolated Git worktrees. Discovery lists isolated worktree layout as a remaining gap. Spec FR-006: versioned checkout created from the local enrolled location; no network clone; no init where none exists. A worktree leaves the enrolled checkout’s current branch unchanged (SC-001 / US1). Dirty enrolled files do not block a new task worktree (spec edge case). Native git already refuses checking out the same branch in two worktrees, which matches “do not share that mutable copy.”

The V0 nested `repository/` + `worktree/` sketch is YAGNI: that layout assumed a clone plus a worktree of the clone. Attaching worktrees to the enrolled repo needs one directory per task.

**Alternatives considered**:
- `git clone --local` into the workspace root — duplicates objects, extra step, not the native worktree capability.
- `shutil.copytree` of the enrolled tree — not a versioned checkout; would copy dirty enrolled files into the task copy.
- Nested `project/task/repository` + `project/task/worktree` — two directories per task with no extra safety this phase.

## 4. Persistence: return host fields, do not add a store

**Decision**: Prepare returns an in-memory record whose workspace fields match Hermes Kanban columns already discovered: `workspace_path`, `branch_name`, `project_id`. Also return correlation fields Hermes does not already store (`execution_id`, `workspace_id`, optional `worker_id`). **This phase does not read or write `kanban.db` or `projects.db`.** No `workspace.db`. No sidecar identity file inside the working copy (that would show as dirty).

Later executor/observability work maps:

| Prepare field | Native Kanban field (later) |
|---|---|
| `path` | `workspace_path` |
| `branch` | `branch_name` |
| `project_id` | `project_id` |
| (implementation may set) | `workspace_kind` = worktree |

`execution_id` / `workspace_id` stay on the prepare record until a later spec asks to persist them.

**Rationale**: Spec FR-013 and constitution III: no second task or workspace store. Project registry already established “in-process records now, native DB later.” This phase has no Kanban task id to update.

**Alternatives considered**:
- Writing `kanban.db` from prepare — couples workspace setup to a live Hermes home and a pre-existing task row; out of scope.
- A new SQLite file — second workspace store (FR-013).
- `.hermes-workspace-id` in the worktree — dirties the copy and can leak into commits.

## 5. Workspace root configuration

**Decision**: Load only `workspace.root` from a caller-supplied operational YAML path (production: `personalAgent/config/default.yaml`, already `root: /workspaces`). Other keys (`projects:`, `ainative:`, `github:`, …) are ignored here. `ProjectRegistry.from_config` on the same file supplies eligibility.

Construction / `from_config` validates: key present, non-empty, path exists, is a readable directory. Failure → `InvalidWorkspaceRootError`. MUST NOT default to `/workspaces`, `$HOME`, `./workspaces`, or `WORKSPACE_ROOT` env.

`ponytail:` a line-oriented scan of the `workspace:` mapping for a single `root` scalar (same ceiling as `load_ainative_settings`). Upgrade: owner-approved PyYAML if the block grows. Do not share a YAML helper with `projects.py` this phase.

**Rationale**: FR-001, FR-002, FR-016. Compose already mounts `${WORKSPACE_ROOT}:/workspaces`; application code reads the configured path, not the host env. Empty `projects: []` remains valid for production until the owner enrolls a repo; tests pass a temp root and a temp enrolled fixture.

**Alternatives considered**:
- Reading `WORKSPACE_ROOT` when YAML is missing — silent host substitute; SC and FR-002 forbid it.
- Creating the root if missing — would hide misconfiguration; spec says fail.
- Requiring `/workspaces` to exist during host pytest against production config — tests never bind to that path.

## 6. Public operations

**Decision**: `WorkspaceManager` exposes exactly the spec names:

| Operation | Success when |
|---|---|
| `prepare_workspace(project_id, task_id, *, worker_id=None)` | Eligible project, valid task id, safe git copy on `feature/task-<task_id>` |
| `inspect_workspace(project_id, task_id)` | Existing valid copy for that project+task |
| `assert_publish_allowed(branch, *, default_branch)` | `branch` is not `main`, `master`, or `default_branch` |

`prepare_workspace` MUST call `registry.resolve_eligible_project(project_id)` first (same `UnknownProjectError` / `DisabledProjectError` / `InvalidProjectLocationError`). It MUST NOT invent a project path.

`assert_publish_allowed` is a pure name gate. It MUST NOT push. `default_branch` is required so a project whose default is `develop` (or any non-main name) is still protected. Success means “allowed later” (this phase does not publish). Failure is `ProtectedBranchError`.

**Rationale**: FR-003, FR-008, FR-011, FR-015. Optional `worker_id` matches FR-012 without inventing workers.

**Alternatives considered**:
- `assert_publish_allowed(branch)` only — cannot protect a non-`main` default.
- Looking up `project_id` inside the publish gate — extra coupling for a name check the caller already has from the project record.
- Returning `bool` instead of raising — weaker than the rest of the package’s distinct errors.

## 7. Feature branch and protected set

**Decision**: Work branch is always `feature/task-<task_id>` with no extra slug. Protected names: `main`, `master`, and the eligible project’s `default_branch` (from `ProjectRecord.default_branch`, which already applies the registry’s `main` fallback). Prepare MUST call the same protected check before `git worktree add` / before returning a reused copy. If the computed work branch is protected, fail with `ProtectedBranchError` and do not check out that branch.

Base ref for a **new** worktree: the project’s default branch in the enrolled repository. After a successful fetch (when a remote exists), prefer `{remote}/{default_branch}` if that ref exists; otherwise fail (cannot refresh the default). When no remote exists, use the local default branch. Missing local default → fail; do not guess `master` if the record says `main`.

**Rationale**: FR-007, FR-008, spec assumptions on branch form and protected set.

**Alternatives considered**:
- `feature/<task-id>-<slug>` from V0 — spec chose no extra slug.
- Allowing `task_id` that produces a protected work branch to pass because the formula “usually” cannot match `main` — SC-002 requires the gate anyway.

## 8. Git safety sequence

**Decision**: Before a copy is returned as ready:

1. Confirm enrolled location is a git work tree (`rev-parse --is-inside-work-tree`). Else `InvalidProjectRepositoryError`. Do not `git init`.
2. Confirm default branch exists (`rev-parse --verify`). Else `MissingDefaultBranchError`.
3. `git remote` — if any remotes, record identity (`remote get-url` for `origin` if present, else the first remote). If none, omit remote identity; skip fetch.
4. If a remote exists: `git fetch` that remote from the enrolled location. Fetch failure → `GitRefreshError`. MUST NOT continue as if default were current. Fetch MUST NOT check out or reset the enrolled branch.
5. Work branch must not be protected.
6. Working copy current branch, dirty flag (`status --porcelain`; untracked counts as dirty), and (for inspect / dirty inspect) a change summary.

After local file changes, `inspect_workspace` reports branch, dirty flag, and a summary of changed paths (porcelain names), not a full diff dump and not model text.

Allowed git subcommands: `status`, `rev-parse`, `branch`/`symbolic-ref`, `remote`, `fetch`, `diff`/`status --porcelain`, `worktree add`, `worktree list`, `show-ref`. **Forbidden in this module**: `push`, `reset --hard`, `clean`, `checkout` of the enrolled tree, `branch -D`, `worktree remove`, `init`, `clone`.

**Rationale**: V0 §16 before/after checks; FR-009–FR-011; FR-015 (no publish). Dirty reuse must not auto-repair (FR-010).

**Alternatives considered**:
- `git pull` on the feature branch during reuse — mutates a reused copy; spec only requires reuse when clean, not rebase onto latest default.
- Skipping fetch on reuse — FR-009 still requires refresh when a remote exists; fetch updates refs without merging the feature branch.
- Using `git checkout` in the enrolled location to create the branch first — would change the enrolled current branch (forbidden).

## 9. Reuse, dirty, invalid, isolation

**Decision**:

| Existing path | Behavior |
|---|---|
| Missing | `git worktree add -b feature/task-<id> <path> <base>` (or `worktree add <path> <branch>` if the branch already exists and is not checked out elsewhere) |
| Valid git copy, expected branch, clean, same project+task | Reuse. Same `workspace_id`. New `execution_id`. |
| Valid copy, uncommitted changes (including untracked) | `DirtyWorkspaceError`. Leave files untouched. Do not reset/clean. Do not touch other task paths. |
| Path exists but is not a git copy, wrong branch, or different repo/task | `InvalidWorkspaceError`. Do not delete or overwrite. |
| Feature branch already checked out in another worktree (including enrolled) | Fail with `InvalidWorkspaceError` (or git’s already-checked-out error mapped to it). Do not share that copy. |
| Sibling task directories under the root | Untouched. Prepare MUST NOT `rmtree` them to make room. |

`workspace_id` is deterministic: `ws-{project_id}-{task_id}` (stable for the same project+task copy). `execution_id` is `uuid.uuid4().hex` per successful prepare.

Two different `task_id` values MUST resolve to two different directories (`{root}/{project_id}/{task_a}` vs `{root}/{project_id}/{task_b}`).

**Rationale**: FR-005, FR-010, FR-012, FR-014, US2/US3.

**Alternatives considered**:
- Auto-reset dirty copies — forbidden.
- Random `workspace_id` stored on disk — extra state; sidecars dirty the tree.
- One worktree per project with branch switching — shares a mutable copy across tasks (forbidden).

## 10. Task identity

**Decision**: `task_id` must be a non-empty string and must fail the same path-like predicate as project ids (`/`, `\`, `..`, extra segments, `.`). Empty/missing → `InvalidTaskIdError`. Path-like → `InvalidTaskIdError`. Do not invent a task id. Reuse `projects._path_like_id` (import the existing function; do not copy a third variant). After validation, join `{workspace_root}/{project.id}/{task_id}` using the enrolled `project.id` and the validated task id — never join before the check.

`worker_id` if omitted or `None`: leave `PreparedWorkspace.worker_id` as `None`. If supplied, store the string; do not invent a worker. Empty string is treated as omitted.

**Rationale**: FR-004, FR-012. Spec forbids joining unsanitized identities onto paths; the registry already solved this with allow-then-join.

**Alternatives considered**:
- `UnknownProjectError` for bad task ids — wrong boundary; task ids are not project ids.
- Restricting task ids to `[A-Za-z0-9._-]+` — spec does not require it; examples are tokens like `123`.

## 11. Correlation identity contents

**Decision**: `CorrelationIdentity` / fields on `PreparedWorkspace`:

| Field | Rule |
|---|---|
| `task_id` | Caller task id (validated) |
| `execution_id` | Unique per successful prepare |
| `project_id` | Enrolled id |
| `workspace_id` | Stable `ws-{project_id}-{task_id}` |
| `worker_id` | Optional |

MUST NOT include instruction text, diffs of file contents, chain-of-thought, or model transcripts. Inspect’s change summary is path status lines only.

**Rationale**: FR-012, V0 §53, spec “no private reasoning.”

**Alternatives considered**:
- Embedding `git diff` in the identity record — not identity; inspect already covers change summary.
- Requiring `worker_id` — this phase does not assign workers.

## 12. Errors

**Decision**: Distinct exception types, all subclasses of `WorkspaceError`:

| Type | When |
|---|---|
| `InvalidWorkspaceRootError` | Missing/empty/non-directory/unreadable workspace root |
| `InvalidTaskIdError` | Empty or path-like `task_id` |
| `InvalidProjectRepositoryError` | Enrolled location is not a git work tree |
| `MissingDefaultBranchError` | Declared default branch is not a ref |
| `ProtectedBranchError` | Work branch or publish target is `main` / `master` / project default |
| `DirtyWorkspaceError` | Reuse refused because the existing copy has uncommitted changes |
| `InvalidWorkspaceError` | Missing, not a work tree, mismatched task, wrong branch, branch already checked out elsewhere, or inspect of a bad path |
| `GitRefreshError` | Remote exists and fetch (or missing `{remote}/{default}` after fetch) failed |

Project eligibility errors propagate unchanged from `ProjectRegistry` (`UnknownProjectError`, `DisabledProjectError`, `InvalidProjectLocationError`).

**Rationale**: Spec wants visible, distinct failures. Tests assert types. Do not return `None` or empty records.

**Alternatives considered**: One `WorkspaceError` with a code enum — slightly less code, worse call-site checks. Swallowing registry errors into `InvalidWorkspaceError` — would hide unknown vs disabled vs bad location.

## 13. Checks and fixture

**Decision**: One pytest file covering the six SC-006 contract behaviors plus: path-like task id, missing workspace root, unknown/disabled project, enrolled path not a git repo, missing default branch, dirty enrolled location still allows a new task worktree, two tasks → two paths, reuse keeps `workspace_id` and rotates `execution_id`, inspect of clean vs dirty, `assert_publish_allowed` refuses protected names including a non-`main` default, fetch failure fails prepare, no `push`/reset, enrolled current branch unchanged, sibling directories under the root are not deleted.

Fixture: `git init` + commit in `tmp_path` (copy `tests/fixtures/projects/standard/` then init, matching adapter tests). Optional second remote-bearing fixture uses a second local bare repo as `origin` — still no GitHub account. Production `projects: []` unchanged. Tests MUST NOT use a live production checkout.

**Rationale**: Constitution IV; spec SC-006; V0 disposable fixture.

**Alternatives considered**: Only Docker e2e — slower, not required to prove the in-process contract. Checking out a real application repo — forbidden.
