# Legacy System Assessment Workflow (Stages 0–10)

> Stage definitions for the [legacy-system-assessment-agent](./AGENTS.md). `AGENTS.md` is the entry point (role, triggers, I/O); this file defines **what** each stage means. Orchestrator mechanics: [orchestrator.md](./orchestrator.md). Methodology: [methodology.md](./methodology.md).

## Purpose

Assess a legacy software system before significant engineering investment is committed to it.

The agent produces an evidence-backed assessment of:

* system structure and architecture
* implementation condition
* dependencies and technical constraints
* historical change patterns
* system behavior and undocumented behavior
* test and validation gaps
* changeability
* technical and operational risks
* modernization strategies
* work required for each viable strategy
* engineering effort and calendar-time estimates
* AI-agent execution effort
* estimated AI token usage and inference cost
* evidence gaps, contradictions, and uncertainty

The agent does **not** decide that a system is "good" or "bad" using a universal score.

Its purpose is to answer:

> What do we know about this system, what evidence supports it, what work would each modernization strategy require, and what uncertainty remains?

---

## Operating Model

The system is an evidence compiler.

The primary reasoning chain is:

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

The orchestrator coordinates this chain but should not become the repository's memory.

Workers inspect the system and produce durable artifacts.

---

# Workflow

## Stage 0 — Establish Assessment Boundary

Before analyzing the repository, establish what evidence is available.

Record availability for:

* source repositories
* Git history
* tests
* build configuration
* dependency manifests
* generated code
* deployment configuration
* infrastructure configuration
* runtime environment
* production environment
* databases
* migrations
* external services
* observability
* logs
* documentation
* product requirements
* user/customer behavior
* operational knowledge
* multiple repositories
* private/internal packages

Each boundary item must be classified as:

```text
AVAILABLE
PARTIAL
UNAVAILABLE
UNKNOWN
```

Do not silently substitute one evidence source for another.

Produce:

```text
assessment-boundary.md
```

---

## Stage 1 — Repository Reconnaissance

Delegate to `repo-scout`.

Responsibilities:

* identify repositories and components
* determine repository completeness
* identify languages and frameworks
* identify applications/services/packages
* identify build systems
* identify test systems
* identify databases and migrations
* identify generated artifacts
* identify external dependencies
* identify deployment/runtime configuration
* identify likely entry points
* identify repository structure
* identify obvious missing components

The scout must explicitly answer:

> Is this repository sufficient to understand the system being assessed?

Produce:

```text
repo-profile.md
```

---

# Stage 2 — Evidence Collection

Run independent evidence-producing workers in parallel where possible.

```text
                    ┌─ Static Analysis
                    │
                    ├─ Architecture Analysis
                    │
Recon ──────────────┼─ Git History Analysis
                    │
                    ├─ System Understanding
                    │
                    └─ Behavior/Test Analysis
```

Workers:

* `static-analyst`
* `architecture-analyst`
* `history-analyst`
* `system-understanding-analyst`
* `behavior-test-analyst`

Each worker writes durable artifacts.

---

## Stage 3 — Evidence Reconciliation

Run:

```text
contradiction-reconciler
```

Compare claims across artifacts.

Examples:

* documentation says service A owns data, code indicates service B writes it
* architecture diagram shows dependency X, source shows additional dependency Y
* tests imply behavior that documentation does not mention
* Git history indicates a hotspot that static analysis does not identify
* declared architecture differs from observed architecture

Produce:

```text
contradictions.md
```

A contradiction must not be silently resolved.

Possible states:

```text
UNRESOLVED
RESOLVED_BY_EVIDENCE
REQUIRES_HUMAN_INPUT
```

---

# Stage 4 — System-Level Assessment

Run:

```text
changeability-analyst
risk-analyst
```

These workers consume the evidence layer rather than independently rediscovering the repository.

### Changeability analysis

Determine:

* coupling affecting changes
* dependency concentration
* change propagation
* architectural seams
* unstable areas
* high-change/high-complexity areas
* representative change scenarios
* likely difficulty of isolating functionality
* difficulty of testing changes
* difficulty of deploying changes
* difficulty of replacing components

### Risk analysis

Determine:

* technical risks
* behavioral risks
* migration risks
* data risks
* operational risks
* dependency risks
* test/validation risks
* deployment risks
* knowledge risks
* external-system risks
* rollback risks

Every significant finding must reference evidence.

---

# Stage 5 — Representative Change Scenarios

Run:

```text
change-scenario-selector
```

Select representative changes using evidence from:

* Git history
* hotspots
* architecture
* dependencies
* business capabilities
* known operational areas
* high-risk components

Each scenario contains:

```yaml
id:
type:
description:
affected_area:
selection_rationale:
evidence_refs:
representativeness:
```

Examples:

```text
add feature
modify existing behavior
change database schema
replace dependency
change external integration
modify UI workflow
change cross-cutting concern
fix production defect
```

These scenarios become the basis for assessing changeability and estimating modernization work.

---

# Stage 6 — Minimum-Sufficient Investigation

Before expanding the investigation, ask:

> Could additional evidence materially change the modernization strategy, risk, changeability assessment, work breakdown, estimate, or confidence?

If no:

```text
STOP INVESTIGATION
```

If yes:

```text
IDENTIFY SPECIFIC EVIDENCE GAP
→ investigate
→ update artifacts
→ reassess
```

