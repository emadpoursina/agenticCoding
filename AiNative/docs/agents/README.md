# Agents

Part **5** of the [agentic system](../systems/agentic-system.md) — per-task workflows (Harness, Model, Context, and Tools are the other four parts).

Each agent is a folder with three core files tuned for one job.

## File contract

| File | Purpose |
|------|---------|
| `AGENTS.md` | What the agent does, when to invoke it, inputs/outputs — [AGENTS.md](https://agents.md/) format, read this first |
| `SKILL.md` | How to do the job — [Agent Skills](https://agentskills.io/home) format (`name` + `description` frontmatter); library skill bodies copied inline so the folder is self-contained |
| `rule.md` | Constraints and stop conditions specific to this agent |

`SKILL.md` `name` must match the parent folder. Supporting files (phase prompts, etc.) live in the same folder when the workflow is multi-step.

## Agents

| Agent | Command | Purpose |
|-------|---------|---------|
| [ready](./ready/) | `/ready` | **Live loop agent** — feature-loop pre-flight gate; returns `READY: ok|blocked` ([feature-loop.md](../systems/feature-loop.md)) |
| [plan-reviewer](./plan-reviewer/) | `/plan-reviewer` | Optional (not on the live graph) — same-model plan quality gate |
| [critic](./critic/) | `/critic` | **Live loop agent** — adversarial review of plan and implementation after converge ([feature-loop.md](../systems/feature-loop.md)) |
| [tester](./tester/) | `/tester` | **Live loop agent** — prove the code works and run the project's `validation_commands` ([feature-loop.md](../systems/feature-loop.md)) |
| [pr-reviewer](./pr-reviewer/) | `/pr-reviewer` | **Live loop agent** — reviews the feature branch; the final gate before publish |
| [task-groomer](./task-groomer/) | `/task-groomer` | Backlog grooming and Monday/Friday meeting prep |
| [project-bootstrapper](./project-bootstrapper/) | `/project-bootstrapper` | New-project environment setup from a single spec doc, up to the point PIV Plan starts |
| [legacy-system-assessment-agent](./legacy-system-assessment-agent/) | `/legacy-system-assessment-agent` | Evidence-backed legacy assessment — strategies, work packages, effort/time/AI-cost estimates with explicit uncertainty |

## Skill library

Reusable [Agent Skills](https://agentskills.io/home) in [`_skills/`](./_skills/). Each skill is a folder with `SKILL.md` (YAML `name` + `description`, then the body). When tuning an agent, copy the **body** into that agent's `SKILL.md` — not the library frontmatter. New skills discovered during tuning go into `_skills/<name>/SKILL.md` first, then copy to other agents that need them.

| Skill | Use for |
|-------|---------|
| [research-first](./_skills/research-first/SKILL.md) | Codebase scan before planning |
| [mermaid-diagrams](./_skills/mermaid-diagrams/SKILL.md) | Architecture and flow diagrams in plans |
| [conventional-commits](./_skills/conventional-commits/SKILL.md) | Commit message format |
| [verification](./_skills/verification/SKILL.md) | Post-implementation review passes (critic) |
| [test-execution](./_skills/test-execution/SKILL.md) | Unit and system test execution (tester) |
| [doc-update-after-work](./_skills/doc-update-after-work/SKILL.md) | Docs, changelog, comments after shipping |

## External agent libraries

Third-party persona collections — borrow prompts or install into Cursor/Claude Code; not part of AiNative PIV agents.

| Resource | Description |
|----------|-------------|
| [The Agency (agency-agents)](https://github.com/msitarzewski/agency-agents) | Specialized AI agent personas (engineering, design, marketing, PM, etc.) with install scripts for Cursor, Claude Code, Copilot, and other tools |

## Add a new agent

1. Copy [`template/`](./template/) to `docs/agents/<task-name>/`
2. Write `AGENTS.md` — purpose, when to use, inputs/outputs
3. Set `SKILL.md` frontmatter: `name` = folder name, `description` = WHAT + WHEN (third person). Pick skills from `_skills/` and copy bodies into `SKILL.md` (add `<!-- source: _skills/<name>/SKILL.md -->` comments)
4. Capture agent-specific constraints in `rule.md`
5. Add supporting prompt files if the workflow has phases
6. Register the agent in this README table
7. Create a matching Cursor Command at `.cursor/commands/<agent-name>.md` in AiNative, then run `./scripts/setup-machine.sh` so it is available in every project. See [personal-agents-symlinks.md](../knowledge/setup/personal-agents-symlinks.md).
8. Tune all three files as you use the agent

## Related

- Five-part model: [agentic-system.md](../systems/agentic-system.md)
- Methodology: [PIV — Plan, Implementation, Validation](../systems/agentic-coding.md)
- Generic templates (not agents): [systems/](../systems/)
- **App projects:** link agents into other repos — [personal-agents-symlinks.md](../knowledge/setup/personal-agents-symlinks.md)
- Formats: [AGENTS.md](https://agents.md/), [Agent Skills](https://agentskills.io/specification)
