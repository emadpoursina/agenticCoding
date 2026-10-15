- The parent is a dispatcher. It never executes a stage itself, writes stage
  artifacts, runs `ready-check.sh`, or edits code because context is loaded.
- Every stage runs in a worker (Pi via `pi-harness` for worker stages; host
  Task for reasoning stages — Cursor `generalPurpose` Task, OpenCode subagent
  equivalent, or Hermes worker session). Never omit `model`. Never pass
  `inherit` on Tasks.
- Ship and UAT are parent-only; workers stay ship-dumb on every path.
- No model slugs are pinned in this skill; resolve both roles per run from
  the runtime (user override else runtime default — Hermes `config.yaml` /
  card profile, Cursor/OpenCode session default). Never invent nearby slugs.
- Reasoning stages (`route`, `analyze`, `converge`, `tester`) use the resolved
  reasoning model then the runtime fallback if one exists; if both are unavailable the run stops.
