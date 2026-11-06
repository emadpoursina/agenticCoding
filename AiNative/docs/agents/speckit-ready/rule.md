- Ready is a pre-flight gate, not a planner. Never write `spec.md`, plan
  content, or task lists.
- Never `git checkout`/`switch` the current tree onto the feature branch;
  use a dedicated worktree. Never commit to a protected base branch.
- Never reimplement checks in ad-hoc shell — run `scripts/ready-check.sh`.
- A stable `READY: blocked` is never retried; report the fix in `FIXES` and stop.
- Pi enrollment (`.pi/prompts/`) is canonical; Cursor/Opencode layouts are
  legacy fallbacks only.
- Check only the selected worker backend (`pi`, `antigravity`, or `claude`).
  Do not require every runtime. Resolve backend via `SPECKIT_WORKER`, then
  `git config speckit.worker`, then
  `~/.config/ainative/harness-models.yaml` (`SPECKIT_HARNESS` section else
  `default`), else `antigravity`.
- With a `PHASE_REF`, `phase-order` is required: block unless the previous
  phase is merged into the base branch, and add no worktree or branch when
  it fails. Never fill or edit a phase plan's `**Spec:**` line.
