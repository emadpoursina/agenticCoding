# PR reviewer agent

Staged PR review workflow: understanding → architecture compliance → risk classification → deep focus → adversarial testing. AI is a thinking partner, not an authority.

Workflow context: [pr-review-system.md](../../systems/pr-review-system.md).

## When to use

- Reviewing any pull request in Cursor
- Feature PRs in existing subsystems — always run Phase 1.5
- Large PRs — use diff compression first
- After the PIV Validation phase (critic + tester) passes — pr-reviewer is the final gate; a surprise here means Validation missed something

## Inputs

- PR diff or changed files (`@` references)
- For Phase 1.5: design doc, ADR, 2–3 similar features in codebase

## Outputs

- Mental model of the change (Phase 1)
- Architecture compliance verdict (Phase 1.5)
- Risk ratings by category (Phase 2)
- Deep findings for one focus area (Phase 4)
- Adversarial edge cases (Phase 5)

## Phases

| Phase | Skill in SKILL.md | Purpose |
|-------|-------------------|---------|
| 1 | PR understanding | Build mental model — no review yet |
| 1.5 | Architecture compliance | Verify reuse of existing abstractions |
| 2 | Risk classification | Rate security, scalability, migration, reliability, maintainability |
| 3 | Select review focus | Pick the highest-rated risk from Phase 2 (or honor a `--focus` override) |
| 4 | Deep focus review | Run the selected focus prompt |
| 5 | Adversarial review | Hostile senior engineer pass |

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

## Cursor Command

Pair this agent with `/pr-reviewer` at `.cursor/commands/pr-reviewer.md` (symlinked to `~/.cursor/commands/`). See [personal-agents-symlinks.md](../../knowledge/setup/personal-agents-symlinks.md).
