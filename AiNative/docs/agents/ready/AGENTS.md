# Per-card ready (branch/layout gate)

Per-card pre-flight gate at the start of every run through the target feature loop
([feature-loop.md](../../systems/feature-loop.md)). Do not confuse with the one-time
install gate ([hermes-readiness.sh](../../knowledge/setup/hermes-readiness.sh)) or
one-time project onboarding ([new-project.md](../../knowledge/setup/new-project.md)).
Ready confirms the repo can support the loop before the first Spec Kit session starts: git state, Spec
Kit layout, and the feature branch. Ready never writes spec content, never
starts `specs/`, and never ships.

## When to invoke

- Hermes starts a new feature loop. Ready is the first state.
- Re-run Ready after `READY: blocked` is fixed. A stable `READY: blocked`
  stops the run; the orchestrator parks it.

## Inputs

- `REPO_ROOT` — the target git repository (for Hermes: the isolated task
  worktree)
- `FLOW_ID` — opaque run id minted by the parent
- `FEATURE_DESCRIPTION` — the task's feature description

## Output

Compact report (the parent parses it, never worker prose):

- `READY: ok|blocked`
- `FLOW_ID`
- `BRANCH`
- `WORKER` (`pi` or `antigravity`)
- `WORKTREE` (absolute feature worktree path on `ok`; `REPO_ROOT` itself when already on the branch)
- `CHECKS` (includes `worker-runtime` for the selected backend only; plus
  `worktree-copy` and `worktree-setup` when a feature worktree was selected)
- `FIXES`

## Worktree local files (optional)

A project may commit a `.worktreeinclude` at the repository root: a
 gitignore-syntax allow-list of ignored/untracked paths (secrets, local config,
 per-worktree data). When Ready **adds** a new worktree (existing-branch or
 new-branch path) and no other required check has failed, it copies the
 matching files from `REPO_ROOT` into the new worktree (layout preserved,
symlinks preserved, never dereferenced). Missing include file, empty file, or
zero matches is a no-op. CHECKS reports the outcome plus a file count only —
never copied paths or contents.

`.specify/ready.yml` MAY declare one optional top-level `setup:` command (the
only YAML-declared command Ready runs; `checks:` stay non-shell). After the
copy (including a zero-file copy) on a newly added worktree, Ready runs it
with the new worktree as cwd, bounded at 10 minutes. Non-zero exit or timeout
blocks Ready with a FIXES line, and the worktree added in that run is removed
so the next run retries fresh. Reused worktrees are never overwritten, never
copied into, and never re-run `setup:`. If another required check already
failed, copy and setup are skipped.

## Model behavior

- Derive a 2–4 word kebab branch slug from the feature description.
- Confirm git state (no detached HEAD, no merge in progress) and the Spec
  Kit skill layout.
- Report exactly the compact report fields. No narrative.

## Boundary

Ready is the per-card gate (branch, layout). Install facts — mounts, keys,
DBs, container runtime — are owned by the install gate
[hermes-readiness.sh](../../knowledge/setup/hermes-readiness.sh). One-time project
files are owned by [new-project.md](../../knowledge/setup/new-project.md). Do not
re-check them here.
