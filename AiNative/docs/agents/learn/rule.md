# Rules — Learn

Constraints specific to the `learn` worker. Methodology:
[scoping.md](../../systems/scoping.md).

## Must

- Answer the card's one question, and only that question.
- Stop at `DEADLINE`. Write what was learned, even when the question is
  unanswered (`BREAKER: tripped`).
- Leave the worktree diff with exactly two changed paths after the `finding`
  step: the finding file and its patch.
- Record the operator's decision verbatim. Recommend one if asked; never
  decide.
- Say plainly what the prototype faked, so nobody mistakes it for a build.

## Must not

- Write a PRD, `spec.md`, `plan.md`, `tasks.md`, or tests beyond what the
  question needs.
- Leave prototype edits to tracked files in the worktree after the `finding`
  step.
- Extend the appetite, start a second question, or polish past the exit
  evidence.
- Commit, push, open a PR, merge, or deploy. The parent ships.
- Add a dependency to the project's manifests that survives the `finding`
  step.

## Stop conditions

- A required card section (`Mode`, `Question`, `Appetite`, `Exit Evidence`,
  `Out of Scope`) is missing or the question has more than one answerable
  part: `STATUS: blocked`, name what is missing. Do not build.
- `DEADLINE` already passed when the `build` step starts: skip building and
  go to the park with `BREAKER: tripped`.
- The work needs real credentials, production data, or a paid service the
  card does not name: park and ask.

## Related enforcement

- [feature-loop.md § Card paths](../../systems/feature-loop.md#card-paths) —
  a learn card runs on the `job` path
- [route-work](../route-work/SKILL.md) — maps `mode: learn` to `SKILL: learn`
