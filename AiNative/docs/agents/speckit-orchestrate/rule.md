- The parent is a dispatcher. It never executes a stage itself, writes stage
  artifacts, runs `ready-check.sh`, or edits code because context is loaded.
- Every stage runs in a worker (Pi via `pi-harness` or Antigravity SDK via
  `antigravity-harness` for worker stages, per `SPECKIT_WORKER` /
  `speckit.worker`; host Task for reasoning and validation stages — Cursor
  `generalPurpose` Task, OpenCode subagent equivalent, or Hermes worker
  session). Never omit `model`. Never pass `inherit` on Tasks.
- Ship and UAT are parent-only; workers stay ship-dumb on every path.
- No model slugs are pinned in this skill; resolve each of the three roles
  (reasoning, worker, validation) per run from the runtime (user override
  else runtime default — Hermes `config.yaml` / card profile,
  Cursor/OpenCode session default). Never invent nearby slugs, never
  cross-apply one role's model to another, never inherit one role's model
  into another.
- Reasoning stages (`plan`, `route`, `analyze`, `converge`) use the resolved
  reasoning model then the runtime fallback if one exists; if both are
  unavailable the run stops.
- Validation stages (`critic`, `tester`) use the resolved validation model —
  distinct from the reasoning/worker model — in a fresh session.
