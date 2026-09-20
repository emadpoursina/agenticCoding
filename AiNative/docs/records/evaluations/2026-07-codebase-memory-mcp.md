# codebase-memory-mcp

**Date:** 2026-07-19
**Status:** Queued
**Category:** tool

## Hypothesis

This MCP server could replace or reduce `@codebase` grep/read cycles during PIV **Plan** and **Implementation** — structural queries (`trace_path`, `get_architecture`, `search_graph`) with sub-ms latency and far fewer tokens than file-by-file exploration. Cursor is a supported client; install auto-configures `.cursor/mcp.json`.

Relevant agentic parts: **Tools** (MCP), **Context** (less noise in the window).

## Source

- https://github.com/DeusData/codebase-memory-mcp
- https://deusdata.github.io/codebase-memory-mcp/
- MIT license; install: `curl -fsSL https://raw.githubusercontent.com/DeusData/codebase-memory-mcp/main/install.sh | bash`
- Research: arXiv:2603.27277

## Test plan

- [ ] Install on macOS; verify in Cursor `/mcp` — 15 tools visible
- [ ] Index AiNative repo: `index_repository`; note index time and disk under `~/.cache/codebase-memory-mcp/`
- [ ] Run Plan-phase questions without `@codebase`: "what calls X?", "architecture of agents layer", "impact of changing piv-gate" — compare answer quality vs grep + read
- [ ] Measure context cost: structural query session vs equivalent manual file reads (rough token estimate)
- [ ] Test `detect_changes` on a feature branch mid-PIV — useful for critic/tester?
- [ ] Check MCP context bloat: does 15-tool metadata crowd the window? (known risk per [agentic-system.md](../../systems/agentic-system.md))
- [ ] Success criteria: faster orientation on unfamiliar areas; accurate call chains; index stays fresh; no worse Plan quality than baseline
- [ ] Baseline: Cursor `@codebase`, `Grep`, and targeted `@files`

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

- [ ] [agentic-system.md](../../systems/agentic-system.md) — Tools table
- [ ] [cursor-setup.md](../../knowledge/setup/cursor-setup.md) — MCP section
- [ ] [tools.md](../../knowledge/tools.md)
- [ ] [decisions/](../decisions/) — ADR if architectural
- [ ] Other: _link_

If rejected, why not worth another look (or when to re-open).
