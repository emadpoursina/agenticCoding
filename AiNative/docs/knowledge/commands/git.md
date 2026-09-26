# Git commands

- Sync the current branch with `development` using the repository's documented Git workflow.
- Removing a branch: `git branch -D [branch-name]`
- Creating a branch from development:
  - `git checkout development`
  - `git checkout -b [branch-name]`
  - `git push --set-upstream origin [branch-name]`
- Updating all branches with remote on GitHub: `git fetch origin --prune`
- `git stash push -m "Description"`

See [release-management-system.md](../../systems/release-management-system.md) for branch flow.
