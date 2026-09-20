---
name: pr-reviewer
description: >-
  Staged PR review for any project. Use when the user runs /pr-review or asks
  to review a PR or branch in a project by path. Loads global prompts plus
  project-specific context from .cursor/agents.yaml.
---

# PR reviewer (global)

Staged workflow: understanding → architecture compliance → risk → one deep focus → adversarial. AI is a thinking partner, not an authority.

Prompts: read `prompts.md` in this skill directory.  
Rules: read `rules.md` in this skill directory.

## Parse input

Accept:

- `/pr-review <project-root>` — review branch changes vs default base
- `/pr-review <project-root> --pr <number>` — review GitHub PR
- `/pr-review <project-root> --uncommitted` — working tree only
- `/pr-review <project-root> --extra @file1 @file2` — one-off context for this run
- Optional: `--focus security|reliability|maintainability|performance` overrides manifest default
- Optional: `--base <branch>` when not using repo default

`project-root` must be an absolute path. Resolve relative paths against the workspace.

## Load project context

1. `cd` to `project-root` for all git/gh commands and file reads.
2. Load shared + agent config (first match wins for agent-specific file):
   - `<project-root>/.cursor/agents.yaml` — preferred; use `agents.pr-reviewer` section
   - `<project-root>/.cursor/pr-review.yaml` — legacy single-agent file
3. From config, collect:
   - `context.*` — rules, architecture, adrs, debugging (shared across agents)
   - `agents.pr-reviewer.default_focus` (Phase 3 tie-breaker only), `subsystems`, `path_triggers`, `skip_phase_1_5_when`
4. Attach `@` files that exist. Skip missing paths silently.
5. Merge `--extra` paths into Phase 1.5 context.

## Detect subsystem (Phase 1.5)

1. Get changed file paths from the diff.
2. Match against `path_triggers` globs in project config.
3. If one subsystem matches, attach its `docs`, `must_use`, `similar`.
4. If multiple match, run Phase 1.5 per subsystem.
5. If none match and `subsystems.default` exists, use it.

## Skip Phase 1.5

Skip when the PR is clearly typo-only, dependency-only, or config-only with no logic — per `rules.md` and `skip_phase_1_5_when` in project config.

## Get diff

In `project-root`:

| Mode | Command |
|------|---------|
| `--pr N` | `gh pr diff N` and `gh pr view N` for title/body |
| default | `git diff <base>...HEAD` (+ staged/unstaged if meaningful) |
| `--uncommitted` | `git diff` and `git diff --cached` |

Base branch: `--base` if given, else `git symbolic-ref refs/remotes/origin/HEAD` or `main`/`master`.

Large PR (>500 lines changed): run diff compression prompt from `prompts.md` before Phase 1.

## Run phases (in order)

Read the matching prompt block from `prompts.md` each phase. Do not combine phases in one response.

| Phase | Stop condition |
|-------|----------------|
| 1 — Understanding | No review yet — mental model only |
| 1.5 — Architecture compliance | **blocking** → stop entire review, request rework |
| 2 — Risk classification | Continue |
| 3 — Select focus | `--focus` if given; else the highest Phase 2 risk rating; `default_focus` only on a tie |
| 4 — Deep focus | Exactly one of security / reliability / maintainability / performance |
| 5 — Adversarial | Final AI pass |

## Problem scores (required)

For each problem give 2 score between 0.0 - 1.0:
  - how often it could happen
  - if it happended, how much trouble it makes

Use one decimal (e.g. `0.3`, `0.8`). Score every concrete problem in Phases 1.5, 2, 4, and 5 — not the Phase 1 summary.

```markdown
### <problem title>
- how often it could happen: 0.X
- if it happended, how much trouble it makes: 0.Y
- why: <one short reason>
```

## Output format

One consolidated report:

```markdown
# PR review — <project-name> (<pr or branch>)

## Summary
## Phase 1 — Understanding
## Phase 1.5 — Architecture (or SKIPPED — reason)
## Phase 2 — Risks
## Phase 3 — Focus chosen
## Phase 4 — Deep review
## Phase 5 — Adversarial
## Verdict — APPROVE / REQUEST CHANGES / BLOCKED (Phase 1.5)
## Human checklist (Phase 6)
```

Every listed problem must include both scores.

Phase 6 is for the human — do not auto-approve.

## Errors

- `project-root` missing or not a git repo → explain and stop
- `gh` missing when `--pr` used → explain and stop
- No diff → report "nothing to review"

Do not fix code unless the user asks after the review.
