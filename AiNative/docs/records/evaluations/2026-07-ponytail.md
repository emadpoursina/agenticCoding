# Ponytail

**Date:** 2026-07-19
**Status:** Testing
**Category:** context

## Hypothesis

Ponytail's YAGNI ladder (reuse → stdlib → native → dependency → minimum code) could reduce over-engineering during PIV **Implementation** in Cursor — smaller diffs, lower token cost, faster review — without cutting validation, security, or accessibility. Benchmarks claim ~54% less LOC and ~20% lower cost vs no-skill baseline on real agentic sessions.

Relevant agentic parts: **Context** (rules/skills injected every turn), **Agents** (subagent injection via hooks).

## Source

- https://github.com/DietrichGebert/ponytail
- https://ponytail.dev
- MIT license; Cursor: copy `.cursor/rules/ponytail.mdc`
- Setup (install + how it works): [ponytail.md](../../knowledge/setup/ponytail.md)

## Test plan

- [x] Install for Cursor: global `ponytail.mdc` with docs-excluded globs — see [setup](../../knowledge/setup/ponytail.md); confirm activation
- [ ] Run 2–3 bounded Implementation tasks (medium feature, not trivial typo) with ponytail **on** vs **off** — same model tier
- [ ] Measure: LOC in diff, files touched, unnecessary dependencies added, acceptance criteria still met
- [ ] Manual critic / review pass on diffs (Cursor has no `/ponytail-review`) — confirm safety guards held (validation, auth, error handling)
- [ ] Test interaction with existing AiNative rules (`engineering-os`, `piv-gate`, `ai-rules`) — conflicts or reinforcement?
- [ ] Success criteria: meaningfully smaller diffs on over-build-prone tasks; no missed acceptance criteria; no safety regressions
- [ ] Baseline: current `.cursor/rules/` without ponytail

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

- [ ] [agentic-system.md](../../systems/agentic-system.md) — Context section
- [ ] [ai-rules-template.md](../../systems/ai-rules-template.md)
- [ ] `.cursor/rules/` in target projects
- [x] [tools.md](../../knowledge/tools.md) — linked (setup live; full Adopted still pending results)
- [x] [setup/ponytail.md](../../knowledge/setup/ponytail.md) — install + explanation
- [ ] [decisions/](../decisions/) — ADR if architectural
- [ ] Other: _link_

If rejected, why not worth another look (or when to re-open).
