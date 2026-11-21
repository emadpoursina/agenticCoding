# Proposal writer agent

Turns an existing Product Requirements Document into a short, client-ready
commercial proposal (English or Persian). The PRD stays the source of truth
for scope; pricing is recommended to the developer and only then written into
the client document.

This file is the agent's instruction surface in the open [AGENTS.md](https://agents.md/) format — standard Markdown, no required fields. Coding agents load the nearest `AGENTS.md`; keep this file the place for role, triggers, and I/O.

## When to use

- A PRD (and usually a phase plan) already exists and the developer needs a
  proposal the client can approve
- The work is AI, automation, custom software, or technical consulting for a
  small-business client
- The proposal may need to be in Persian as well as English

## Inputs

- A PRD file in the repo (required)
- Optional: phase plan, client notes, budget, prior proposals
- Developer-approved price before the client draft is written

## Outputs

- `PROPOSAL.md` at the project root, or a path the user specifies: overview,
  solution, scope, phases and deliverables, timeline, approved investment and
  payment terms, assumptions and exclusions, next steps
- Persian files include `lang: fa` / `dir: rtl` and are passed through
  `scripts/persian-normalize.py`

## Supporting files

| File | Purpose |
|------|---------|
| [SKILL.md](./SKILL.md) | Intake → analysis → pricing park → client draft |
| [rule.md](./rule.md) | PRD-as-source-of-truth, no invented prices, stop conditions |
| [persian.md](./persian.md) | Formal Persian register, glossary, RTL/PDF notes |
| [scripts/persian-normalize.py](./scripts/persian-normalize.py) | Unicode-safe ye/kaf, digits, ZWNJ |
