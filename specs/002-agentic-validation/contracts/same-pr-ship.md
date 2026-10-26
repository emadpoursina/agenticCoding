# Contract: same-PR ship

Parent-only. Applies after a validation PASS that follows REQUEST CHANGES (feature or change) or any later ship on the same run.

## First ship of the run

Unchanged from current Ship / UAT: commit, push `BRANCH`, `gh pr create` with `## Walkthrough` and `## Evidence`, emit `SHIP: ok` with `PR: <url>`.

## Reuse (same-PR)

When `PR` is already set for this run (or `gh pr view --head <BRANCH>` shows an open PR created by this run):

1. Commit pending work on `BRANCH` in `WORKTREE` (Conventional Commits; same secret/pre-push guards).
2. Push `BRANCH` (do not force-push unless the existing ship policy already requires it; default is a normal push of new commits).
3. Refresh the existing PR body: keep the same URL; update `## Walkthrough` and `## Evidence` from current plan/quickstart/implement summary and tester manifest.
4. Do **not** call `gh pr create`.
5. Emit `SHIP: ok` with the **same** `PR:` URL.

## Must not

- Open a second PR for the same run.
- Ask a worker to push or edit the PR.
- Skip walkthrough refresh because a PR already exists.
- Treat reuse as `keep-local`.

## Re-review after reuse

Launch pr-reviewer against that PR URL with `--extra` pointing at the previous report artifact (`REPORT` from the last compact header).
