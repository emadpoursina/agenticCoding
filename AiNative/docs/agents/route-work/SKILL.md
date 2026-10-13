---
name: route-work
description: >-
  Decides which execution path a task takes (feature, change, or job) after
  ready passes. Use when /speckit-orchestrate launches the route stage.
disable-model-invocation: true
---

# Route work

Stage 1 of `/speckit-orchestrate`, right after ready. Decide the path. Do not
do the work. Do not write files, specs, or code.

```text
                    ┌─ feature → speckit-orchestrate (full Spec Kit flow)
route-work ─────────┼─ change  → change skill
                    └─ job     → one named skill
```

## Inputs (from the parent prompt)

- `REPO_ROOT` — target git repository
- `FLOW_ID` — opaque run id minted by the parent
- `TASK_DESCRIPTION` — user arguments verbatim
- `REQUESTED_PATH` — `feature`, `change`, `job`, or `none`
- `REQUESTED_SKILL` — skill name the user named, or `none`

## Decide

1. If `REQUESTED_PATH` is not `none`, use it. Do not second-guess the user.
2. Otherwise read the task, glance at the repo (README, layout, the files the
   task names), and pick one:

| Path | Pick it when |
| --- | --- |
| `feature` | New or changed product behavior that needs a spec, a plan, or design choices. Touches several areas, adds a contract/API/schema, or leaves open questions. |
| `change` | A small code edit that is already fully specified: clear expected result, a few files, no architectural decision, no new dependency. A bug fix with a known cause, a copy tweak, a config value, a small refactor. |
| `job` | The output is not a code change: write a PRD, research, documentation, analysis, a report, project bootstrap from a PRD. |

3. When unsure between `feature` and `change`, pick `feature`. When unsure
   whether a named skill fits, pick `feature` or `change` instead of `job`.

## Resolve the job skill (job only)

Pick one existing skill. Never invent one and never pick a Spec Kit command
or `speckit-*` skill. Use `REQUESTED_SKILL` when given. Look in this order and
take the first `SKILL.md` that exists:

1. `<AINATIVE>/docs/agents/<name>/SKILL.md` (canonical — AiNative is the
   source of truth; mounted read-only at `/opt/data/mnt/AiNative` for Hermes
   workers, symlinked at `~/.cursor/skills/<name>/SKILL.md` on the host)
2. `REPO_ROOT/.pi/skills/<name>/SKILL.md` (project override, Pi enrollment)
3. `REPO_ROOT/docs/agents/<name>/SKILL.md` (AiNative agent folders, legacy path)

Legacy fallbacks (honored, not canonical): `REPO_ROOT/.cursor/skills/<name>/SKILL.md`,
`~/.cursor/skills/<name>/SKILL.md`, `REPO_ROOT/.opencode/skill/<name>/SKILL.md`,
`~/.config/opencode/skill/<name>/SKILL.md`.

Match the task to a skill by its `description`. Examples: a PRD →
`prd-writer`; bootstrap from a PRD → `project-bootstrapper`. If no skill
fits, return `ROUTE: job`, `SKILL: none`, and say what kind of skill is
missing. Do not pick a near miss.

## Report

Return exactly:

```text
FLOW_ID: <flow_id>
ROUTE: feature | change | job
SKILL: <skill name, or none>
SKILL_PATH: <absolute path to SKILL.md, or none>
WHY: <one or two sentences>
```
