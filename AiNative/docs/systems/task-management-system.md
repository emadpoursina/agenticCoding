# Task Management System

Lightweight task board for small software teams (roughly 2–15 people). Pair with [PR review](./pr-review-system.md) and [release management](./release-management-system.md).

---

## Goals

- Reduce mental overload and context switching
- Make work, blockers, and ownership visible
- Improve delivery predictability without heavy process

---

## Principles

1. **Simplicity** — If a rule annoys the team, remove or shorten it.
2. **Visibility** — Tasks, blockers, priorities, and decisions live on the board (not only in chat).
3. **Finish before starting** — Fewer active items; smaller tasks.

---

## Board

```text
Backlog → Todo → In Progress → In Review → Testing → Ready For Release → Released → Archived
```

| Column | Purpose | Rules |
|---|---|---|
| **Backlog** | Ideas, bugs, requests | Rough is fine; not committed |
| **Todo** | Ready to build | Clear scope, acceptance criteria, owner assigned |
| **In Progress** | Active development | Dev work only; max 1 feature per developer |
| **In Review** | PR open | Self-tested; follow [PR review system](./pr-review-system.md) |
| **Testing** | QA / staging | Manual, regression, or PO sign-off |
| **Ready For Release** | Approved, not deployed | Groups release scope; see [release system](./release-management-system.md) |
| **Released** | In production | Deploy complete |
| **Archived** | History | Move here to reduce clutter |

### WIP limits

```text
- max 1 active feature per developer (In Progress)
- finish or hand off reviews before starting new feature work
- P0 production bugs may interrupt; note exception on the card
```

### Backlog → Todo

Before moving a card: meet the [Tasks](#tasks) standard (template, priority, label, owner + reviewer). Groom rough Backlog items using [AI — Todo-ready grooming](#ai--todo-ready-grooming) or manually.

---

## Tasks

### Template

```md
## Problem
What is happening?

---

## Expected Result
What should happen?

---

## Platform
- Backend
- Desktop
- Android
- iOS
- Website

---

## Acceptance Criteria
- [ ]
- [ ]

---

## Technical Notes
Optional.

---

## Dependencies
Optional blockers or related tasks.
```

### Good vs bad

| Good | Bad |
|---|---|
| Clear, scoped, testable | Vague, huge, unclear |
| `Add validation when login password is empty` | `Fix login` |

### Priority (use only these four)

| Priority | Meaning |
|---|---|
| P0 | Production issue |
| P1 | Critical feature / blocker |
| P2 | Normal development |
| P3 | Nice-to-have |

### Labels

| Label | Purpose |
|---|---|
| Bug | Existing issue |
| Feature | New functionality |
| Improvement | Enhancement |
| Refactor | Cleanup |
| Release Blocker | Must ship before release |
| Tech Debt | Maintenance |

### Ownership

- One **owner** and one **reviewer** per task
- No shared or unnamed ownership

### AI — Todo-ready grooming

Use when a Backlog card is rough and you want it ready for **Todo**. Read [template](#template), [good vs bad](#good-vs-bad), [priority](#priority-use-only-these-four), and [labels](#labels) first — then run the **Todo-ready grooming** prompt in [task-groomer agent](../agents/task-groomer/).

AI drafts; you fix assumptions, assign owner + reviewer, then move to Todo.

---

## Related workflows

| Stage on board | Doc |
|---|---|
| **In Review** | [pr-review-system.md](./pr-review-system.md) — when to move a card, review checklists, AI-assisted review |
| **Testing → Released** | [release-management-system.md](./release-management-system.md) — branches, staging, deploy, rollback |

**Column ↔ PR (summary)**

```text
PR opened   → In Review
Merged      → Testing (or Ready For Release if no separate QA)
Deployed    → Released (release approver)
```

---

## Meetings

### Monday — planning (30–45 min)

- What must finish this week?
- What is blocked or highest risk?
- What should we *not* start?
- Groom [Backlog → Todo](#backlog--todo) ([task standard](#tasks)); assign owners

No deep debugging or architecture debates.

#### AI — Monday planning prep (async)

Run day before or morning of the meeting. Use **Monday planning prep** in [task-groomer agent](../agents/task-groomer/). AI drafts; team confirms in the meeting.

After AI: confirm shortlist in the meeting; run [Todo-ready grooming](#ai--todo-ready-grooming) on any card still rough.

### Friday — delivery (30–45 min)

- What shipped? What slipped? Why?
- Move done cards to Released / Archived
- What is Ready For Release for the next deploy?

#### AI — Friday meeting prep (async)

Run day before or morning of the meeting. Use **Friday delivery prep** in [task-groomer agent](../agents/task-groomer/). AI drafts; team validates in the meeting.

After AI: validate in the meeting; move cards; confirm deploy per [release system](./release-management-system.md).

---

## Rollout checklist

Use when introducing this system on a new project or with a new group.

**Day 0 — setup (~2–3 hours)**

1. **Roles** — Process owner (board + meetings), default reviewer, release approver (can be same person).
2. **Board** — Create the 8 columns above; add P0–P3 and core labels; paste the task template as the default card body.
3. **WIP** — In Progress: 1 feature per developer; document P0 exceptions in project notes.
4. **Project notes** — Stack, repos, board URL, meetings, release approver (in the project repo or `scratch/`); link [PR](./pr-review-system.md) and [release](./release-management-system.md) docs.
5. **Rules** — Todo needs owner, reviewer, acceptance criteria; tasks before long chat threads; decisions in card comments.

**Column transitions**

| Transition | Rule |
|---|---|
| Backlog → Todo | Prioritized; groomed ([AI](#ai--todo-ready-grooming) or manual); acceptance criteria written |
| Todo → In Progress | Owner starts; respect WIP |
| In Progress → In Review | PR opened; [PR review](./pr-review-system.md) pre-move checks done |
| In Review → Testing | PR approved and merged per release doc |
| Testing → Ready For Release | QA / staging sign-off |
| Ready For Release → Released | Production deploy per [release system](./release-management-system.md) |
| Released → Archived | After sprint close or release notes |

**Week 1**

- Schedule Monday planning and Friday delivery (agendas above).
- First Monday: walk columns + WIP; groom week’s Todo; assign owners.
- First Friday: archive done work; review slips; confirm Ready For Release queue.
- Pilot: few Todo items; template on every card; daily card updates + PR link on card.

**Week 2+**

- Process owner mid-week check: wrong column, missing owner, overloaded In Progress.
- Retrospect: shorten one rule at a time if friction appears.
- New member: read this doc; board access; shadow one Monday/Friday; one P2 task end-to-end with buddy.

**Checklist**

```text
[ ] 8 columns, P0–P3, core labels, task template
[ ] Board URL and release approver written down (project repo or scratch)
[ ] PR + release docs linked
[ ] Monday + Friday scheduled; WIP communicated
[ ] Pilot sprint; first release used Ready For Release → Released
```

### Test flows

**A — Happy path** — P2 Feature: Backlog → Todo (template + owner) → In Progress → PR → In Review → merge → Testing → Ready For Release → deploy → Released → Archived.

**B — P0 bug** — Assign immediately; WIP exception if needed; fast review per [PR doc](./pr-review-system.md); release approver before Released.

**C — Blocked** — Note in Dependencies; surface on Monday; resolve or slip by Friday.

**D — Meetings** — Monday: Backlog → Todo and priorities only. Friday: archive week’s Released cards per team preference.

---

## Outcome

Predictable delivery, visible work, and sustainable pace — not more meetings or bureaucracy for its own sake.
