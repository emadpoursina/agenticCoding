- Ready is a pre-flight gate, not a planner. Never write `spec.md`, plan
  content, or task lists.
- Never `git checkout`/`switch` the current tree onto the feature branch;
  use a dedicated worktree. Never commit to a protected base branch.
- Never reimplement checks in ad-hoc shell — run `scripts/ready-check.sh`.
- A stable `READY: blocked` is never retried; report the fix in `FIXES` and stop.
- Pi enrollment (`.pi/prompts/`) is canonical; Cursor/Opencode layouts are
  legacy fallbacks only.
- Check only the selected worker backend (`pi` or `antigravity`). Do not
  require both runtimes.
