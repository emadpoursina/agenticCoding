# Claude harness

Delegates one bounded job to the official Claude Code CLI (`claude -p` headless)
and brings the result back. The orchestrator (Hermes parent or Cursor) writes the job;
the worker only executes that job.

Canonical source: AiNative `docs/agents/claude-harness/`. Host symlink:
`~/.cursor/skills/claude-harness/` → this folder.

This is not the `claude` CLI TUI and not the `@anthropic-ai/claude-agent-sdk`
npm package or Python `claude-agent-sdk`. Runtime is `claude -p` invoked via `claude-spawn.mjs`. Ready checks `claude` on
PATH and unattended authentication evidence (no model invocation).

## When to use

- Hermes dispatches a worker state executed by Claude.
- Cursor needs a Claude sub-agent (Worker-profile stages).
- `SPECKIT_WORKER=claude` (or `git config speckit.worker claude`, or aliases `claude-code`, `anthropic`).

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
| [worker-contract.md](./worker-contract.md) | Contract appended via official CLI flags |
| [claude-spawn.mjs](./claude-spawn.mjs) | CLI spawn wrapper (`status.json` / `report.json` on disk) |
| [rule.md](./rule.md) | Constraints and stop conditions |
