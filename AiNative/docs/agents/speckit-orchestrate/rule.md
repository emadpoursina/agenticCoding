- The parent is a dispatcher. It never executes a stage itself, writes stage
  artifacts, runs `ready-check.sh`, or edits code because context is loaded.
- Every stage runs in a worker (Pi via `pi-harness` or Antigravity SDK via
  `antigravity-harness` for Worker-profile stages, per `SPECKIT_WORKER` /
  `speckit.worker`; host Task for Reasoning- and Validation-profile stages — Cursor
  `generalPurpose` Task, OpenCode subagent equivalent, or Hermes worker
  session). Never omit `model`. Never pass `inherit` on Tasks.
- Ship and UAT are parent-only; workers stay ship-dumb on every path.
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
- Validation stages (`critic`, `tester`) use the resolved Validation-profile
  model — distinct from the Reasoning/Worker model when available — in a
  fresh session. If model independence was not achieved, report it.
