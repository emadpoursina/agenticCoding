# Feature Specification: Ready worktree local files

**Feature Branch**: `skip`

**Created**: 2026-10-26

**Status**: Draft

**Input**: User description: "Make feature-loop worktrees created by the Ready gate testable by bringing in the gitignored files each project needs (secrets/local config, deps, per-worktree data), so PIVS loops can run tests in isolation without conflicts."

## Clarifications

### Session 2026-10-26

- Q: After copy or setup fails on a worktree Ready just created, what should happen to that worktree so the next Ready run can retry? → A: Remove that newly added worktree (unregister it) before reporting blocked; never remove a reused worktree.
- Q: How long may the optional setup command run before Ready treats it as a failure? → A: 10 minutes, then treat as a failed setup.
- Q: If a listed local path is a symlink, how should Ready copy it? → A: Preserve the symlink (layout as in the source tree); do not dereference. Ready still must not invent links back to the source checkout.
- Q: What should the compact report print about a successful copy, given secret files must not leak? → A: Outcome plus a file count only; no copied paths.
- Q: If other required Ready checks have already failed after the new worktree was added, should copy and setup still run? → A: Skip both; do not copy local files into a tree this run will report as blocked.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - New worktrees receive listed local files (Priority: P1)

An operator starts a feature-loop card. Ready creates a new isolated checkout for the feature branch. Tracked source is present, but the files the project actually needs to run tests (local secrets, config, installed dependencies, local data) live only as ignored files on the main checkout. After Ready succeeds, those listed files also exist in the new checkout, in the same relative layout, so later stages can run tests there without colliding with the main tree.

**Why this priority**: Without this, a successful Ready still leaves the isolated checkout untestable. That is the whole problem.

**Independent Test**: In a throwaway repository, ignore two files, list only one of them in a committed include file, run Ready so it creates a new worktree, and confirm only the listed file appears in that worktree.

**Acceptance Scenarios**:

1. **Given** a project with a committed `.worktreeinclude` at the repo root using gitignore syntax and ignored files that match it, **When** Ready successfully adds a new worktree for an existing feature branch, **Then** those matching untracked-or-ignored files are copied from the source checkout into the new worktree with paths preserved.
2. **Given** the same project, **When** Ready successfully adds a new worktree while creating a new feature branch, **Then** the same copy happens.
3. **Given** an ignored file that does not match `.worktreeinclude`, **When** Ready creates a new worktree, **Then** that file is absent from the new worktree.
4. **Given** no `.worktreeinclude` at the source checkout root, **When** Ready creates a new worktree, **Then** Ready does not copy extra files and otherwise behaves as today.

---

### User Story 2 - Optional post-create setup, without touching reused trees (Priority: P2)

Some projects need a command after the copy (install dependencies, sync a lockfile). The project may declare one optional setup command. It runs only inside a newly created worktree. If it fails, Ready is blocked with a fix the operator can act on. Reusing an existing worktree must not overwrite local files or re-run setup.

**Why this priority**: Copy alone is not enough when tests need installed deps; silent setup failure would look like Ready success and then fail later stages.

**Independent Test**: Declare a setup command that fails; confirm Ready is blocked with a FIXES line and the just-created worktree is gone so a second Ready adds a fresh tree and retries. Re-run Ready against an existing worktree whose local extra file was changed; confirm the file is not overwritten and setup does not run again.

**Acceptance Scenarios**:

1. **Given** `.specify/ready.yml` contains a `setup:` command and other required checks have not already failed, **When** Ready has just created a new worktree, **Then** that command runs with the new worktree as its working directory and is treated as failed if it runs longer than 10 minutes.
2. **Given** that setup command exits non-zero or exceeds 10 minutes, **When** Ready finishes the gate, **Then** the report is `READY: blocked`, `FIXES` includes a clear line naming the failed setup (not silent success), and the worktree added in this run is removed so a later Ready can create it again.
3. **Given** no `setup:` key, **When** Ready creates a new worktree, **Then** Ready does not run a project command and otherwise behaves as today.
4. **Given** Ready reuses an existing feature worktree (or the current checkout is already the feature worktree), **When** the gate runs, **Then** listed local files in that worktree are not overwritten and `setup:` is not executed.

---

### User Story 3 - Operators see copy/setup outcome without leaked secrets (Priority: P3)

The compact Ready report already drives the orchestrator. Copy and setup must show up there so a blocked run is diagnosable, without printing secret file contents or copied paths. Both Ready script copies and their operator docs must describe the include file and setup command so the two agent folders cannot drift.

**Why this priority**: A copy that fails quietly, or docs that mention only one of the twin scripts, recreates the original “looks ready, cannot test” failure.

**Independent Test**: Inspect a successful and a failed Ready report for CHECKS/FIXES lines; grep the Ready agent docs for `.worktreeinclude` and `setup:`; confirm the two `ready-check.sh` copies stay equivalent.

**Acceptance Scenarios**:

