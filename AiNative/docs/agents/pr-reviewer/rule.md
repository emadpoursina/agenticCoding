# Rules — PR reviewer agent

Constraints for staged PR review. Workflow overview: [pr-review-system.md](../../systems/pr-review-system.md).

Review focus: The pr-reviewer's job is architecture, risk, and evidence on the opened PR — not a second spec/plan implementation critique that replaces critic.

## Must

- Run phases in order — do not ask AI to "review this PR" in one shot
- Run Phase 1.5 for any feature PR in an existing subsystem
- Attach design docs, ADRs, and similar features with `@` before Phase 1.5
- Stop and request rework if Phase 1.5 verdict is **blocking** — do not continue to Phase 2
- Run exactly one deep focus review in Phase 4 (security, reliability, maintainability, or performance), unless every Phase 2 rating is Low or None
- In Phase 3, pick the highest-rated risk from Phase 2 — do not fall back to a fixed default category. Honor a `--focus <area>` override from the caller, and state when you are using it
- Give every finding the two 0.0–1.0 scores; trouble sets severity (see SKILL.md Scores)
- Output the parseable compact header (`FLOW_ID`, `VERDICT: APPROVE | REQUEST CHANGES | BLOCKED`, `CRITICAL_COUNT`, `CRITICALS`, `REPORT`, `SUMMARY`)
- Only Critical findings block merge (trigger REQUEST CHANGES). Warning and Suggestion never change the verdict
- Every finding names file:line. Critical findings also name a trigger. Code outside the PR's changed lines is never Critical, except evidence-audit Criticals against the current head's gitignored bundle and CI
- Use diff compression for large PRs before Phase 1
- On re-review, follow the Re-review section in SKILL.md using `--extra @<previous-review>.md`
- After Phase 5, run the evidence audit when the PR carries (or should carry) a feature-loop evidence bundle; skip otherwise. **stale** and **claimed but unproven** are Critical under the merge gate (trouble ≥ 0.8, file:line, trigger) — they REQUEST CHANGES; they are not a separate blocker

## Must not

- Request general feedback without structure
- Write `tasks.md`, dispatch converge/implement, ship, or merge
- Run all review types in Phase 4 — choose one based on PR type
- Run security/reliability/performance review before Phase 1.5 completes
- Treat AI output as authority — human judgment is final
- Invent findings to look thorough. "No Critical findings" is a complete answer

## Stop conditions

- Phase 1.5 INTEGRATION VERDICT is **blocking** — stop, request rework (only for a bypassed safety layer or a broken documented rule)
- PR is typo-only, dependency-only, or config-only with no logic — skip Phase 1.5

## Phase 1.5 skip criteria

Skip architecture compliance when the PR is:
- Typo or formatting only
- Dependency bump only
- Config change with no logic changes

Run Phase 1.5 when the PR adds or changes behavior in an existing subsystem.
