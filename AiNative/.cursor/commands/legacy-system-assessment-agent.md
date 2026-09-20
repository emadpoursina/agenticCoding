# Legacy System Assessment Agent Command

This file defines the legacy-system-assessment-agent command, which activates the legacy-system-assessment-agent.

## Command Definition

```yaml
name: legacy-system-assessment-agent
description: Evidence-backed legacy system assessment — modernization strategies, work packages, effort/time/AI-cost estimates with explicit uncertainty
```

## Invocation

When this command is invoked, the agent should:

1. **Load Context**
   - Read `docs/agents/legacy-system-assessment-agent/AGENTS.md` (purpose, when to use, inputs/outputs, stages)
   - Read `docs/agents/legacy-system-assessment-agent/SKILL.md` (operating model, dispatch guide, estimate dimensions)
   - Read `docs/agents/legacy-system-assessment-agent/rule.md` (constraints and stop conditions)
   - Consult `docs/agents/legacy-system-assessment-agent/workflow.md` (Stage 0–10 definitions), `methodology.md` (worker methodology), `orchestrator.md` (DAG execution), `workers.md` (contracts), `schemas.md` (artifact fields), `dag.json` (executable contract) as needed

2. **Parse Arguments**
   - `$ARGUMENTS` contains the assessment target and decision after the command (e.g. `Assess ~/projects/billing for refactor-vs-rewrite. Available: git history, docs. Unavailable: runtime, prod DB.`)
   - If empty, prompt the user for: (a) path to the system, (b) the decision the assessment supports, (c) known available/unavailable evidence sources

3. **Activate Agent**
   - Adopt the persona and constraints from the loaded files
   - Treat `$ARGUMENTS` as the task input
   - Start at Stage 0 (assessment boundary) — never skip to strategy or estimation
   - Do not redefine behavior already specified in the agent files

## Usage Examples

```text
/legacy-system-assessment-agent Assess ~/projects/billing-service for refactor-vs-rewrite in Q4. Available: git history, docs. Unavailable: runtime, prod DB.
```

→ Establishes the assessment boundary (Stage 0), profiles the repo (Stage 1), fans out parallel evidence workers, reconciles contradictions, and compiles strategies + work packages + estimates into `legacy-system-assessment.md`

```text
/legacy-system-assessment-agent Assess ./legacy-app for incremental-replacement viability. Available: source, git history, tests. Unavailable: production, observability.
```

→ Same pipeline, scoped to incremental-replacement viability with explicit unknowns where production evidence is missing

```text
/legacy-system-assessment-agent
```

→ Activates legacy-system-assessment-agent; prompts for the system path, the decision to support, and available/unavailable evidence sources
