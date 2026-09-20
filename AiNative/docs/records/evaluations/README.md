# Evaluations

Candidates with potential — new models, tools, MCP servers, agent patterns, harness changes — that are worth testing before they become canonical.

**Not** proven yet (that is [knowledge/](../../knowledge/)). **Not** raw capture (that is `scratch/`). **Not** a final decision (that is [decisions/](../decisions/) after adoption).

## Queue

| Status | Entry | Category | Link |
|--------|-------|----------|------|
| Queued | Hermes Agent | harness | [2026-07-hermes-agent.md](./2026-07-hermes-agent.md) |
| Testing | Ponytail | context | [2026-07-ponytail.md](./2026-07-ponytail.md) |
| Queued | codebase-memory-mcp | tool | [2026-07-codebase-memory-mcp.md](./2026-07-codebase-memory-mcp.md) |
| Queued | 9Router | tool | [2026-08-9router.md](./2026-08-9router.md) |
| Queued | RTK | tool | [2026-08-rtk.md](./2026-08-rtk.md) |

## When to add an entry

- You hear about a model, tool, or workflow that might improve Plan, Implementation, or Validation
- Something in `scratch/` keeps coming up and deserves a structured test
- You want to compare alternatives before updating [agentic-system.md](../../systems/agentic-system.md) or [tools.md](../../knowledge/tools.md)

## Lifecycle

| Status | Meaning |
|--------|---------|
| **Queued** | Worth testing; no results yet |
| **Testing** | Active evaluation in progress |
| **Promising** | Early signal is good; needs more runs or a real task |
| **Adopted** | Promoted — link to where it landed |
| **Rejected** | Tested; not worth keeping — note why |

## Categories

Align with the [agentic system](../../systems/agentic-system.md) five parts where possible:

| Category | Examples |
|----------|----------|
| `model` | New LLM tier, critic/tester model swap |
| `tool` | MCP server, CLI plugin, browser automation |
| `harness` | Tmux layout, Cursor CLI flag, session workflow |
| `agent` | New per-task agent or major prompt change |
| `context` | Rule pattern, skill, AI-layer technique |
| `workflow` | PIV variant, validation approach, handoff format |
| `other` | Anything that does not fit above |

## How to evaluate

1. Copy [template.md](./template.md) to `YYYY-MM-short-title.md`
2. Write the **hypothesis** and **test plan** before running — what would “good” look like?
3. Run the test on a **real task** when possible (not only a toy prompt)
4. Record **results** and set status
5. On **Adopted**: update the target doc (reference, agentic-system, agents, systems) and set **Promotion** on the evaluation file
6. On **Rejected**: keep the file — short “why not” saves re-testing the same thing in six months

## Friday review

- Move promising `scratch/` notes here as new Queued entries
- Advance or close anything in **Testing**
- Promote **Adopted** items into the right layer; do not leave stale “Promising” entries

See [ENGINEERING-OS.md](../../../ENGINEERING-OS.md) for the full layer contract.
