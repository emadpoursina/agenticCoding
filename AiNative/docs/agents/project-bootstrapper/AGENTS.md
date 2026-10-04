# Project bootstrapper agent

Post-onboarding `job` that scaffolds an **already-onboarded** repo from a PRD
card. Runs as a `job` card: one worker session in the task worktree of a repo
the control plane already enrolled and onboarded (see
[new-project.md](../../knowledge/setup/new-project.md) — onboarding creates no
PRD and scaffolds no app). Sets up app layout, declared dependencies, real
validation commands, and project `AGENTS.md` — no feature code, no git. Workers
never ship; the parent commits, pushes the branch, and opens a PR only after
operator approval.

> **Status: target methodology — not wired into the current install.**
> The current Hermes install has no worker loop running; see
> [feature-loop.md](../../systems/feature-loop.md).

## When to use

- A repo is already onboarded (project + board + common files exist) and a PRD card describes what to build — typically the first `job` after onboarding an empty repo (`prd-writer` first, then this)
- You want the app structure, dependency manifests, real `validation_commands`, and agent config in one pass before feature cards run

## Inputs

- One `job` card (`## Skill: project-bootstrapper`) whose body references a PRD card/file produced after onboarding (e.g. by `prd-writer`)
- The onboarded repo's common files (`.ainative/project.yaml`, `AGENTS.md`) — created during onboarding, never by this job from scratch

## Outputs

- Confirmed app/repo layout scaffolded in the task worktree
- Dependency manifests declared; installs and validation runs happen in the loop's tester state
- `.ainative/project.yaml` with **real** `validation_commands` (placeholder marker removed — the orchestrator blocks workflows while it remains)
- `AGENTS.md` project rules filled from [ai-rules-template.md](../../systems/ai-rules-template.md), preserving any existing project control-plane or agent-rules section
- Handoff: parent commits, pushes the branch, and opens a PR only after operator approval; then the PRD is implemented as feature cards through the [feature loop](../../systems/feature-loop.md)

## Supporting files

| File | Purpose |
|------|---------|
| [SKILL.md](./SKILL.md) | Bootstrap steps, park/resume stack confirmation, report shape, feature-loop handoff |
| [rule.md](./rule.md) | Constraints — confirm before scaffolding, no feature code, no git, preserve control-plane section |
