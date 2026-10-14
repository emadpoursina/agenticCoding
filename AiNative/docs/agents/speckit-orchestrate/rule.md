- The parent is a dispatcher. It never executes a stage itself, writes stage
  artifacts, runs `ready-check.sh`, or edits code because context is loaded.
- Every stage runs in a worker (Pi via `pi-harness` for Luna stages; Cursor
  `generalPurpose` Task for Grok stages). Never omit `model`. Never pass
  `inherit` on Tasks.
- Ship and UAT are parent-only; workers stay ship-dumb on every path.
- Model slugs live in the SKILL.md registry section only; never invent nearby slugs.
- Grok stages (`route`, `analyze`, `converge`, `tester`) use the Grok Task
  slug then the Grok substitute; if both are unavailable the run stops.
