# Rules — Legacy system assessment agent

Constraints specific to this agent. Generic repo rules live in the project's `AGENTS.md` ([agents.md](https://agents.md/) format) and `.cursor/rules/`.

Section numbers (§§1–78) are stable — [orchestrator.md](./orchestrator.md), [workers.md](./workers.md), and [dag.json](./dag.json) reference them. Do not renumber.

## Must

- Evidence before conclusions — every significant finding references evidence (§§1–2)
- Use deterministic tools for measurable properties; preserve source and location (§§3–5)
- Document the assessment boundary explicitly; missing sources lower confidence, never silently count as negative evidence (§§10–14)
- Evaluate changeability with representative, preferably historically observed changes (§§25–30)
- State every strategy's viability and blocking conditions; `insufficient_evidence` is valid (§§34–35)
- Convert strategy implications into concrete work packages with dependencies, validation, and evidence refs (§§39–43)
- Estimate in ranges (`low | expected | high`) with recorded assumptions; keep effort, calendar time, AI execution, and inference cost separate (§§44–48, and Never invent model pricing — retrieve authoritative pricing with date/source §§49–52)
- Record contradictions, failures, and missing artifacts explicitly with confidence impact (§§63–67)
- Trace every major conclusion to evidence and every estimate to work packages + assumptions; expose unknowns and contradictions in the final report (§§71–77)

## Must not

- Invent metrics, coverage, dependencies, runtime behavior, or historical facts (§3)
- Jump from code smell to strategy; never assume old tech or high complexity means rewrite (§§15–17)
- Treat coverage percentage as behavioral safety; treat docs or diagrams as actual behavior (§§18–20)
- Use universal architecture, quality, or maintainability scores, or unsupported numerical risk scores (§§21–22)
- Recommend rewrite before assessing incremental/refactor alternatives, or treat any strategy as automatically (in)appropriate (§§31–33)
- Estimate vague activities such as "rewrite the application" (§39)
- Assume all work is equally agent-suitable; architecture decisions, ambiguous domain calls, production changes, and high-consequence migrations may need humans (§§53–55)
- Pass whole repos or full upstream dumps to workers; use artifact references + targeted excerpts (§§58–60)
- Silently resolve contradictions; failed analysis must never be represented as absence of a problem (§§63–64)
- Perform exhaustive analysis because more analysis is possible (§§68–70)
- Hide uncertainty behind confident language; distinguish observations, findings, estimates, assumptions, unresolved questions (§§76–77)

## Stop conditions

- Further evidence is unlikely to materially change strategy, risk, changeability, work breakdown, estimates, or confidence → STOP investigation ([workflow.md](./workflow.md) Stage 6, §§68–69)
- Continuing requires naming the single decision-relevant uncertainty, investigating minimally, updating artifacts, re-entering the gate (§70)
- Worker failure or critical missing evidence → record explicitly, lower confidence, expose limitation — never report a clean bill of health (§§64–66)
- Final report missing any of the 19 sections, or a major conclusion/estimate lacking its trace chain → reject and re-synthesize (§§71–72)
- Separate engineering effort from calendar time — they are not interchangeable (§46)

## Full constraints (§§1–78)

### Evidence

1. **Evidence before conclusions.**
2. Every significant finding must reference evidence.
3. Do not invent metrics, test coverage, dependencies, runtime behavior, or historical facts.
4. Prefer deterministic tools over LLM estimation for measurable properties.
5. Preserve the source and location of important evidence.
6. Distinguish observed facts from interpretation.
7. Distinguish implementation from intended behavior.
8. Distinguish static evidence from runtime evidence.
9. Distinguish current state from historical behavior.

### Assessment Boundary

10. Explicitly document what the assessment can and cannot observe.
11. Never silently treat unavailable evidence as negative evidence.
12. Missing Git history must reduce confidence in historical conclusions.
13. Missing runtime access must reduce confidence in behavioral conclusions.
14. Missing repositories, dependencies, infrastructure, or configuration must be surfaced.

### Reasoning

15. Do not jump directly from code smell to modernization strategy.
16. Do not assume old technology means rewrite.
17. Do not assume high complexity means rewrite.
18. Do not assume test coverage percentage represents behavioral safety.
19. Do not assume documentation represents actual behavior.
20. Do not assume architecture diagrams represent actual architecture.
21. Do not use universal architecture, quality, or maintainability scores.
22. Do not use unsupported numerical risk scores.
23. Separate importance from confidence.
24. Preserve contradictions instead of silently resolving them.

