# Project bootstrapper agent

Bootstraps an **enrolled-but-empty** project repo from a PRD inside the Hermes
feature loop. Runs as a `job` card: one worker session in the task worktree of
a repo the control plane already enrolled. Handles the content between "the repo
is enrolled" and "feature cards can run": app scaffold, declared dependencies,
real validation commands, and project `AGENTS.md` — no feature code, no git.

## When to use

- A repo is enrolled with Hermes (empty or scaffold-only) and a PRD describes what to build
- You want the app structure, dependency manifests, real `validation_commands`, and agent config in one pass before feature cards run

## Inputs

- One `job` card (`## Skill: project-bootstrapper`) whose body references a PRD — see [new-project.md](../../knowledge/setup/new-project.md#planning) for the PRD shape (business model, app structure, tech stack, PRD)
- The enrolled repo's onboarding scaffold (`.ainative/project.yaml`, `AGENTS.md`)

## Outputs

- Confirmed app/repo layout scaffolded in the task worktree
- Dependency manifests declared; installs and validation runs happen in the loop's tester state
- `.ainative/project.yaml` with **real** `validation_commands` (placeholder marker removed — the orchestrator blocks workflows while it remains)
- `AGENTS.md` project rules filled from [ai-rules-template.md](../../systems/ai-rules-template.md), preserving any existing project control-plane or agent-rules section
- Handoff: operator approves publish; then imports the PRD as feature cards for the [feature loop](../../systems/feature-loop.md)

## Supporting files

| File | Purpose |
|------|---------|
| [SKILL.md](./SKILL.md) | Bootstrap steps, park/resume stack confirmation, report shape, feature-loop handoff |
| [rule.md](./rule.md) | Constraints — confirm before scaffolding, no feature code, no git, preserve control-plane section |
