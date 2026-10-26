---
name: pr-reviewer
description: >-
  Staged PR review (understanding → architecture → risk → one deep focus →
  adversarial). Use when the user runs /pr-review or asks to review a PR,
  branch, or uncommitted changes. Loads prompts in this skill plus optional
  project context from .cursor/agents.yaml.
  Canonical source: AiNative docs/agents/pr-reviewer/ (promoted from Cursor pr-review 2026-10-07).
disable-model-invocation: true
---

# PR review (staged)

Staged workflow: understanding → architecture compliance → risk → one deep focus → adversarial. AI is a thinking partner, not an authority.

Prompts: read `prompts.md` in this skill directory.  
Rules: read `rule.md` in this skill directory.

## Parse input

Accept (`project-root` defaults to this workspace):

- `/pr-review` — review branch changes vs default base
- `/pr-review --pr <number>` — review GitHub PR
- `/pr-review --uncommitted` — working tree only
- `/pr-review --extra @file1 @file2` — one-off context for this run
- Optional: `--focus security|reliability|maintainability|performance` overrides manifest default
- Optional: `--base <branch>` when not using repo default
- Optional: an absolute `project-root` if reviewing a different clone

Resolve relative paths against the workspace.

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
6. If no project config exists, proceed with prompts/rules only (skip subsystem attach; still run Phase 1.5 against obvious nearby design docs if present).

## Detect subsystem (Phase 1.5)

1. Get changed file paths from the diff.
2. Match against `path_triggers` globs in project config.
3. If one subsystem matches, attach its `docs`, `must_use`, `similar`.
4. If multiple match, run Phase 1.5 per subsystem.
5. If none match and `subsystems.default` exists, use it.

## Skip Phase 1.5

Skip when the PR is clearly typo-only, dependency-only, or config-only with no logic — per `rule.md` and `skip_phase_1_5_when` in project config.

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
| 4 — Deep focus | Exactly one of security / reliability / maintainability / performance; skipped if every Phase 2 rating is Low or None |
| 5 — Adversarial | Final AI pass |

If the project has extra review rules (e.g. `.cursor/rules/*pr-review*`), apply those in addition to the one Phase 4 focus when the PR touches API or multi-client behavior.

## Scores

Keep the two 0.0–1.0 scores (one decimal) on every finding:
  - how often it could happen
  - if it happended, how much trouble it makes

Trouble sets severity. Frequency only sorts.

- Critical: trouble ≥ 0.8
- Warning: trouble 0.5–0.7
- Suggestion: trouble below 0.5

Anchors: 0.9 = data loss, security hole, wrong money, outage. 0.5 = wrong result on a rare path with a workaround. 0.2 = naming, docs, missing tests.

Never multiply the two to gate. A rare data-loss bug would then rank below a common cosmetic one.

Score every concrete problem in Phases 1.5, 2, 4, and 5 — not the Phase 1 summary.

```markdown
### <problem title>
- how often it could happen: 0.X
- if it happended, how much trouble it makes: 0.Y
- why: <one short reason>
```

## Merge gate

Same labels as `critic` and `verification`:

- **Critical**: merge blocker. Trouble ≥ 0.8 (see Scores) and a named trigger: file:line plus the input that hits it. No trigger, no finding.
- **Warning**: should fix. Never blocks.
- **Suggestion**: optional. Never blocks. Tests, naming, docs, duplication, "could be cleaner".

Scope: only lines this PR adds or changes. Older code gets at most a Pre-existing note, never Critical.

Verdict:
- **BLOCKED**: Phase 1.5 is blocking.
- **REQUEST CHANGES**: at least one Critical.
- **APPROVE**: no Critical. Warnings and Suggestions don't change this. Zero findings is a valid result.

Show at most 5 Warnings and 5 Suggestions, highest trouble score first.

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
## Follow-ups (Warning and Suggestion, non-blocking)
## Accepted risks (author-marked)
## Verdict — APPROVE / REQUEST CHANGES / BLOCKED (Phase 1.5)
## Human checklist (Phase 6)
```

Every listed problem must include both scores.

Phase 6 stays with the human. APPROVE means "merge recommended," not auto-merge.

## Re-review (second run or later on the same PR)

Pass the previous report with `--extra @<previous-review>.md`.

1. Check each previous Critical: fixed or not, with file:line.
2. Review only commits since the last reviewed commit.
3. Raise no new Warning or Suggestion in code this round didn't change.
4. Don't re-raise a listed finding unless its code changed. An author note "accepted: <reason>" moves it to Accepted risks.
5. If the author disputes a finding with file:line evidence, re-read that code once. Drop it if the evidence holds. Otherwise keep it and state the trigger.
6. From round 3 on, report Criticals only.

## Errors

- `project-root` missing or not a git repo → explain and stop
- `gh` missing when `--pr` used → explain and stop
- No diff → report "nothing to review"

Do not fix code unless the user asks after the review.
