# Cursor harness

Delegates one bounded job to a local Cursor agent through the official
TypeScript SDK (`@cursor/sdk`) and brings the result back. The orchestrator
(Hermes parent or Cursor) writes the job; the worker only executes that job.

Canonical source: AiNative `docs/agents/cursor-harness/`. Host symlink:
`~/.cursor/skills/cursor-harness/` → this folder.

This is not the `agent` CLI TUI, not a cloud agent VM, and not the SDK bridge.
Runtime is `Agent.create({ local })` invoked via `cursor-spawn.mjs`.
Docs: [TypeScript SDK](https://cursor.com/docs/sdk/typescript.md).
The in-product `/sdk` skill is a Cursor onboarding aid; this harness is the
worker wrapper.

## When to use

- Hermes dispatches a worker state executed by the Cursor SDK.
- Cursor needs a Cursor-SDK sub-agent (Worker-profile stages).
- `SPECKIT_WORKER=cursor` (or `git config speckit.worker cursor`, or alias `cursor-sdk`).

## Inputs

- Goal, cwd (project root / feature `WORKTREE`), files to read, done criteria,
  what **not** to do, report format, `--model` (required — no harness default).

## Outputs

- `report.json` (`lifecycle` + `workerStatus`/`reportValid` + `totalCostUsd`/`numTurns`/`sessionId`, schemaVersion 1), diff review,
  follow-up decision. See [SKILL.md](./SKILL.md).

## Supporting files

| File | Purpose |
|------|---------|
| [SKILL.md](./SKILL.md) | Spawn, monitor, and report-back procedure |
| [worker-contract.md](./worker-contract.md) | Contract prepended to the user message |
| [cursor-spawn.mjs](./cursor-spawn.mjs) | SDK spawn wrapper (`status.json` / `report.json` on disk) |
| [package.json](./package.json) | Pins `@cursor/sdk` and `zod` for a local install |
| [rule.md](./rule.md) | Constraints and stop conditions |
