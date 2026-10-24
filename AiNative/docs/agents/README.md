# Agents

Part **5** of the [agentic system](../systems/agentic-system.md) — per-task workflows (Harness, Model, Context, and Tools are the other four parts).

Each agent is a folder with three core files tuned for one job.

> The managed-project dispatch described here is **target methodology**. The
> current Hermes install has no worker loop wired (see
> [feature-loop.md](../systems/feature-loop.md)).

## File contract

| File | Purpose |
|------|---------|
| `AGENTS.md` | What the agent does, when to invoke it, inputs/outputs — [AGENTS.md](https://agents.md/) format, read this first |
| `SKILL.md` | How to do the job — [Agent Skills](https://agentskills.io/home) format (`name` + `description` frontmatter); library skill bodies copied inline so the folder is self-contained |
| `rule.md` | Constraints and stop conditions specific to this agent |

`SKILL.md` `name` must match the parent folder. Supporting files (phase prompts, etc.) live in the same folder when the workflow is multi-step.

## Agents

| Agent | Hermes use | Purpose |
|-------|------------|---------|
| [ready](./ready/) | Per-card gate | Branch + worktree + Spec Kit preflight before every card; returns `READY: ok\|blocked` with `WORKTREE` ([feature-loop.md](../systems/feature-loop.md)) |
| [route-work](./route-work/) | Per-card router | Decides `feature\|change\|job` after `ready`; returns `ROUTE` + job `SKILL_PATH` |
| [speckit-orchestrate](./speckit-orchestrate/) | Cursor parent only | Cursor implementation of the feature-loop graph; Hermes implements the same graph via dispatch |
| [speckit-ready](./speckit-ready/) | Shared gate impl | Same body/script as `ready/` (Cursor stage name); canonical script `scripts/ready-check.sh` |
| [pi-harness](./pi-harness/) | Worker backend | Delegates one bounded job to Pi (required `--model`); `pi-spawn.mjs` + `worker-contract.md` |
| [antigravity-harness](./antigravity-harness/) | Worker backend | Delegates one bounded job to the Google Antigravity Python SDK (required `--model`); `agy-spawn.py` + `worker-contract.md` |
| [change](./change/) | `change` path worker | Thin inspect→edit→tester path; stops with `SCOPE: feature` when underspecified |
| [critic](./critic/) | Feature-loop Validation | Adversarial review after converge ([feature-loop.md](../systems/feature-loop.md)) |
| [tester](./tester/) | Feature-loop Validation | Proves flows and runs project `validation_commands` ([feature-loop.md](../systems/feature-loop.md)) |
| [e2e-testing](./e2e-testing/) | On-demand tool | Plans, implements, executes, debugs, and maintains E2E tests across web, iOS, Android, and React Native; honest Passed/Failed/Blocked reporting with human handoff on retry exhaustion |
| [handoff](./handoff/) | On-demand tool | Capture or resume session state in `.agent/handoff/`; not a loop state |
| [pr-reviewer](./pr-reviewer/) | On-demand tool | PR review after Ship on operator request; not a loop state (`SKILL.md` + `prompts.md` + `rules.md`) |
| [project-bootstrapper](./project-bootstrapper/) | Post-onboarding `job` | Scaffolds an onboarded repo from a PRD card; onboarding itself never writes a PRD |
| [prd-writer](./prd-writer/) | Post-onboarding `job` | Writes the PRD as a card after onboarding |
| [task-groomer](./task-groomer/) | Per-card helper | Turns a rough request into a dispatch-ready Hermes kanban card; not a dispatched worker |
| [scout](./scout/) | On-hand tool | Read-only brief / Repo Q&A Hermes may call any time; not a loop state |
| [legacy-system-assessment-agent](./legacy-system-assessment-agent/) | On-hand tool | Standalone evidence-backed assessment Hermes may call any time; not a loop state |
| [plan-reviewer](./plan-reviewer/) | Historical only | Old PIV plan gate; not on the live graph |

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

Third-party persona collections are external reference material, not part of the AiNative feature-loop agents.

| Resource | Description |
|----------|-------------|
| [The Agency (agency-agents)](https://github.com/msitarzewski/agency-agents) | Specialized AI agent personas (engineering, design, marketing, PM, etc.) with setup for multiple coding tools |

## Host editor access (Cursor and OpenCode)

Same folders, two hosts. Do not copy skill bodies into either editor.

| Host | Skills | Invoke |
|------|--------|--------|
| OpenCode | `~/.config/opencode/skill/<name>` → this directory | Skill name |
| Cursor | `~/.cursor/skills/<name>` → this directory | Skill name, or `/<name>` command |

Cursor slash commands live in [`../../.cursor/commands/`](../../.cursor/commands/) and only wrap the skill. That is the Cursor-only difference; see [cursor-setup.md](../knowledge/setup/cursor-setup.md). Relink after adding an agent:

```bash
./docs/knowledge/setup/link-host-skills.sh --all
```

## Add a new agent

1. Copy [`template/`](./template/) to `docs/agents/<task-name>/`
2. Write `AGENTS.md` — purpose, when to use, inputs/outputs
3. Set `SKILL.md` frontmatter: `name` = folder name, `description` = WHAT + WHEN (third person). Pick skills from `_skills/` and copy bodies into `SKILL.md` (add `<!-- source: _skills/<name>/SKILL.md -->` comments)
4. Capture agent-specific constraints in `rule.md`
5. Add supporting prompt files if the workflow has phases
6. Register the agent in this README table
7. If Hermes must dispatch it, wire it to the relevant feature-loop state or named job skill in the control plane.
8. Run `docs/knowledge/setup/link-host-skills.sh --all` so Cursor and OpenCode symlink this folder. Cursor gets a slash command that only points at the skill; do not fork the workflow in the command file.
9. Tune all three files as the agent is used

## Related

- Five-part model: [agentic-system.md](../systems/agentic-system.md)
- Methodology: PIVS ([feature loop](../systems/feature-loop.md#pivs-mapping); historical write-up: [agentic-coding.md](../systems/agentic-coding.md))
- Generic templates (not agents): [systems/](../systems/)
- **Managed projects (target):** Hermes reads AiNative read-only and starts one worker per assigned state or job skill. Not wired in the current install.
- Formats: [AGENTS.md](https://agents.md/), [Agent Skills](https://agentskills.io/specification)
