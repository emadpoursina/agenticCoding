# Contract: per-card `## Metrics` block

**Feature**: `specs/004-adjust-stage` | **Requirements**: FR-025–FR-029 | **Plan**: [../plan.md](../plan.md) (W6) | **Research**: [../research.md](../research.md) (D1)

The one home for a card's numbers, on the card itself. Written by the **parent**
when the card reaches its terminal state, before Adjust is dispatched. Read by
Adjust (baseline input 1) and by the weekly roll-up. Never written by a worker.

---

## Block

Appended to the card body, last block on the card:

```markdown
## Metrics

- path: feature | change | job
- terminal: merged | blocked | parked | killed | abandoned
- closed_at: 2026-11-26T14:03:11Z
- loops: converge=<n|n/a> critic=<n|n/a> tester=<n|n/a> pr_review=<n|n/a>
- uat: pass | fail | not_run | rounds=<n> | reasons=<comma list or none>
- uat_notes: "<operator's own words, quoted, or none>"
- tokens: input=<n|unknown> output=<n|unknown> total=<n|unknown>
- cost_usd: <number|unknown>
- wall_time_active: <2h14m|unknown>
- boundary: sessions from ready dispatch to the last dispatch before <terminal>; excludes human park time; cost unavailable when the harness or provider does not report it
```

One block per card. A re-opened card keeps its block and appends a new one with
the new `closed_at`; the roll-up uses the latest block whose `closed_at` falls in
its week (D2).

---

## Field rules

| Field | Rule |
|---|---|
| `path` | Required; the card's routed path |
| `terminal` | Required; `merged` requires a UAT pass on the merged head (feature/change) |
| `closed_at` | ISO-8601 UTC; **anchors the roll-up week** — a card belongs to the week this timestamp falls in |
| `loops.<stage>` | Count of **return dispatches caused by that stage** (D1): `converge` = `tasks_appended` re-entry, `critic` = FAIL loop-back, `tester` = FAIL loop-back, `pr_review` = REQUEST CHANGES |
| `loops` = `0` | Only when the stage ran and returned a non-looping verdict (PASS / converged / APPROVE) |
| `loops` = `n/a` | Stage absent on the path, or never ran before the card closed. Never `0` for an absent stage. **Job path**: all four are `n/a` (`converge`, `critic`, `tester`, `pr_review` — the path is `ready → route → one worker → ship`), with `uat.outcome: not_run`; the block is still written so job cards feed the roll-up |
| `uat.outcome` | `pass` \| `fail` \| `not_run`; `not_run` for job cards and cards that closed before ship |
| `uat.rounds` | Rounds attempted (0 when `not_run`) |
| `uat.reasons` | Closed-set ids, required when `outcome: fail`; each item may carry its round (`wrong-behavior@r2`) |
| `uat_notes` | Verbatim operator words; required when `reasons` contains `other` |
| `tokens` | Cumulative across the card's worker sessions, or `unknown`. Never `0` as a stand-in for missing |
| `cost_usd` | As reported by the harness (e.g. a harness report's `totalCostUsd`), or `unknown` |
| `wall_time_active` | Sum of worker session durations; excludes human park/UAT idle time |
| `boundary` | One line; must state what is covered and what is unavailable today (FR-027) |

### Closed UAT failure reason set

| Id | Means |
|---|---|
| `missing-feature` | A promised behavior is absent |
| `wrong-behavior` | Behavior differs from the walkthrough |
| `broken-ui` | Page/control broken, layout or interaction failure |
| `error-crash` | Error, exception, or 5xx on the happy path |
| `missing-evidence` | PR walkthrough or evidence does not let the operator verify |
| `env-setup` | Could not exercise it (config, data, credentials, port) |
| `scope-mismatch` | Shipped more or less than the card asked |
| `docs-wrong` | Documented step or claim is wrong |
| `other` | None of the above — `uat_notes` required |

The operator's words are always kept in `uat_notes`; the id exists so failures
can be **counted** without re-reading prose (FR-026).

---

## Derivation rules (no transcripts, FR-029)

| Field | Derived from |
|---|---|
| `loops.*` | Parent dispatch history + each stage's verdict field (`CONVERGE_OUTCOME`, `CRITIC`, `TESTER`, `VERDICT`) |
| `uat.*` | The UAT exchange on the card (round number, operator verdict, operator words) |
| `tokens`, `cost_usd`, `wall_time_active` | Harness per-session reporting and dispatch timestamps. Where the control plane does not aggregate yet, the field is `unknown` and `boundary` says why |
| `path`, `terminal`, `closed_at` | Card fields at close |

**Today's reality**: this methodology is not wired, so most cards will read
`unknown` for cost and tokens. The contract's job is to make that explicit
rather than to fake zeros; the definition is usable the moment the control plane
reports these numbers.

---

## How the numbers are used

| Question | Fields compared | Window |
|---|---|---|
| Did an accepted rule change help? | `loops.*`, `uat.reasons`, `wall_time_active`, `cost_usd` | The 5 cards before the Change card's merge vs the 5 cards after it on the same path; skip weeks where a different change landed |
| Is a stage concentrating friction? | `loops.<stage>` per card | The roll-up's week |
| Is a rule change noise? | `uat.reasons` share and `loops` unchanged or worse | The same before/after pair |

Comparison rule (must be stated in `feature-loop.md`): compare **per-path**,
**per-stage**, with sample sizes printed, and treat a stage recorded `n/a` as
absent from the sample rather than as zero. No comparison may require
transcripts.

---

## Acceptance (checked by TF-7)

- The block, all field rules, and the closed reason set appear once in
  `feature-loop.md` (this file is the wire format reference).
- Every field admits `unknown`/`n/a` with a stated meaning; no field requires a
  transcript.
- `closed_at` is documented as the roll-up week anchor and matches
  `contracts/rollup-card.md`.