1. **Given** a copy and/or setup ran (or was skipped as a no-op), **When** Ready prints its compact report, **Then** CHECKS records the outcome (for copy: outcome plus a file count, never paths), and FIXES has an actionable line for each required failure.
2. **Given** copied files include secrets, **When** Ready prints output, **Then** file contents and copied paths never appear.
3. **Given** this change is delivered, **When** an operator reads Ready AGENTS.md and SKILL docs, **Then** those docs mention `.worktreeinclude` and `setup:`.

---

### Edge Cases

- Missing `.worktreeinclude` or missing `setup:` is a no-op, not a failure.
- Empty include file, or an include file that matches no ignored/untracked paths: copy transfers nothing; setup still runs on a newly created worktree if declared.
- `.worktreeinclude` only selects from untracked-or-ignored paths; tracked files are already checked out by `git worktree add` and are not part of this transfer.
- Copy or setup tool/runtime failure (missing copy tool, permission error, non-zero setup, setup longer than 10 minutes) blocks Ready; it must not report `READY: ok`. If that failure is for a worktree added in this run, Ready removes that worktree before reporting blocked so the next run is a fresh add, not a reuse that would skip copy/setup. Reused worktrees are never removed.
- If another required check has already failed after a new worktree was added, copy and setup are skipped (do not copy local files into a tree this run will report blocked). Existing worktree-lifetime behavior for those other failures stays as today.
- Listed paths that are symlinks are copied as symlinks (not dereferenced). Ready still does not create new `node_modules` / `.venv` / `.env` links back to the source checkout.
- Reused worktrees and “already on the feature branch” reuse of the current checkout skip both copy and setup.
- Malformed `.specify/ready.yml` remains a required failure as today; adding `setup:` must not break existing `checks:` behavior.
- Ready still never writes spec content, never starts `specs/`, and never ships.
- The two `ready-check.sh` copies (Ready and speckit-ready) must stay in sync, including their self-tests.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: Target repositories MUST be able to commit a `.worktreeinclude` file at the repository root. The file uses gitignore pattern syntax as an allow-list of ignored/untracked paths to bring into new feature worktrees (the same convention Cursor and Claude Code already use).
- **FR-002**: After `git worktree add` succeeds in Ready (both the existing-branch path and the new-branch path), and only when no other required check has already failed, Ready MUST copy matching untracked-or-ignored files from the source checkout (the tree where Ready was invoked) into the new worktree, preserving relative layout, including preserving symlinks (do not dereference). The specified transfer is: from the source checkout, list matches with `git ls-files --others --ignored --exclude-from=.worktreeinclude -z` and copy with `rsync -a --from0 --files-from=- ./ "$wt_path/"` (or an equivalent layout-preserving copy; on macOS, `cp -c` APFS clone is acceptable for heavy directories).
- **FR-003**: Ready MUST NOT copy ignored files that do not match `.worktreeinclude`.
- **FR-004**: If `.worktreeinclude` is absent, Ready MUST skip the copy step and continue (current behavior unchanged).
- **FR-005**: `.specify/ready.yml` MAY include an optional top-level `setup:` command string. After a successful new worktree add (and after the copy step, including a no-op copy), and only when no other required check has already failed, Ready MUST run that command inside the new worktree. If the command is still running after 10 minutes, Ready MUST treat that as a setup failure.
- **FR-006**: If `setup:` is absent, Ready MUST skip setup and continue (current behavior unchanged).
- **FR-007**: Setup is the only YAML-declared command Ready may run. Existing `checks:` types stay non-shell (`tcp`, `http`, `file_exists`, `env_var_set`). Ready MUST NOT add arbitrary per-check shell.
- **FR-008**: A failed copy or a failed setup MUST yield `READY: blocked` with a FIXES line an operator can act on. Failure MUST NOT be reported as success.
- **FR-009**: When Ready reuses an existing feature worktree, or reuses the current checkout because it is already on the feature branch, Ready MUST NOT overwrite local files there and MUST NOT run `setup:`.
- **FR-010**: The compact report MUST keep fields `READY`, `FLOW_ID`, `BRANCH`, `WORKER`, `WORKTREE`, `CHECKS`, `FIXES`. Copy and setup outcomes MUST appear under CHECKS (copy: outcome plus a file count, never copied paths); required failures MUST appear under FIXES.
- **FR-011**: Ready output MUST never print the contents or the relative paths of copied files.
- **FR-012**: Both script copies MUST stay in sync: `AiNative/docs/agents/ready/scripts/ready-check.sh` and `AiNative/docs/agents/speckit-ready/scripts/ready-check.sh` (and their paired self-tests).
- **FR-013**: One small runnable check MUST prove the copy step: a temp repo with a `.env` matched by `.worktreeinclude` ends up in the created worktree; a non-matching ignored file does not.
- **FR-014**: Ready AGENTS.md and SKILL docs MUST mention `.worktreeinclude` and `setup:` (canonical `ready/` and the `speckit-ready/` twin).
- **FR-015**: Ready MUST remain the per-card branch/layout gate: it never writes spec content, never starts `specs/`, and never ships.
- **FR-016**: If copy or setup fails for a worktree added in this run, Ready MUST unregister and remove that new worktree before reporting `READY: blocked`, so a later Ready run adds it again and retries copy/setup. Ready MUST NOT remove a reused worktree or the current checkout.
- **FR-017**: If another required check has already failed after a new worktree add, Ready MUST skip copy and setup for that run.

