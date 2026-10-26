# Antigravity harness

Delegates one bounded job to the official Antigravity CLI (`agy -p` headless)
and brings the result back. The orchestrator (Hermes parent or Cursor) writes the job;
the worker only executes that job.

Canonical source: AiNative `docs/agents/antigravity-harness/`. Host symlink:
`~/.cursor/skills/antigravity-harness/` → this folder.

This is not the `agy` CLI TUI and not the community VS Code `antigravity-sdk`
npm package. Runtime is `agy -p` invoked via `agy-spawn.py`. Ready checks `agy` on
PATH and successful `agy models`.

## When to use

- Hermes dispatches a worker state executed by Antigravity.
- Cursor needs an Antigravity sub-agent (Worker-profile stages).
- `SPECKIT_WORKER=antigravity` (or `git config speckit.worker antigravity`).

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
| [worker-contract.md](./worker-contract.md) | Contract prepended to the prompt |
| [agy-spawn.py](./agy-spawn.py) | CLI spawn wrapper (`status.json` / `report.json` on disk) |
| [rule.md](./rule.md) | Constraints and stop conditions |
