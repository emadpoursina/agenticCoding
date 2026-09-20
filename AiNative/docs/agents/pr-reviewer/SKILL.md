---
name: pr-reviewer
description: Staged PR review covering understanding, architecture compliance, risk, deep focus, and adversarial testing. Use when reviewing a pull request, especially after PIV Validation passes, or for feature PRs in existing subsystems.
---

# PR reviewer

Review phase prompts copied inline for self-contained use.

---

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

---

## Architecture compliance (Phase 1.5)

**When to run:** Any PR that adds or changes behavior in an existing subsystem. Skip for typo-only, dependency-only, or config-only changes with no logic.

Attach context first: `@` the design doc, ADR, or 2–3 similar features in the codebase.

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

**Example opener (Cursor):**

```text
I'm reviewing PR #[N]. Subsystem: Dynamic Transcribe.
Context: @docs/dynamic-transcribe-design.md @src/chatWithProvider @src/modelRouter

Run Phase 1.5 architecture compliance only.
```

---

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

---

## Select review focus (Phase 3)

Do NOT run all review types. Choose exactly one.

**Default:** pick the category with the highest rating from Phase 2's risk classification (security, scalability, migration, reliability, maintainability). Ties → pick the one whose reasoning in Phase 2 named concrete PR-specific failures over generic concerns. Phase 2 drives Phase 3 — never skip Phase 2, and never default to a fixed category out of habit.

**Override:** if the caller passes `--focus <security|reliability|maintainability|performance>`, use that and say so explicitly. The override is for when the human sees something the ratings missed, not a shortcut around Phase 2.

Map Phase 2 categories to Phase 4 prompts:
- security → Security
- reliability, migration → Reliability
- maintainability → Maintainability / architecture
- scalability → Performance

Allowed focus areas:
- Security Review
- Reliability Review
- Maintainability / Architecture Review
- Performance Review

---

## Deep focus review (Phase 4)

### Security

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

### Reliability

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

### Maintainability / architecture

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

### Performance

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

---

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

---

## Diff compression (large PRs)

```text
Summarize only meaningful logic changes.
Ignore formatting and refactors.
```
