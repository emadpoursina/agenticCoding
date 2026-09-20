# Legacy System Assessment Methodology

> Worker methodology for the [legacy-system-assessment-agent](./AGENTS.md). Operational dispatch guide: [SKILL.md](./SKILL.md). Stage definitions: [workflow.md](./workflow.md).

## Purpose

This skill defines the methodology used by workers in the Legacy System Assessment system.

The skill is reusable across:

* languages
* frameworks
* architectures
* monoliths
* distributed systems
* desktop applications
* web applications
* backend systems
* mobile applications
* multi-repository systems
* partially documented systems

The methodology is evidence-first.

---

# 1. Core Assessment Model

Use:

```text
Evidence
  ↓
Finding
  ↓
Impact
  ↓
Strategy implication
  ↓
Work package
  ↓
Estimate
```

Never skip directly from:

```text
code smell → rewrite
```

or:

```text
old technology → rewrite
```

---

# 2. Evidence Model

Every important observation should be represented as evidence.

```yaml
id: EVID-042
type: dependency | metric | source | history | test | runtime | documentation | configuration
source:
location:
observation:
collected_by:
timestamp:
confidence:
```

Examples:

```yaml
id: EVID-001
type: dependency
source: dependency-cruiser
location: src/modules
observation: Module A imports Module B and Module B imports Module A
```

```yaml
id: EVID-002
type: history
source: git
location: src/billing
observation: Billing files changed in 47 commits during the last 12 months
```

```yaml
id: EVID-003
type: test
source: test-runner
location: src/billing
observation: No automated tests cover the refund workflow
```

Evidence should be as close to the original source as practical.

---

# 3. Finding Model

Findings interpret evidence.

```yaml
id: FIND-017
statement:
evidence_refs:
impact:
affected_area:
confidence:
```

A finding should answer:

> What does the evidence mean for engineering?

Example:

```text
Finding:
The billing subsystem has high change activity and weak automated behavioral protection.

Evidence:
EVID-002
EVID-003

Impact:
Changes in billing are likely to require significant manual regression validation.

Confidence:
High
```

---

# 4. Evidence Hierarchy

Prefer:

```text
runtime evidence
direct source/configuration evidence
deterministic tool output
Git history
tests
documentation
developer statements
LLM inference
```

This is not an absolute ranking.

Different evidence answers different questions.

For example:

* runtime evidence is useful for actual behavior
* Git history is useful for historical change patterns
* documentation is useful for intended behavior
* source code is useful for implemented behavior

When sources disagree, preserve the disagreement.

---

# 5. Assessment Boundary

Always identify what is and is not observable.

Record:

```text
repository
history
runtime
database
external services
deployment
configuration
production behavior
documentation
user behavior
```

as:

```text
AVAILABLE
PARTIAL
UNAVAILABLE
UNKNOWN
```

A conclusion must not imply evidence that was outside the assessment boundary.

---

# 6. Repository Completeness

Determine whether the repository contains enough material to represent the deployed system.

Check for:

* multiple repositories
* generated code
* submodules
* private packages
* external services
* deployment manifests
* infrastructure repositories
* migration scripts
* environment-specific configuration
* build-time code generation
* shared libraries

A repository can be internally coherent while still being incomplete as a system representation.

---

# 7. Static Analysis

Use deterministic tooling whenever possible.

Examples include:

* dependency graph tools
* complexity analyzers
* duplication analyzers
* linters
* type-checkers
* security scanners
* build tools
* test coverage tools

Do not invent metrics.

Do not estimate a metric from visual inspection when a deterministic tool can produce it.

Static metrics are evidence, not conclusions.

---

# 8. Architecture Analysis

Distinguish:

```text
declared architecture
```

from:

```text
observed architecture
```

Analyze:

* modules
* components
* dependencies
* dependency direction
* cycles
* boundaries
* ownership
* external integrations
* data ownership
* deployment topology
* runtime communication

Architecture diagrams should reflect observed evidence where possible.

---

# 9. Implementation Condition

Assess characteristics such as:

* complexity
* duplication
* coupling
* cohesion
* dependency problems
* obsolete dependencies
* inconsistent patterns
* error handling
* configuration management
* data-access structure
* code organization
* build/release complexity

Do not turn these into a universal quality score.

A technical problem becomes more significant when combined with:

```text
change frequency
× affected scope
× business relevance
× operational relevance
× migration relevance
```

---

# 10. Git History

Git history can reveal:

* change hotspots
* ownership concentration
* recurring defects
* unstable modules
* architectural pressure
* coupled changes
* abandoned areas
* migration history

Useful signals include:

```text
commit frequency
file churn
co-change
authors
reverts
bug-fix commits
large changes
long-lived branches
```

History should describe observed patterns, not infer developer motives.

---

# 11. Behavior Analysis

Separate:

```text
intended behavior
implemented behavior
observed runtime behavior
tested behavior
```

These may differ.

For modernization, undocumented behavior is itself a risk.

Examples:

* implicit validation
* undocumented API behavior
* unusual error handling
* database side effects
* ordering assumptions
* compatibility behavior
* hidden integrations

A rewrite must account for behavior that users or downstream systems depend on even if that behavior is poorly documented.

---

