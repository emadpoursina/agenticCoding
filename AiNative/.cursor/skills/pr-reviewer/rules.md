# PR reviewer rules

<!-- source: docs/8. agents/pr-reviewer/rule.md -->

## Must

- Run phases in order — do not ask AI to "review this PR" in one shot
- Run Phase 1.5 for any feature PR in an existing subsystem
- Attach design docs, ADRs, and similar features with `@` before Phase 1.5
- Stop and request rework if Phase 1.5 verdict is **blocking** — do not continue to Phase 2
- Run exactly one deep focus review in Phase 4
- Use diff compression for large PRs before Phase 1
- For each problem give 2 score between 0.0 - 1.0: how often it could happen; if it happended, how much trouble it makes

## Must not

- Request general feedback without structure
- Run all review types in Phase 4 — choose one based on PR type
- Run security/reliability/performance review before Phase 1.5 completes
- Treat AI output as authority — human judgment is final

## Stop conditions

- Phase 1.5 INTEGRATION VERDICT is **blocking** — stop, request rework
- PR is typo-only, dependency-only, or config-only with no logic — skip Phase 1.5
