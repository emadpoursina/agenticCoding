# Contract: Plan test flows and proof types

Applies to Plan artifacts (`plan.md` test flows) and plan-stage / critic guidance.

## Requirement (FR-001)

Every acceptance criterion MUST map to at least one test flow. Each test flow MUST declare exactly one **proof type**:

| Proof type | Plan declaration | Tester must produce |
|------------|------------------|---------------------|
| UI | `Proof type: UI` | Playwright **trace, video, and screenshots** under `specs/<flow>/evidence/` |
| API | `Proof type: API` | Captured HTTP request/response (redacted headers/body) |
| CLI/job | `Proof type: CLI/job` | Terminal transcript file and recorded exit code |
| logic | `Proof type: logic` | Test name in manifest + JUnit XML (or project-standard unit report) |

Plans MUST NOT assign UI unless the flow’s commands are Playwright. Non-Playwright UI work MUST use CLI/job or logic. This feature does not introduce other UI recorders (FR-012).

## Plan test flow template (documentation agents should cite)

```markdown
### TF-00N: <flow title>
- **Maps to**: AC-00N "<criterion text>"
- **Proof type**: UI | API | CLI/job | logic
- **Role**: unit | system
- **Steps**: ...
- **Command(s)**: exact command(s) tester will run
- **Expected artifacts**: relative paths under `specs/<flow>/evidence/`
```

## Critic plan pass (FR-002)

When reviewing the **plan** (pre-implementation), including a **change-path** Plan, critic MUST emit a **blocking** finding if:

- Any acceptance criterion **listed on that Plan** has zero linked test flows, or
- Any linked test flow lacks a proof type from the table above, or
- A flow is labeled UI but its validation commands are not Playwright (tell the Plan to use CLI/job or logic instead).

Finding text MUST name the orphan criterion id or quote.

## Optional fail-before / pass-after (FR-016, US-6)

Document in validation or tester docs only: for a new test flow, operator **may** run the same command at merge-base (expect fail) then at feature HEAD (expect pass). Not a gate for every project or every flow.