### Key Entities

- **Worktree include list**: Committed `.worktreeinclude` at a target repo root; gitignore-syntax allow-list of ignored/untracked paths to copy into new worktrees.
- **Source checkout**: The repository tree where Ready runs (`REPO_ROOT`); origin of copied local files.
- **Feature worktree**: Isolated git worktree Ready creates or reuses for the feature branch; destination of copy and working directory of setup, only when newly added.
- **Setup command**: Optional single command in `.specify/ready.yml` (`setup:`), intended for per-worktree install steps such as `pnpm install` or `uv sync`.
- **Compact Ready report**: Parent-parsed stdout (`READY`, `FLOW_ID`, `BRANCH`, `WORKER`, `WORKTREE`, `CHECKS`, `FIXES`).

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: In 100% of newly created feature worktrees for a project that lists local files, every listed matching file from the source checkout is present at the same relative path in the new worktree.
- **SC-002**: The proving check fails unless a matched `.env` is present in the new worktree and a non-matching ignored file is absent.
- **SC-003**: In 100% of Ready runs that reuse an existing worktree (or the current feature checkout), extra local files already in that tree are left unchanged and setup does not run.
- **SC-004**: Projects with neither an include list nor a setup command see the same Ready pass/fail outcomes they see today (no new required failures).
- **SC-005**: Every setup failure produces `READY: blocked` and at least one FIXES line; none of those runs report success.
- **SC-006**: Operators can diagnose copy/setup from CHECKS/FIXES without any secret file contents or copied paths appearing in Ready output.
- **SC-007**: After delivery, a reader of Ready AGENTS.md / SKILL docs can find both `.worktreeinclude` and `setup:` without opening the scripts.
- **SC-008**: After 100% of copy or setup failures on a newly added worktree, a subsequent Ready run is not stuck on reuse-skip: that worktree is gone and Ready adds a new one and retries.
- **SC-009**: 100% of setup commands still running after 10 minutes are reported as setup failure (`READY: blocked` with a FIXES line), never as success.

## Assumptions

Skip is active: no operator questions. Defaults below are the specified answers.

- Copy source is Ready’s invocation checkout (`REPO_ROOT`), not another worktree.
- `.worktreeinclude` is an allow-list over untracked-or-ignored paths only (gitignore syntax). Projects commit it; Ready consumes it and does not invent one for every repo.
- Copy and setup run only after a successful **new** `git worktree add` (existing-branch and new-branch paths), and only when no other required check has already failed. Reuse of an existing worktree and reuse of the current checkout skip both.
- On a new worktree that is otherwise passing required checks, setup runs even when the copy transferred zero files, as long as `setup:` is present.
- `setup:` is a single top-level command string, run with the new worktree as cwd. Non-zero exit or still running after 10 minutes is a required failure. FIXES may name the command and exit status (or timeout); CHECKS must not dump command stdout/stderr (those streams can contain secrets).
- Copy failure (missing `rsync`/equivalent, I/O error) is a required failure and, like setup failure, rolls back a worktree added in this run. `rsync` is the default copier; macOS `cp -c` APFS clone is an allowed option for heavy directories. Copy preserves symlinks. No new package dependencies.
- CHECKS reports copy outcome with a file count only; copied paths are never printed.
- Caches and build output (`dist`, `.next`, `__pycache__`) are out of this transfer unless a project lists them; Ready does not add extra denylist logic beyond the include file.
- Ready does not symlink `node_modules`, `.venv`, or `.env` back to the source checkout (that would mix branches and leak edits).
- Install-gate concerns (mounts, keys, DBs, container runtime) stay with `hermes-readiness.sh`. Per-worktree port/DB isolation is follow-up only, not this feature.
- Existing `ready.yml` `checks:` still run against the invocation checkout as today; this feature does not retarget those checks into the worktree.
- Twin `ready-check.selftest.sh` files stay in sync with the scripts; the proving check lives there (or an equally small sibling invoked by them).
- Docs in scope: `AiNative/docs/agents/ready/AGENTS.md`, `AiNative/docs/agents/ready/SKILL.md`, and the `speckit-ready/` twins. `feature-loop.md` is context only and is not required to change.
- The git branch for this run is `skip`; the spec directory is `specs/001-worktree-include-setup` and must not be inferred from the branch name.

## Out of Scope

- Symlinking `node_modules` / `.venv` / `.env` to the main checkout.
- Copying build output or caches as a built-in default (`dist`, `.next`, `__pycache__`).
- Install-gate work owned by `hermes-readiness.sh`.
- Automating per-worktree port or database isolation (follow-up only).
- Ready writing specs, starting `specs/`, or shipping.
