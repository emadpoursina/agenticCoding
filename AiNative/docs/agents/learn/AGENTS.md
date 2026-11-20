# Learn

Time-boxed `learn` worker ([scoping.md](../../systems/scoping.md)). It builds
a throwaway `spike` or `demo` that answers exactly one question within the
card's appetite. It parks once for the operator's verdict and decision, then
writes a finding. The only thing that ships is the finding and a reference
patch of the prototype. Prototype code never reaches the base branch as code.

> **Status: target methodology — not wired into the current install.**
> The current Hermes install has no worker loop running; see
> [feature-loop.md](../../systems/feature-loop.md).

## When to use

- `route-work` returns `ROUTE: job`, `SKILL: learn` for a card with `## Mode`
  set to `learn: spike` or `learn: demo`
- The operator asks to try, prototype, spike, or demo an idea before deciding
  to build it

## Inputs

- The card: `## Mode`, `## Question`, `## Appetite`, `## Exit Evidence`,
  `## Out of Scope` (all required)
- `STEP` — `build` or `finding`
- `DEADLINE` — when the appetite runs out (ISO 8601), from the parent
- On the `finding` step: the operator's answers to the `build` step's park

## Outputs

- `docs/learn/<YYYY-MM-DD>-<slug>.md` — the finding, including the operator's
  decision (go / rework / kill)
- `docs/learn/<YYYY-MM-DD>-<slug>.patch` — the prototype as a reference patch,
  never applied
- A compact report (see [SKILL.md § Report](./SKILL.md#report))

## Supporting files

| File | Purpose |
|------|---------|
| [SKILL.md](./SKILL.md) | The two steps, the finding format, the report |
| [rule.md](./rule.md) | Constraints and stop conditions |
