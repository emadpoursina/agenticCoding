# Pi harness

Delegates one bounded job to Pi and brings the result back. The orchestrator
(Hermes parent or Cursor) writes the job; Pi only executes that job.

Canonical source: AiNative `docs/agents/pi-harness/` (promoted from Cursor
`pi-harness` 2026-10-13, Pi 1.2.0). Host symlink:
`~/.cursor/skills/pi-harness/` → this folder. Pi has built-in MCP support
since 1.0 (Codemode); `pi-mcp-adapter` is opt-in, not required.

## When to use

- Hermes dispatches a worker state executed by Pi.
- Cursor needs a Pi sub-agent (worker-role stages or explicit Pi offload).

## Inputs

- Goal, cwd (project root / feature `WORKTREE`), files to read, done criteria,
  what **not** to do, report format, `--model` (required — no harness default).

## Outputs

- `report.json` (`lifecycle` + `workerStatus`/`reportValid`), diff review,
  follow-up decision. See [SKILL.md](./SKILL.md).

## Supporting files

| File | Purpose |
|------|---------|
| [SKILL.md](./SKILL.md) | Spawn, monitor, and report-back procedure |
| [worker-contract.md](./worker-contract.md) | Contract appended to every Pi prompt |
| [pi-spawn.mjs](./pi-spawn.mjs) | Spawn wrapper (keeps event stream on disk) |
