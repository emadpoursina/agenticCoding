# Spec Kit ready

Per-card pre-flight gate. Confirms git state, Spec Kit layout (Pi enrollment
canonical), and optional `.specify/ready.yml` checks; creates or reuses a git
worktree for the feature branch; returns `READY: ok|blocked`.

Canonical source: AiNative `docs/agents/speckit-ready/` (promoted from Cursor
`speckit-ready` 2026-10-07). Hermes per-card gate `ready/` shares the same
skill body and script; see [`../ready/`](../ready/).

## When to use

- First state of every card run, before `route`.
- Re-run after `READY: blocked` is fixed.

## Inputs

- `REPO_ROOT`, `FLOW_ID`, `FEATURE_DESCRIPTION`

## Outputs

- `READY: ok|blocked`, `FLOW_ID`, `BRANCH`, `WORKER` (`pi` or `antigravity`), `WORKTREE`, `CHECKS` (includes `worker-runtime`, plus `worktree-copy` and `worktree-setup` when a feature worktree was selected), `FIXES`

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

## Supporting files

| File | Purpose |
|------|---------|
| [SKILL.md](./SKILL.md) | Gate procedure (branch, layout, project checks) |
| [rule.md](./rule.md) | Constraints specific to this agent |
| [scripts/ready-check.sh](./scripts/ready-check.sh) | Executable gate (do not reimplement) |
| [scripts/ready-check.selftest.sh](./scripts/ready-check.selftest.sh) | Script self-test |
