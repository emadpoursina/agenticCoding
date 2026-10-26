# PR reviewer agent

Staged PR review workflow: understanding → architecture compliance → risk classification → deep focus → adversarial testing. AI is a thinking partner, not an authority.

Workflow context: [pr-review-system.md](../../systems/pr-review-system.md).

## When to use

- Reviewing a pull request on operator request; in the target feature loop ([feature-loop.md](../../systems/feature-loop.md#pivs-mapping)) this is an on-demand tool after Ship, not a loop state
- Feature PRs in existing subsystems — always run Phase 1.5
- Large PRs — use diff compression first
- After critic and tester report PASS and Ship has opened a PR — run whenever review is wanted

## Inputs

- PR diff or changed files (`@` references)
- For Phase 1.5: design doc, ADR, 2–3 similar features in codebase

## Outputs

- Mental model of the change (Phase 1)
- Architecture compliance verdict (Phase 1.5)
- Risk ratings by category (Phase 2)
- Deep findings for one focus area (Phase 4)
- Adversarial edge cases (Phase 5)
- Evidence audit (on demand after Ship): completeness (verdict-aware — PASS ⇒ every acceptance criterion has a row; FAIL ⇒ rows for every executed flow), manifest SHA vs PR head (stale), CI job success on this head; **stale** and **claimed but unproven** are blocking, re-runnable after every fix push

## Phases

| Phase | Skill in SKILL.md | Purpose |
|-------|-------------------|---------|
| 1 | PR understanding | Build mental model — no review yet |
| 1.5 | Architecture compliance | Verify reuse of existing abstractions |
| 2 | Risk classification | Rate security, scalability, migration, reliability, maintainability |
| 3 | Select review focus | Pick the highest-rated risk from Phase 2 (or honor a `--focus` override) |
| 4 | Deep focus review | Run the selected focus prompt |
| 5 | Adversarial review | Hostile senior engineer pass |
| Audit | Evidence audit (prompts.md) | On demand after Ship — completeness, stale SHA vs PR head, CI agreement; blocking findings re-checked after fix pushes |

## Supporting files

| File | Purpose |
|------|---------|
| [SKILL.md](./SKILL.md) | Staged review phase prompts |
| [rule.md](./rule.md) | Phase ordering, skip criteria, stop conditions |

## Quick start

```text
Analyze this PR first.
Explain: problem solved, architectural changes, important files, risky areas,
production impact, database/auth/api implications. Do not review yet.
```

For feature PRs in existing subsystems, attach context and run Phase 1.5 before Phase 2. See [SKILL.md](./SKILL.md) for all phase prompts.
