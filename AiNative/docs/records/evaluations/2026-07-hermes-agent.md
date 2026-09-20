# Hermes Agent

**Date:** 2026-07-19
**Status:** Queued
**Category:** harness

## Hypothesis

Hermes could complement or replace the Cursor CLI agent pane in the [harness](../../knowledge/setup/harness.md) — especially for long-running work on a VPS, scheduled automations (cron), cross-session memory, and messaging-gateway access (Telegram/Discord) while a task runs unattended. Provider-agnostic model switching (`hermes model`) may reduce lock-in vs a single IDE stack.

Relevant agentic parts: **Harness** (primary), **Agents** (skills, subagents, MCP), **Tools** (40+ built-in tools + optional MCPs).

## Source

- https://github.com/NousResearch/hermes-agent
- Docs: https://hermes-agent.nousresearch.com/docs
- MIT license; install via `curl -fsSL https://hermes-agent.nousresearch.com/install.sh | bash`

## Test plan

- [ ] Install on macOS; run `hermes doctor` and a short interactive session
- [ ] Compare against current harness: same multi-file PIV task (Plan, then implementation) — quality, friction, context handling
- [ ] Test memory/skills loop: does autonomous skill creation help on repeated task types in AiNative?
- [ ] Test MCP integration with an existing server (e.g. Prisma, MongoDB) — setup cost and context bloat
- [ ] Optional: gateway to Telegram for async status on a long Implementation pass
- [ ] Success criteria: equal or better task completion vs Cursor CLI; acceptable setup/maintenance overhead; no security regressions (command approval, isolation)
- [ ] Baseline: current Tmux + Cursor CLI harness per [harness.md](../../knowledge/setup/harness.md)

## Results

_Fill after testing._

| Run | Date | Task | Outcome | Notes |
|-----|------|------|---------|-------|
| 1 | | | | |

### Summary

What worked, what did not, surprises.

## Verdict

**Adopted** / **Rejected** / **More testing needed**

If adopted, where it was promoted:

- [ ] [agentic-system.md](../../systems/agentic-system.md) — Harness section
- [ ] [harness.md](../../knowledge/setup/harness.md)
- [ ] [tools.md](../../knowledge/tools.md)
- [ ] [agents/](../../agents/) — new or updated agent
- [ ] [decisions/](../decisions/) — ADR if architectural
- [ ] Other: _link_

If rejected, why not worth another look (or when to re-open).