# 12. Test Gap Analysis

Assess:

* unit tests
* integration tests
* end-to-end tests
* characterization tests
* regression tests
* contract tests
* production validation
* observability

Do not treat coverage percentage as sufficient evidence of safety.

Ask:

> Which important behavior is protected?

and:

> Which important behavior can change without automated detection?

---

# 13. Changeability

Changeability is about the cost and risk of making representative changes.

Analyze:

* dependency propagation
* change surface
* coupling
* testability
* deployment isolation
* architectural seams
* ownership boundaries
* historical change patterns

Use representative change scenarios rather than abstract claims.

---

# 14. Representative Change Scenarios

Select scenarios from actual evidence.

Good scenarios include:

* recent high-impact changes
* frequent changes
* changes crossing architectural boundaries
* database changes
* external integrations
* high-risk business capabilities
* historically difficult changes

Each scenario should explain why it represents the system.

---

# 15. Risk

Classify risk into useful categories:

```text
technical
behavioral
migration
data
operational
deployment
security
dependency
testing
knowledge
external-system
rollback
```

A risk should contain:

```yaml
id:
description:
evidence_refs:
likelihood:
impact:
uncertainty:
mitigation:
```

Avoid unsupported numerical risk scores.

---

# 16. Contradiction Handling

When evidence disagrees:

```text
identify
→ preserve
→ investigate
→ resolve if possible
```

Never silently choose whichever source supports the preferred conclusion.

Example:

```yaml
id: CONTR-004
sources:
  - architecture.md
  - source-code
conflict: Documentation says A owns customer data; code indicates B performs writes.
significance: High
resolution_status: UNRESOLVED
resolution: Requires data-owner decision before migration planning.
```

---

# 17. Modernization Strategies

Possible strategies include:

```text
retain
refactor
re-architect
incremental replacement
full rewrite
replatform
partial replacement
vendor replacement
```

The strategy set should adapt to the system.

For incremental replacement, assess whether there are controllable seams and whether behavior can be migrated safely. Incremental modernization commonly depends on isolatable boundaries and controlled routing; lack of clear boundaries can itself become a major work item.

For every strategy determine:

```text
viable
conditionally viable
currently not viable
insufficient evidence
```

Do not force a strategy when evidence is insufficient.

---

# 18. Strategy Comparison

Compare strategies across explicit dimensions:

* required work
* dependencies
* migration complexity
* behavior uncertainty
* data migration
* testing requirements
* operational impact
* rollback capability
* time
* engineering effort
* AI suitability
* AI token cost
* unresolved assumptions

Do not collapse these into one score.

---

# 19. Work Breakdown

Convert strategy implications into concrete work packages.

Each work package should have:

```yaml
id:
description:
strategy:
depends_on:
affected_area:
evidence_refs:
finding_refs:
validation:
assumptions:
```

Prefer:

```text
Introduce characterization tests for invoice calculation
```

over:

```text
Improve billing
```

---

# 20. Estimation

Estimate ranges:

```text
low
expected
high
```

Record the basis for the estimate.

Separate:

```text
engineering effort
calendar duration
AI execution effort
AI inference cost
```

These are different quantities.

---

# 21. AI Execution Model

AI coding agents can accelerate implementation, but not every work package is equally automatable.

Classify each package:

```text
agent_friendly
agent_assisted
human_dominant
human_only
```

Consider:

* ambiguity
* architecture decisions
* domain knowledge
* testability
* environment access
* production access
* approval requirements
* migration coordination
* observability

Do not equate:

```text
AI can write code
```

with:

```text
AI can independently complete the work
```

---

# 22. Token Cost Model

Estimate agent usage by stage.

For each worker:

```yaml
worker:
model:
input_tokens:
output_tokens:
cached_tokens:
iterations:
tool_calls:
```

Cost:

```text
input_tokens × input_price
+
output_tokens × output_price
+
cached_tokens × cached_price
```

Include uncertainty ranges.

Record model pricing source and date.

---

# 23. Confidence

Use confidence to describe evidence quality.

Suggested vocabulary:

```text
high
medium
low
unknown
```

Confidence is not the same as importance.

A highly important finding can have low confidence.

---

# 24. Unknowns

Unknowns are first-class outputs.

Examples:

```text
production behavior unavailable
database ownership unclear
private dependency unavailable
runtime traffic unavailable
customer workflows undocumented
deployment process unknown
```

Unknowns should influence strategy viability and estimates.

---

# 25. Minimum-Sufficient Investigation

Stop when additional investigation is unlikely to materially change:

* strategy viability
* major risks
* changeability
* work breakdown
* estimates
* confidence

This prevents analysis from becoming an endless repository archaeology project.

---

# 26. Evidence Traceability

Important conclusions should support:

```text
Conclusion
→ Finding
→ Evidence
→ Source
```

Important estimates should support:

```text
Estimate
→ Work package
→ Finding
→ Evidence
→ Assumptions
```

This allows another engineer to challenge an assessment without rerunning the entire analysis.

---

# 27. Assessment Philosophy

The system should answer:

> What would we need to do, why, how difficult might it be, and how certain are we?

It should not answer:

> Is this codebase good or bad?

The output is decision support, not a universal software-quality score.

