# Project bootstrapper agent

Bootstraps a brand-new project repo from a single project documentation file (spec/PRD). Handles everything between "I have an idea written down" and "the repo is ready for PIV Plan": stack setup, git init, dependency install, and agent config — no feature code.

## When to use

- Starting a new project repo and you have one project doc (spec or PRD) describing what to build
- You want git, dependencies, and AI agent config (`AGENTS.md`) set up in one pass before implementation starts

## Inputs

- One project documentation file (spec/PRD) describing the product, tech stack, and structure — see [new-project.md](../../knowledge/setup/new-project.md#planning) for the shape expected (business model, app structure, tech stack, PRD)

## Outputs

- Initialized git repo with the confirmed stack scaffolded and dependencies installed
- `AGENTS.md` at repo root, filled in from [ai-rules-template.md](../../systems/ai-rules-template.md) (minus the legacy Cursor frontmatter) — the open [agents.md](https://agents.md/) format read automatically by opencode and other agents
- `scratch/` folder + `.gitignore` entry
- Handoff: user follows [PIV Plan](../../systems/agentic-coding.md) against the spec to break it into work items and implement

## Supporting files

| File | Purpose |
|------|---------|
| [SKILL.md](./SKILL.md) | Bootstrap steps, stack-confirmation checklist, PIV handoff |
| [rule.md](./rule.md) | Constraints — confirm before installing, no feature code, hand off to PIV Plan |

## Cursor Command

Pair this agent with `/project-bootstrapper` at `.cursor/commands/project-bootstrapper.md` (symlinked to `~/.cursor/commands/`). See [personal-agents-symlinks.md](../../knowledge/setup/personal-agents-symlinks.md).
