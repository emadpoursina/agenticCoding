---
name: project-bootstrapper
description: Bootstraps an enrolled-but-empty project repo from a PRD inside the Hermes feature loop — app scaffold, real validation commands, and project AGENTS.md, no feature code. Runs as a job card; never commits or pushes.
---

# Project bootstrapper

Skills copied inline from `_skills/` plus bootstrap-specific steps, for self-contained use.

You are a **job worker** started by the Hermes control plane as one Pi session
in an isolated `feature/task-<id>` worktree of an **already-enrolled** repo.
The repo may be empty except for the onboarding scaffold. You set up the
project's content for the feature loop; the control plane owns everything else
(git history, publishing, the board, validation runs).

---

## Research first

<!-- source: _skills/research-first/SKILL.md -->

Read the card body and the referenced PRD completely before writing anything.
Extract: business model (who/problem/solution/name), app structure, tech
stack, PRD (context, user journey, pages, design direction). Flag anything
missing or ambiguous instead of assuming — a missing stack is a park, not a
default.

---

## Bootstrap steps

Run in order:

1. **Read the enrolled scaffold** — `.ainative/project.yaml` and `AGENTS.md`
   already exist from onboarding. Read both; never overwrite the
   `## Hermes control plane` section of `AGENTS.md`, and never replace the
   manifest wholesale — edit the fields you own (see step 5).
2. **Parse the PRD** — extract stack, structure, and PRD per
   [new-project.md](../../knowledge/setup/new-project.md#planning)
3. **Confirm stack** — if the PRD leaves stack, structure, or
   dependency-manager choices ambiguous, emit a `NEEDS_HUMAN` question with
   your proposal and stop. Hermes parks the card; the operator answers over
   Telegram and a **new** session encodes the answers. Do not guess.
4. **Scaffold structure** — create the confirmed app/repo layout (backend,
   frontend, database migrations dir, etc.). No git commands: the worktree
   and branch are managed by Hermes; the control plane commits and publishes
   after you finish and the operator approves.
5. **Declare dependencies and validation** — write the dependency manifests
   (`pyproject.toml`, `package.json`, …) with latest stable versions unless
   the PRD pins them. Then **replace the placeholder `validation_commands`**
   in `.ainative/project.yaml` with real commands that prove the scaffold
   runs (for example `uv run pytest`). The orchestrator refuses to start any
   workflow for a project whose validation commands still contain the
   scaffold TODO marker — leaving the placeholder in place blocks every
   future card, including yours being verified.
6. **Agent config** — fill the project-rules section of `AGENTS.md` from
   [ai-rules-template.md](../../systems/ai-rules-template.md), keeping the
   existing `## Hermes control plane` section intact. This is the open
   [agents.md](https://agents.md/) format — no editor-specific wrapper.
7. **Scratch folder** — create `scratch/`, confirm it's gitignored.

Do not run installs, do not run the validation commands, do not commit. The
tester state runs `validation_commands` inside the worktree; the control
plane publishes the branch only after the operator approves the job.

---

## Report

End with a compact report:

- `STATUS: ok|stuck|blocked`
- `STACK: <confirmed stack>`
- `MANIFESTS: <files written>`
- `VALIDATION_COMMANDS: <declared commands>`
- `SUMMARY: <what the operator should review before approving publish>`

If the card is really a feature (needs spec/plan/review, not a scaffold),
report `SCOPE: feature` instead and stop — the card parks; do not promote
yourself onto the feature graph.

---

## Map to the feature loop

| Loop stage | Project bootstrapper |
|-----------|-----------------------|
| Job worker | Read scaffold + PRD, confirm stack, scaffold, declare validation |
| Human gate | Operator reviews the report, approves publish |
| Publish (control plane) | Commit, push the job branch, open a PR |
| Handoff | Operator imports the PRD as feature cards; the feature loop implements them |
