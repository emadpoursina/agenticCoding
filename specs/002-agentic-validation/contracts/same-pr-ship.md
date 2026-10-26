# Contract: same-PR ship

Parent-only. Applies after a validation PASS that follows REQUEST CHANGES (feature or change) or any later ship on the same run.

## First ship of the run

Commit, push `BRANCH`, restamp local manifest (`specs/<flow>/evidence.md`) with the pushed commit SHA and re-run any HEAD-sensitive validation commands on the pushed SHA so captures match that head, leaving it uncommitted per validation-layer evidence hygiene, `gh pr create` with `## Walkthrough` and `## Evidence` (published without a SHA-only follow-up commit; do not invent a second PR), emit `SHIP: ok` with `PR: <url>`.

## Reuse (same-PR)

When `PR` is already set for this run (or `gh pr view --head <BRANCH>` shows an open PR created by this run):

1. Commit pending work on `BRANCH` in `WORKTREE` (Conventional Commits; same secret/pre-push guards).
2. Push `BRANCH` (do not force-push unless the existing ship policy already requires it; default is a normal push of new commits).
3. Restamp local manifest (`specs/<flow>/evidence.md`) with the pushed commit SHA (`git rev-parse HEAD`), re-running any HEAD-sensitive validation commands on the pushed SHA so captures match that head, leaving the restamp uncommitted per validation-layer evidence hygiene.
4. Refresh the existing PR body: keep the same URL; update `## Walkthrough` and publish that table in PR `## Evidence` without a SHA-only follow-up commit.
5. Do **not** call `gh pr create` (do not invent a second PR).
6. Emit `SHIP: ok` with the **same** `PR:` URL.

## Must not

- Open a second PR for the same run.
- Ask a worker to push or edit the PR.
- Skip walkthrough refresh because a PR already exists.
- Treat reuse as `keep-local`.

## Re-review after reuse

Launch pr-reviewer against that PR URL with `--extra` pointing at the previous report artifact (`REPORT` from the last compact header).
