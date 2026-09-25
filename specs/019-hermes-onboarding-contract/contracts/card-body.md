# Contract: Card body (Feature Cards and Task Cards)

Owner module: `personalAgent/src/hermes_kanban/onboard.py` (composition +
validation), `board.py` (read side). The card body is external input; every
rule here is enforced fail-closed at the trust boundary (constitution IV).

## Sections

A card body is UTF-8 text with `## Heading` sections (parsed by the existing
`board._sections` / `onboard._H2_HEADING`).

| Section | Required | Allowed values | Notes |
|---------|----------|----------------|-------|
| `Priority` | yes (existing) | `P0`–`P3` | unchanged (`validate_card_draft`) |
| `Problem` | yes (existing) | non-empty | unchanged |
| `Expected Result` | yes (existing) | non-empty | unchanged |
| `Path` | yes for work cards (existing) | `feature` \| `change` \| `job` | unchanged read in `board._task` |
| `Profile` | **NEW**, optional on legacy cards | `{task-generator\|executor\|validator}[:named-strategy-ref]` | see rules below |
| `Parent` | **NEW**, child Task Cards only | exactly one existing Feature Card id | top-level cards MUST NOT carry it |
| `Dependencies` | optional (existing) | task ids, one per line / comma-separated | unchanged parse |
| `Skill` | optional (existing) | job-path allowlist | unchanged |

## Profile rules (FR-013, FR-014, FR-014a)

1. `role` ∈ {`task-generator`, `executor`, `validator`} — anything else is
   rejected with a message naming the allowed roles.
2. Optional strategy suffix uses the existing named-reference rule
   (`must be a named reference`; `/` and `\` rejected) — same checks as
   harness model profiles in `external_framework.py` / `executor.py`.
3. A value matching the existing provider-leak pattern (vendor/provider/model
   forms) is rejected: *profiles express execution strategy, never a provider*.
4. At card creation the system composes the default: role selected by
   `## Path` — explicitly `feature` → `task-generator`, `change` →
   `executor`, `job` → `executor` — sourced from project defaults
   (`profiles.defaults` keys `feature`/`change`/`job` in config/overlay;
   fallback = the role name itself). Operator overrides of the section value
   pass the same validation.
5. Absent `## Profile` on an existing card is not an error (idempotency: no
   rewrite of enrolled projects); the orchestrator applies the Path default
   at claim time without mutating the card body.

## Parent rules (FR-011, FR-023)

1. Child Task Cards created by the task-generator carry `## Parent:
   <feature-card-id>` and, where supported, a native `task_links` row.
2. The referenced id MUST exist on the same native project; a dangling or
   self parent fails card creation.
3. `BoardTask` exposes **NEW** `parent_id: str = ""` and `profile: str = ""`;
   the parent is always derivable from the child (body ∪ task_links).

## Hierarchy invariants

- A Feature Card has no `## Parent`; a Task Card has exactly one.
- No card's any section encodes an internal workflow state name
  (`ready, specify, clarify, confirm, plan, tasks, implement, converge,
  critic, tester, uat, pr-review, publish`) as its Path/Profile value (FR-027).
- Child creation is idempotent per parent + title (existing
  `--idempotency-key` `_slugify(title)` mechanism); re-running decomposition
  never duplicates children.
