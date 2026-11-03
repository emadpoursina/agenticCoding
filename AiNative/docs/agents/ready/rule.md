- Ready is a pre-flight gate, not a planner. Never write `spec.md`, plan
  content, or task lists.
- Never ship, push, merge, or deploy. Ready may only prepare the feature
  work branch required by the Hermes preflight.
- A stable `READY: blocked` is never retried by the orchestrator; report the
  fix in `FIXES` and stop.
- Check only the selected worker backend (`pi`, `antigravity`, or `claude`).
  Do not require every runtime. Resolve backend via `SPECKIT_WORKER`, then
  `git config speckit.worker`, then
  `~/.config/ainative/harness-models.yaml` (`SPECKIT_HARNESS` section else
  `default`), else `antigravity`.
