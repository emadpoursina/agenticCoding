# Records

Append-only operational memory — what happened, what broke, what you decided, and what you tried. Organized by record type.

| Folder | Holds | When to write | Contract |
|--------|-------|---------------|----------|
| [debugging/](./debugging/) | Bug pattern library — symptom, root cause, fix, early detection | Immediately after solving a hard bug | Append-only |
| [decisions/](./decisions/) | Architecture Decision Records (ADRs) | After a significant technical decision | Dated, never modified |
| [postmortems/](./postmortems/) | Incident reviews | Before closing an incident ticket | Dated, append-only |
| [evaluations/](./evaluations/) | Candidates to test — models, tools, agents, workflows | Before adopting something new | Lifecycle status |

Records are historical: date them and never rewrite them. If a decision is reversed or a bug recurs, add a new record that references the old one. Evergreen knowledge that is updated in place lives in [knowledge/](../knowledge/), not here.

Use the `template.md` in each folder. See [ENGINEERING-OS.md](../../ENGINEERING-OS.md) for the full layer contract.
