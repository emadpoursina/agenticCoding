- The parent is a dispatcher. It never executes a stage itself, writes stage
  artifacts, runs `ready-check.sh`, or edits code because context is loaded.
- Every stage runs in a worker (Cursor `generalPurpose` Task, or Pi via
  `pi-harness` for Luna stages when Luna is unavailable). Never omit `model`.
  Never pass `inherit`.
- Ship and UAT are parent-only; workers stay ship-dumb on every path.
- Model slugs live in the SKILL.md registry section only; never invent nearby slugs.
- Grok stages (`route`, `analyze`, `converge`, `tester`) have no substitute:
  unavailable model stops the run.
