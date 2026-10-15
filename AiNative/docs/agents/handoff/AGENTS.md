# Handoff

Capture current session state to a resumable file, or resume from one, so work
survives across sessions and agents.

## When to use

- User says `handoff`, `hand off`, `save state`, `pick this up later`
- User says `resume`, `continue from handoff`, `pick up <slug>`
- User passes work to another agent (`next_agent`, `hand to tester/critic`)

## Inputs

- Capture: goal (1 sentence), done criteria, open TODOs, blockers if not
  observable; everything else is gathered from git + workspace
- Resume: handoff file path or slug; `DIR = REPO_ROOT/.agent/handoff/`

## Outputs

- Capture: `HANDOFF: captured`, `FILE`, `NEXT`, plus copy-paste Next Prompt block
- Resume: `HANDOFF: resumed`, `FILE`, `GOAL`, `STATE`, `BLOCKERS`, then starts
  first open TODO
- Artifact: `REPO_ROOT/.agent/handoff/<slug>-YYYYMMDD-HHMM.md` (gitignored, never
  committed unless asked)

## Supporting files

| File | Purpose |
|------|---------|
| [SKILL.md](./SKILL.md) | Capture/resume procedure + handoff file template |
| [rule.md](./rule.md) | Constraints and stop conditions |
