# Sync Branch Command

This file defines the sync-branch command, which updates the current branch with new commits from an integration branch.

## Command Definition

```yaml
name: sync-branch
description: Update the current branch with new commits from development (merge by default)
```

## Invocation

When this command is invoked, the agent should:

1. **Parse Arguments**
   - `$ARGUMENTS` may contain:
     - Target branch name (default: `development`)
     - `--rebase` to rebase onto the target instead of merge
   - Examples: `/sync-branch`, `/sync-branch staging`, `/sync-branch --rebase`, `/sync-branch development --rebase`

2. **Pre-flight Checks**
   - Confirm the working tree is clean (`git status --porcelain`). If dirty, stop and ask the user to commit or stash first.
   - Confirm the current branch is not the target branch. If it is, stop and explain.
   - Run `git fetch origin --prune`.

3. **Show Divergence**
   - Report commits on `origin/<target>` not in `HEAD` (incoming).
   - Report commits on `HEAD` not in `origin/<target>` (local-only).
   - If there are no incoming commits, report "already up to date" and stop.

4. **Sync**
   - Default: `git merge origin/<target>`
   - With `--rebase`: `git rebase origin/<target>`
   - Do not use `--force`, `--force-with-lease`, or destructive git operations.

5. **Handle Conflicts**
   - If the sync succeeds with no conflicts, report success and show `git log --oneline -5`.
   - If conflicts occur, **stop immediately**. Do not auto-resolve.
   - List each conflicted file and present a per-file checklist for the user to resolve manually.
   - Offer to help resolve one file at a time only when the user asks.

6. **Post-sync Guidance**
   - If conflicts were resolved or many files changed, suggest running `/critic` and `/tester` before opening or updating a PR.
   - Do not push unless the user explicitly asks.

## Constraints

- Never force-push.
- Never push without explicit user request.
- Never auto-resolve merge or rebase conflicts.
- Never run `git reset --hard`, `git clean`, or other destructive commands.
- Never amend commits unless the user explicitly requests it.

## Usage Examples

```text
/sync-branch
```

→ Fetches `origin` and merges `origin/development` into the current branch

```text
/sync-branch staging
```

→ Merges `origin/staging` into the current branch

```text
/sync-branch --rebase
```

→ Rebases the current branch onto `origin/development`