Avoid exhaustive analysis merely because more analysis is possible.

---

# Stage 7 — Modernization Strategy Analysis

Run strategy-specific workers:

```text
refactor-strategy-planner
incremental-replacement-planner
rewrite-strategy-planner
```

Additional strategies may be added when applicable, such as:

* retain/maintain
* replatform
* replace with commercial product
* partial modernization
* architectural restructuring

Each strategy must produce:

```yaml
status:
  viable
  conditionally_viable
  currently_not_viable
  insufficient_evidence

blocking_conditions:
evidence_refs:
findings:
required_work:
dependencies:
major_risks:
unknowns:
```

Do not select a strategy because it is fashionable or generally recommended.

Determine viability from the assessed system.

---

# Stage 8 — Work Breakdown

Delegate to:

```text
work-breakdown-planner
```

For every strategy that is sufficiently understood, create explicit work packages.

Example:

```text
WP-01 Establish characterization tests
WP-02 Extract authentication boundary
WP-03 Separate database access layer
WP-04 Introduce routing seam
WP-05 Migrate billing capability
WP-06 Migrate data
WP-07 Validate behavioral equivalence
WP-08 Decommission legacy component
```

Every work package must reference:

* findings
* evidence
* dependencies
* assumptions
* validation requirements

Do not estimate a vague statement such as:

> Rewrite the application.

Break it into observable engineering work.

---

# Stage 9 — Estimation

Delegate to:

```text
estimator
```

Separate four dimensions.

## Engineering effort

Estimate human-equivalent engineering effort.

Use:

```text
low
expected
high
```

Do not produce false precision.

---

## Calendar time

Estimate elapsed time based on:

* work dependencies
* parallelizable work
* validation requirements
* migration windows
* external dependencies
* human decision points

Engineering effort and calendar time must not be treated as interchangeable.

---

## AI execution effort

Estimate how much of the work can realistically be performed by coding agents.

Classify work as:

```text
agent_friendly
agent_assisted
human_dominant
human_only
```

Consider:

* repository complexity
* required domain knowledge
* ambiguity
* validation difficulty
* architectural decisions
* external-system coordination
* production access
* human approvals

---

## AI inference cost

Estimate token consumption separately.

Model:

```text
cost =
  input_tokens × input_price
  + output_tokens × output_price
  + cached_tokens × cached_price
```

Record:

```yaml
model:
pricing_source:
pricing_date:
input_tokens_low:
input_tokens_expected:
input_tokens_high:
output_tokens_low:
output_tokens_expected:
output_tokens_high:
estimated_cost_low:
estimated_cost_expected:
estimated_cost_high:
```

Current model pricing must be retrieved from an authoritative source when producing an actual cost estimate.

---

# Stage 10 — Synthesis

Delegate to:

```text
evidence-synthesizer
```

The final synthesizer is an **evidence compiler**.

It may:

* combine findings
* resolve references
* explain relationships
* expose uncertainty
* compare strategies
* assemble work packages
* summarize estimates

It must not independently invent major findings that do not exist in the evidence artifacts.

The synthesizer should be able to trace every important conclusion back to:

```text
conclusion
→ finding
→ evidence
→ source
```

---

# Final Report

Produce:

```text
legacy-system-assessment.md
```

Structure:

1. Executive Summary
2. Assessment Scope & Evidence Boundary
3. System Profile
4. Current Architecture
5. Implementation Condition
6. Changeability
7. Technical & Operational Risks
8. Behavior & Test Gaps
9. Major Evidence-Backed Findings
10. Modernization Options
11. Work Breakdown
12. Engineering Effort Estimates
13. Calendar-Time Estimates
14. AI Execution Assessment
15. AI Token & Cost Estimates
16. Assumptions
17. Unknowns & Contradictions
18. Recommended Further Investigation
19. Evidence Index

---

# Orchestrator Responsibilities

The orchestrator owns:

* DAG execution
* worker dispatch
* artifact registry
* dependency tracking
* retries
* failure handling
* evidence-boundary state
* stopping decisions
* token/cost accounting
* final synthesis coordination

The orchestrator does **not** own:

* repository memory
* detailed methodology
* architectural reasoning
* static analysis
* Git analysis
* modernization methodology
* code-level implementation

Those belong to workers, skills, and artifacts.

---

# Context Management

Never pass an entire repository or entire previous artifact set into every worker.

Prefer:

```text
artifact references
+
structured findings
+
targeted excerpts
+
specific evidence
```

Workers should consume only the evidence necessary for their task.

---

# Failure Handling

A worker failure must be explicit.

Record:

```yaml
worker:
stage:
status:
failure:
attempts:
missing_artifacts:
impact:
```

Never convert:

```text
analysis failed
```

into:

```text
no problems found
```

If a critical evidence source is unavailable, reduce confidence and expose the limitation.

---

# Completion Criteria

The assessment is complete when:

* the evidence boundary is documented
* repository completeness has been assessed
* major evidence domains have been investigated
* contradictions have been surfaced
* representative change scenarios exist
* major findings have evidence references
* viable strategy options have been analyzed
* work packages exist for sufficiently understood strategies
* effort/time/AI-cost estimates have assumptions
* important unknowns are explicit
* additional investigation no longer appears likely to materially change the result

The system should prefer:

> sufficiently supported decision information

over:

> exhaustive analysis for its own sake.

