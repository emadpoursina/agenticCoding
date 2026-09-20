# Legacy System Assessment Artifact Schemas (V2)

Field contracts for every durable artifact in `dag.json`. `R` = required, `O` = optional. Workers emit these; the orchestrator (`orchestrator.md` §3) validates references; `tests/test_v2_contracts.py` enforces the static half (DAG coverage, worker coverage, contract presence).

Conventions: IDs (`EVID-xxx`, `FIND-xxx`, `CONTR-xxx`, `WP-xxx`, scenario IDs) are unique within one assessment and never reused after rejection. Confidence uses `high | medium | low | unknown`. Availability uses `AVAILABLE | PARTIAL | UNAVAILABLE | UNKNOWN`.

## 1. Evidence item

```yaml
id: EVID-042            # R, unique
type:                  # R, one of:
  # dependency | metric | source | history | test | runtime
  # | documentation | configuration
source:                # R, tool name + version, or document/system name
location:              # R, file path / module / revision / URL — as close to origin as practical
observation:           # R, observed fact only, no interpretation
collected_by:          # R, worker name
timestamp:             # R
confidence:            # R, high | medium | low | unknown
```

## 2. Finding

```yaml
id: FIND-017            # R, unique, stable within the assessment
statement:             # R, answers "what does the evidence mean for engineering?"
evidence_refs:         # R, ≥1 EVID-xxx; every ID must resolve in the registry
impact:                # R
affected_area:         # R
confidence:            # R, high | medium | low | unknown (evidence quality, not importance)
```

## 3. assessment-boundary

One entry per row below, each `AVAILABLE | PARTIAL | UNAVAILABLE | UNKNOWN`, plus a one-line note for anything not `AVAILABLE`:

`repositories | git-history | tests | runtime | production | database | migrations | external-services | deployment | configuration | documentation | user-behavior | infrastructure | private-dependencies`

```yaml
status:                # R per item, AVAILABLE | PARTIAL | UNAVAILABLE | UNKNOWN
note:                  # R when not AVAILABLE — what is missing and why
assessed_by: orchestrator
```

A conclusion that implies evidence from a non-`AVAILABLE` source is invalid (`rule.md` §§10–14).

## 4. repo-profile

```yaml
languages_frameworks:  # R
components:            # R, apps / services / packages found
build_systems:         # R
test_systems:          # R
databases_migrations:  # R
generated_artifacts:   # R, incl. build-time generation
external_dependencies: # R, incl. private packages
deployment_runtime:    # R, manifests, infra repos, env-specific config
entry_points:          # R
missing_components:    # R, explicit list; empty only with justification
sufficient:            # R, boolean — is this repo enough to understand the deployed system?
sufficiency_rationale: # R
multi_repo_notes:      # O, submodules, sibling repos, infra repos
```

## 5. Contradiction (contradictions artifact = list of)

```yaml
id: CONTR-004          # R, unique
sources:               # R, ≥2 artifact/source references
conflict:              # R, what disagrees, precisely
significance:          # R, high | medium | low
resolution_status:     # R, UNRESOLVED | RESOLVED_BY_EVIDENCE | REQUIRES_HUMAN_INPUT
resolution:            # R when RESOLVED_BY_EVIDENCE (deciding evidence + refs);
                       # otherwise: next step / who must decide
```

## 6. Change scenario (change-scenarios artifact = list of)

```yaml
id:                    # R, unique
type:                  # R, e.g. add-feature | modify-behavior | schema-change
                       # | replace-dependency | integration-change | ui-workflow
                       # | cross-cutting-change | production-defect-fix
description:           # R, concrete and observable
affected_area:         # R
selection_rationale:   # R, why this scenario represents the system
evidence_refs:         # R, ≥1 EVID-xxx
representativeness:    # R, which class of real changes this stands in for
```

## 7. Risk (risk-register artifact = list of)

Category is one of `technical | behavioral | migration | data | operational | deployment | security | dependency | testing | knowledge | external-system | rollback`.

```yaml
id:                    # R, unique
description:           # R
category:              # R, one of the above
evidence_refs:         # R, ≥1 EVID-xxx (or explicit unknown marker per §12-failure rules)
likelihood:            # R, high | medium | low | unknown — qualitative only
impact:                # R, high | medium | low | unknown — qualitative only
uncertainty:           # R, what could change this assessment
mitigation:            # O
```

## 8. Strategy assessment (one artifact per strategy)

```yaml
strategy:              # R, retain | refactor | re-architect | incremental-replacement
                       # | full-rewrite | + approved extras (replatform, vendor-replacement, partial)
status:                # R, viable | conditionally_viable | currently_not_viable
                       # | insufficient_evidence
blocking_conditions:   # R, empty only when status is viable, with rationale
evidence_refs:         # R
findings:              # R, FIND-xxx supporting the viability judgment
required_work:         # R, references to WP-xxx (post-breakdown) or named work items
dependencies:          # R
major_risks:           # R
unknowns:              # R
```

## 9. Work package (work-packages artifact = list of)

```yaml
id: WP-014             # R, unique
description:           # R, observable engineering work, e.g.
                       # "Introduce characterization tests for invoice calculation"
strategy:              # R, which strategy this package belongs to
depends_on:            # R, other WP-xxx (empty only if genuinely independent)
affected_area:         # R
evidence_refs:         # R
finding_refs:          # R
validation:            # R, how completion/equivalence is proven
assumptions:           # R
```

Vague packages ("rewrite the application", "improve billing") are invalid.

## 10. Estimates (estimates artifact)

Four separated dimensions; effort/time/AI-cost must never be merged (`rule.md` §§46–48). Each numeric estimate is a `low | expected | high` range — point estimates are invalid.

```yaml
engineering_effort:    # R, human-equivalent effort range per package + total, with basis
calendar_time:         # R, elapsed-time range from dependencies, parallelizable work,
                       # validation, migration windows, external deps, decision points
ai_execution:          # R, per-package class agent_friendly | agent_assisted
                       # | human_dominant | human_only, with rationale
assumptions:           # R, recorded basis for every major estimate
```

## 11. AI token / inference cost (part of estimates)

```yaml
model:                 # R
pricing_source:        # R, authoritative source (never invented)
pricing_date:          # R
input_tokens_low|expected|high:    # R
output_tokens_low|expected|high:   # R
cached_tokens_low|expected|cached_tokens_high:  # O (R when caching applies)
estimated_cost_low|expected|high:  # R
# cost = input_tokens × input_price + output_tokens × output_price
#        + cached_tokens × cached_price
```

Per-worker usage ledger (kept by the orchestrator, `orchestrator.md` §7):

```yaml
worker: | model: | input_tokens: | output_tokens: | cached_tokens:
| iterations: | tool_calls:
```

## 12. Failure record (registry entry, not a worker artifact)

```yaml
worker: | stage: | status: failed
failure:               # R, what happened
attempts:              # R, number (max 2 retries before FAILED/PARTIAL)
missing_artifacts:     # R
impact:                # R, effect on assessment confidence
```

`analysis failed` must never be recorded as `no problems found` (`rule.md` §64).