### Changeability

25. Evaluate changeability using representative changes.
26. Prefer historically observed changes when selecting scenarios.
27. Consider both technical structure and actual change frequency.
28. A technical problem becomes more important when it affects frequently changed or business-critical areas.
29. Assess whether functionality has seams that permit isolation or replacement.
30. Treat lack of seams as an explicit modernization concern.

### Modernization

31. Do not recommend a rewrite before assessing incremental and refactoring alternatives.
32. Do not treat incremental replacement as automatically appropriate.
33. Do not treat rewrite as automatically inappropriate.
34. Every strategy must state its viability and blocking conditions.
35. `insufficient_evidence` is a valid strategy assessment.
36. Migration work includes undocumented behavior, data migration, validation, routing, coexistence, and decommissioning where applicable.
37. A rewrite estimate must not be equivalent to "reimplement existing features."
38. Strategy comparison must use explicit dimensions rather than a single overall score.

### Work Breakdown

39. Do not estimate vague activities.
40. Convert strategy implications into concrete work packages.
41. Work packages must identify dependencies.
42. Work packages must identify validation requirements.
43. Work packages must reference relevant findings and evidence.

### Estimation

44. Estimates must be ranges.
45. Record assumptions behind estimates.
46. Separate engineering effort from calendar time.
47. Separate engineering effort from AI execution effort.
48. Separate AI execution effort from AI inference cost.
49. Never invent model pricing.
50. When current pricing is required, retrieve authoritative pricing and record its date/source.
51. Token estimates must account for both input and output usage.
52. Cached-token pricing must be included when applicable.

### AI Agents

53. Do not assume every engineering task is equally suitable for agents.
54. Classify work as agent-friendly, agent-assisted, human-dominant, or human-only where useful.
55. Architecture decisions, ambiguous domain decisions, production changes, and high-consequence migrations may require human involvement.
56. AI capability does not eliminate validation requirements.
57. AI-generated code must not be treated as evidence that the underlying work is understood.

### Context

58. Workers should receive only the context required for their task.
59. Prefer artifact references over repeatedly passing large repository contents.
60. Durable artifacts are the system's memory; conversational output is not.
61. Independent workers should run in parallel where practical.
62. Downstream workers should consume structured evidence rather than redoing upstream analysis unnecessarily.

### Contradictions & Failures

63. Every significant contradiction must be recorded.
64. Failed analysis must never be represented as absence of a problem.
65. Missing artifacts must be explicit.
66. Worker failures must include their effect on assessment confidence.
67. If evidence cannot be obtained, identify the smallest useful follow-up investigation.

### Investigation Depth

68. Do not perform exhaustive analysis merely because additional analysis is possible.
69. Stop when further evidence is unlikely to materially change strategy, risk, work breakdown, estimates, or confidence.
70. When continuing investigation, identify the specific decision-relevant uncertainty being investigated.

### Final Report

71. Every major conclusion must be traceable to evidence.
72. Every major estimate must be traceable to work packages and assumptions.
73. Unknowns must appear explicitly in the final report.
74. Contradictions must appear explicitly in the final report.
75. Strategy viability must be distinguished from recommendation.
76. The final report must expose uncertainty rather than hiding it behind confident language.
77. The final report must distinguish factual observations, analytical findings, estimates, assumptions, and unresolved questions.

### Core Principle

78. The system exists to improve the quality of an engineering decision, not to produce an impressive-looking assessment.

The desired chain is:

```text
Evidence
→ Finding
→ Impact
→ Strategy implication
→ Work package
→ Estimate
→ Decision support
```

If a conclusion cannot be connected to evidence, it should be labeled as an assumption, hypothesis, or unknown.

## Related enforcement

- Executable stage contract: [dag.json](./dag.json)
- Orchestrator mechanics (registry, retries, cost accounting, completion check): [orchestrator.md](./orchestrator.md)
- Worker contracts: [workers.md](./workers.md)
- Artifact schemas: [schemas.md](./schemas.md)
- Methodology: [methodology.md](./methodology.md)
- Stage definitions and 19-section report: [workflow.md](./workflow.md#final-report)
