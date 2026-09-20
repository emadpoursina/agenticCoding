# PR reviewer prompts

<!-- source: docs/8. agents/pr-reviewer/skill.md -->

For each problem give 2 score between 0.0 - 1.0:
  - how often it could happen
  - if it happended, how much trouble it makes

Apply this in Phases 1.5, 2, 4, and 5. Skip Phase 1 (understanding only).

## PR understanding (Phase 1)

```text
Analyze this PR first.
Explain:
- what problem it solves
- core architectural changes
- important files
- risky areas
- possible production impact
- database/auth/api implications
Do not review yet.
```

## Architecture compliance (Phase 1.5)

```text
Compare this PR to the existing [SUBSYSTEM_OR_FEATURE] design and established codebase patterns.

Before reviewing risks or code quality:
1. Read the relevant design doc / ADR (use attached @files).
2. Scan the codebase for similar features — note how they integrate (shared routers, modals, services, logging hooks).
3. List platform abstractions this PR MUST go through.

Check specifically:
- Does it reuse existing abstractions instead of reimplementing them?
- Does it bypass shared infrastructure (config/model routers, provider layers, logging/monitoring wrappers)?
- Does it hard-code values that should be dynamic (models, prompts, feature flags)?
- Does it duplicate functionality that already exists elsewhere?
- Does it follow the same layer boundaries as similar features?

Output:
- MUST USE — existing abstractions this feature should go through
- BYPASSED — existing code this PR skips, and what breaks (logs, monitoring, config, etc.)
- DUPLICATED — logic reimplemented instead of reused
- INTEGRATION VERDICT — clean / needs rework / blocking

Do not run security, reliability, or performance review yet.
```

## Risk classification (Phase 2)

```text
Classify the risks in this PR.
Rate:
- security risk
- scalability risk
- migration risk
- reliability risk
- maintainability risk
Explain why.
```

## Select review focus (Phase 3)

Choose exactly one: Security, Reliability, Maintainability / Architecture, or Performance.

Selection order (do not skip to `default_focus`):
1. `--focus` if the user passed it.
2. Else the Phase 2 category with the **highest** rating (High > Medium > Low; ignore N/A). Eligible: security, reliability, maintainability, performance, and client compatibility when that row was rated.
3. On a tie for the top rating, use `agents.pr-reviewer.default_focus`.

State which Phase 2 ratings drove the choice.

## Deep focus — security (Phase 4)

```text
Review this PR like a security engineer.
Look for:
- auth issues
- permission leaks
- JWT/session risks
- SQL injection
- unsafe validation
- secrets exposure
- multi-tenant risks
- rate limiting issues
```

## Deep focus — reliability (Phase 4)

```text
Review this PR for production reliability.
Focus on:
- failure handling
- retries
- logging quality
- observability
- rollback safety
- migrations
- partial failure scenarios
- timeout handling
```

## Deep focus — maintainability (Phase 4)

```text
Review ONLY architecture and maintainability.
Ignore formatting.
Focus on:
- coupling
- separation of concerns
- abstraction quality
- domain boundaries
- future extensibility
- hidden complexity
- technical debt
```

## Deep focus — performance (Phase 4)

```text
Review performance implications.
Focus on:
- DB query efficiency
- N+1 problems
- memory usage
- caching opportunities
- async behavior
- scalability bottlenecks
```

## Adversarial review (Phase 5)

```text
Act like a hostile senior engineer.
Assume this PR will fail in production.
Find:
- hidden assumptions
- edge cases
- race conditions
- rollback risks
- scalability traps
- long-term maintenance issues
```

## Diff compression (large PRs)

```text
Summarize only meaningful logic changes.
Ignore formatting and refactors.
```
