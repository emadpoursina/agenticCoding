- The parent is a dispatcher. It never implements application code, never writes
  `spec.md`, `plan.md`, `tasks.md`, or stage artifacts, never runs `ready-check.sh`,
  never edits code because context is loaded, and never ships from a worker session.
- Validators never write or append `tasks.md`. Workers are stage-dumb: they report a
  compact verdict and exit; they do not dispatch the next stage, write `tasks.md`,
  ship, or implement.
- Auto-merge MUST NOT be introduced; merge stays human and outside the loop.
- `keep-local` MUST NOT be inferred from `SHIP: blocked`.
- Downstream stages MUST use `FEATURE_DIR` / `.specify/feature.json` and MUST NOT
  infer the spec directory from git `BRANCH`.
- Every stage runs in a worker (Pi via `pi-harness` or Antigravity CLI via
  `antigravity-harness` for Worker-profile stages, per the Worker execution's
  `provider` (`SPECKIT_WORKER` / `speckit.worker` holds that value); host Task for Reasoning- and Validation-profile stages — Cursor
  `generalPurpose` Task, OpenCode subagent equivalent, or Hermes worker
  session). Never omit `model`. Never pass `inherit` on Tasks.
- Ship and UAT are parent-only; workers stay ship-dumb on every path.
- Feature path sequence is strictly `converge(converged) → critic → tester → ship → pr-review → uat`.
- Validation stages (`critic`, `tester`, `pr-reviewer`) use the resolved Validation-profile
  model — distinct from the Reasoning/Worker model when available — in a
  fresh session. If model independence was not achieved, report it.
- Hard ban: Parent MUST NOT feed validator Criticals directly to implement; Implement-target failures MUST enter converge first.
- Parent LOOP_BACK routing:
  - `implement` FAIL → converge (`$ARGUMENTS`) then implement ↔ converge then critic → tester.
  - `plan` or mixed FAIL → park.
  - Missing `LOOP_BACK` on FAIL → tester assertion/code as `implement`, explicit spec/plan contradiction as `plan`, else park.
  - `CONVERGE_OUTCOME: converged` while a validator FAIL is still open → park; do not re-run critic/tester/pr-review.
- Job path: after named skill `STATUS: ok` → ship (or declined); MUST NOT run pr-reviewer; UAT is not a job-path stage.
- Feature `keep-local`: critic and tester still run; skip ship, automatic pr-review, and UAT; emit `SHIP: declined`.
- No model slugs are pinned in this skill; resolve each of the three profiles
  (Reasoning, Worker, Validation) per run from the runtime (user override
  else runtime default — Hermes `config.yaml` / card profile,
  Cursor/OpenCode session default). Never invent nearby slugs, never
  cross-apply one profile's model to another, never inherit one profile's model
  into another.
- Reasoning stages (`ready`, `route`, `specify`, `clarify`, `plan`, `tasks`,
  `analyze`) use the resolved Reasoning-profile model then the configured
  fallback if one exists; if both are unavailable the run stops. Profile
  mapping and fallback policy: `docs/systems/agentic-system.md` §2 Model.
- Worker stages (`implement`, `converge`, `change`, `job`) use the resolved
  Worker-profile model then the configured fallback if one exists; if both
  are unavailable the run stops. Do not blindly rerun a partially executed
  stage through the fallback — inspect artifacts and side effects first.
