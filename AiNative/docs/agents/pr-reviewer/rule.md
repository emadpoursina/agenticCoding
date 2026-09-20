# Rules — PR reviewer agent

Constraints for staged PR review. Workflow overview: [pr-review-system.md](../../systems/pr-review-system.md).

## Must

- Run phases in order — do not ask AI to "review this PR" in one shot
- Run Phase 1.5 for any feature PR in an existing subsystem
- Attach design docs, ADRs, and similar features with `@` before Phase 1.5
- Stop and request rework if Phase 1.5 verdict is **blocking** — do not continue to Phase 2
- Run exactly one deep focus review in Phase 4 (security, reliability, maintainability, or performance)
- In Phase 3, pick the highest-rated risk from Phase 2 — do not fall back to a fixed default category. Honor a `--focus <area>` override from the caller, and state when you are using it
- Use diff compression for large PRs before Phase 1

## Must not

- Request general feedback without structure
- Run all review types in Phase 4 — choose one based on PR type
- Run security/reliability/performance review before Phase 1.5 completes
- Treat AI output as authority — human judgment is final

## Stop conditions

- Phase 1.5 INTEGRATION VERDICT is **blocking** — stop, request rework
- PR is typo-only, dependency-only, or config-only with no logic — skip Phase 1.5

## Phase 1.5 skip criteria

Skip architecture compliance when the PR is:
- Typo or formatting only
- Dependency bump only
- Config change with no logic changes

Run Phase 1.5 when the PR adds or changes behavior in an existing subsystem.
