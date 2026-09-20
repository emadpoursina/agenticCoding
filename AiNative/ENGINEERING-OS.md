# Engineering Operating System

A personal knowledge system for developers transitioning into technical operator and engineering lead roles. This document describes the full structure, the reasoning behind each layer, and the rituals that keep it alive.

---

## What this is

This is not a second brain. It is not a productivity system. It is an **engineering operating system** — a structured repository of knowledge, decisions, and operational patterns that compounds over time.

The goal is to reduce the cognitive overhead of repeated work, preserve the knowledge that normally evaporates after a bug is fixed or a decision is made, and give you fast retrieval under pressure.

It works inside Git. It requires no external tools. It stays alive through three weekly rituals, not through discipline alone.

---

## Repository structure

```text
AiNative/
├── README.md
├── .cursor/rules/                 # Cursor rules (engineering-os, ai-rules, Commit-style)
│
├── docs/
│   ├── README.md
│   │
│   ├── systems/                       # How you work — stable, rarely changes
│   │   ├── task-management-system.md
│   │   ├── pr-review-system.md
│   │   ├── release-management-system.md
│   │   ├── client-compatibility-system.md
│   │   ├── agentic-system.md          # AI methodology (Harness, Model, Context, Tools, Agents)
│   │   ├── agentic-coding.md          # PIV — Plan, Implementation, Validation
│   │   ├── validation-layer.md
│   │   ├── agent-handoff-template.md
│   │   ├── system-understanding-brief-template.md
│   │   ├── cursor-rules.md
│   │   └── ai-rules-template.md
│   │
│   ├── agents/                        # Per-task AI agents — AGENTS.md, SKILL.md, rule.md
│   │   ├── README.md
│   │   ├── _skills/                   # Central skill library (source of truth)
│   │   ├── template/                  # Scaffold for new agents
│   │   ├── scout/
│   │   ├── plan-reviewer/
│   │   ├── critic/
│   │   ├── tester/
│   │   ├── pr-reviewer/
│   │   ├── task-groomer/
│   │   ├── prd-writer/
│   │   ├── project-bootstrapper/
│   │   └── legacy-system-assessment-agent/
│   │
│   ├── knowledge/                     # Evergreen knowledge — updated in place
│   │   ├── README.md
│   │   ├── setup/
│   │   ├── commands/
│   │   ├── architecture/
│   │   ├── snippets/                  # Copy-paste code only
│   │   ├── backup-system.md
│   │   └── tools.md
│   │
│   └── records/                       # Dated, append-only memory
│       ├── README.md
│       ├── debugging/                 # Bug pattern library
│       ├── decisions/                 # ADRs
│       ├── postmortems/               # Incident reviews
│       └── evaluations/               # Candidates to test
│
└── scratch/                           # Gitignored — raw capture, no quality bar
    └── .gitignore
```

---

## The four layers

Four folders, one decision each at capture time: **how you work** → `systems/`, **AI partners** → `agents/`, **evergreen knowledge** → `knowledge/`, **what happened** → `records/`. When you are unsure, the answer is always `scratch/` followed by a Friday review.

### Layer 1 — Systems (`docs/systems/`)

**What it holds:** Universal operational workflows and AI methodology. How to run a release. How to review a PR. How to manage a task board. The five-part agentic system, PIV methodology, validation-layer architecture, and shared templates.

**Why it exists:** These are the processes you repeat on every team, plus the AI methodology that underpins every per-task agent. Writing them once and running them everywhere eliminates reinvention and gives you a baseline to iterate on rather than a blank page every time.

**How it compounds:** Each time you run a workflow and notice friction, you update the system doc. Over time the docs become refined by real use, not theoretical best practice. When you join a new team, you bring a proven playbook rather than starting from scratch.

**Rule:** These docs change rarely. If you are editing them frequently, they have become operational notes, which belong in `records/` or `scratch/`. No task-specific prompts here — those belong in `agents/<name>/`.

---

### Layer 2 — Agents (`docs/agents/`)

**What it holds:** Per-task AI agents. Each agent is a folder with three core files: `AGENTS.md` (what it does, when to use — [agents.md](https://agents.md/) format), `SKILL.md` (how to do the job — [Agent Skills](https://agentskills.io/home) format with `name` + `description` frontmatter; library skill bodies copied inline from `_skills/<name>/SKILL.md`), and `rule.md` (agent-specific constraints). A central `_skills/` library is the source of truth; each agent's `SKILL.md` copies what it needs for self-contained use.

**Why it exists:** Prompts scattered across workflow docs are hard to tune per task. One folder per agent lets you iterate `AGENTS.md`, `SKILL.md`, and `rule.md` independently as you learn what works for that job — without cross-contaminating other agents.

**How it compounds:** For every new task, add a new agent folder from `template/`. Reusable skills discovered during tuning go into `_skills/<name>/SKILL.md` and get copied to other agents. Over time you build a library of tuned agents and skills that encode how you work with AI on specific jobs.

**Rule:** One agent per task type. Three core files always present. Skills are copied inline in `SKILL.md` (not just linked). Supporting phase files stay in the same agent folder.

---

### Layer 3 — Knowledge (`docs/knowledge/`)

**What it holds:** Evergreen technical knowledge organized by domain. Commands for every tool you use. Setup guides for projects and servers. Architecture patterns for backend, database, and infrastructure work. Copy-paste code in `snippets/`.

**Why it exists:** During an incident or a late-night deploy you need one thing: the exact command, fast. A single flat file does not scale. Domain folders give you a three-second mental path to any piece of information: `knowledge/commands/postgres.md` for Postgres, `knowledge/commands/nginx.md` for Nginx.

The `architecture/` subfolder is where you move from "I know commands" to "I know patterns." It holds opinionated notes about backend patterns, database design choices, and infrastructure decisions — updated as your views evolve. This is how senior technical knowledge compounds.

`snippets/` is the action layer: working, copy-pasteable code with no prose. Reference docs explain how things work; snippets are ready to use. Keeping them separate means you never confuse "reading to understand" with "copying to deploy."

**How it compounds:** Every time you learn a command you have had to look up three times, you add it. Every time you discover a pattern or a config that works reliably, you add it. The knowledge layer grows slowly and stays trustworthy because it only contains things tested in production.

**Rule:** Knowledge docs have no dates. They are updated in place. If information is time-sensitive or context-specific, it does not belong here. Snippet files contain no prose — a one-line comment above a block is acceptable; full explanations belong in reference docs.

---

### Layer 4 — Records (`docs/records/`)

**What it holds:** Dated, append-only operational memory. Four record types, each with a `template.md`:

| Folder | Holds | Written when |
|--------|-------|--------------|
| `debugging/` | Bug pattern library — symptom, root cause, fix, early detection | Immediately after solving a hard bug |
| `decisions/` | Architecture Decision Records (ADRs) | After a significant technical decision |
| `postmortems/` | Incident reviews for production failures | Before closing the incident ticket |
| `evaluations/` | Candidates to test — models, tools, agents, workflows | Before adopting something new |

**Why it exists:** This is the highest-leverage layer for engineering growth. The difference between a mid-level and a senior engineer is not raw ability — it is pattern recognition built from accumulated, organized experience. Without a system, every hard bug you solve leaves your head within a week; every decision loses its reasoning; every incident is repeated. With this layer, each becomes a permanent asset.

**Why one folder, four types:** They share one contract — *dated, never rewritten* — and one retrieval question: "what happened before?" Splitting them into separate top-level folders adds navigation cost without changing how you use them.

**How it compounds:** After six months you stop re-solving problems and re-litigating decisions. After a year you recognize incident patterns before they escalate. Evaluations stop you re-testing the same tool every quarter — rejected ones record *why*, adopted ones link to where they landed.

**Rule:** Date every record. Write it while context is fresh. Never modify a record after the fact — if a decision is reversed or a bug recurs, write a new record that references the old one.

#### Debugging template

```md
## [Short title of the bug]

**Date:** YYYY-MM-DD
**Domain:** postgres / docker / nginx / auth / billing / desktop

### Symptom
What you saw. Exact error messages if available.

### Root cause
What was actually wrong.

### Fix
What resolved it.

### How to detect early
What would have caught this sooner.

### Related patterns
Links to similar issues or decisions.
```

#### ADR template

```md
# ADR-NNN: [Title]

**Date:** YYYY-MM-DD
**Status:** Accepted / Deprecated / Superseded by ADR-NNN

## Context
What was the situation that required a decision. What constraints existed.

## Decision
What we decided.

## Consequences
What this enables. What trade-offs we accepted. What becomes harder.

## Rejected alternatives
What we considered and why we said no.
```

#### Postmortem template

```md
# YYYY-MM-DD: [What broke]

**Severity:** P0 / P1 / P2
**Duration:** X hours
**Services affected:** ...

## Timeline
- HH:MM — first symptom observed
- HH:MM — investigation started
- HH:MM — root cause identified
- HH:MM — fix deployed
- HH:MM — confirmed resolved

## Root cause
...

## What we did to fix it
...

## What would have prevented it
...

## Follow-up tasks
- [ ] ...
```

#### Evaluation template

Evaluations record a **hypothesis** and **test plan** before running, then **results** and a lifecycle status (`Queued` → `Testing` → `Promising` → `Adopted` / `Rejected`). On adoption, promote to the target layer and link where it landed; on rejection, keep the file with a short verdict.

---

### Scratch (`scratch/`)

**What it holds:** Raw capture and temp files. Meeting notes, pasted error logs, agent handoffs, drafts, half-formed ideas — anything you want in the workspace but not in git.

**Why it exists:** Most knowledge systems fail because people try to write final-quality notes during raw work. The friction is too high and nothing gets written. Scratch has no quality bar. Write badly. Agents may read and write here freely. The goal is to not lose the information, not to organize it immediately.

**Rule:** Every project includes `scratch/`. Gitignore contents (`scratch/*`, keep `!scratch/README.md` so the folder exists in clone). Nothing in scratch is canonical — promote into real docs or delete. Every Friday, spend ten minutes reviewing scratch and either promoting valuable content to the right layer or deleting it.

---

## Retrieval by mental path

The structure is designed so retrieval requires no search. The folder names are the retrieval system.

| When you need... | Go to... |
|---|---|
| A specific command | `knowledge/commands/<tool>.md` |
| Project or server setup | `knowledge/setup/` |
| Local databases (Docker) | `knowledge/setup/local-shared-services.md` |
| An architecture pattern | `knowledge/architecture/` |
| A working config or script | `knowledge/snippets/<type>/` |
| How to run a release | `systems/release-management-system.md` |
| Agent handoff between AI passes | `systems/agent-handoff-template.md` |
| A per-task AI agent | `agents/<name>/` — start with `AGENTS.md` |
| Agentic system (five parts) | `systems/agentic-system.md` |
| Harness setup (Tmux + Cursor CLI) | `knowledge/setup/harness.md` |
| PIV methodology (Plan, Implementation, Validation) | `systems/agentic-coding.md` |
| Validation layer architecture | `systems/validation-layer.md` |
| PIV Validation — adversarial review | `agents/critic/` |
| PIV Validation — prove the code works | `agents/tester/` |
| PR review prompts | `agents/pr-reviewer/` |
| Task grooming / meeting prep | `agents/task-groomer/` |
| New-project scaffolding | `agents/project-bootstrapper/` |
| Legacy assessment (strategies, estimates) | `agents/legacy-system-assessment-agent/` |
| Reusable agent skills | `agents/_skills/` |
| How to run a planning meeting | `systems/task-management-system.md` |
| A bug you have seen before | `records/debugging/<domain>/` |
| Why a decision was made | `records/decisions/` |
| What broke and why | `records/postmortems/` |
| Something new to test | `records/evaluations/` |

Project-specific context (board URL, approvers, stack) belongs in the project repo or `scratch/` — not in this OS repo.

If you find yourself searching instead of navigating, a document is in the wrong place.

---

## The three rituals

The system does not stay alive through organization alone. It stays alive through three short rituals.

### Ritual 1 — Capture during work (zero friction)

During active work, write in `scratch/`. Write badly. One file per day or per topic. The only goal is to not lose the information.

When you solve a hard bug, stop for ten minutes and write the debug note immediately. Context degrades fast — a note written the same day is worth ten written a week later.

### Ritual 2 — Friday review (15 minutes)

Every Friday, open `scratch/` and do three things:

1. Promote anything valuable to the right layer (`records/`, `knowledge/`, `systems/`, `agents/`).
2. Update any knowledge doc that was out of date during the week.
3. Delete everything that does not need to be kept.

This is the entropy prevention ritual. Without it, the system drifts toward a graveyard of stale notes.

### Ritual 3 — After every significant event (10–30 minutes)

Three triggers, each with a specific response:

| Event | Action |
|---|---|
| Solved a hard bug | Write a debug note in `records/debugging/<domain>/` |
| Made a significant architectural decision | Write an ADR in `records/decisions/` |
| Production incident | Write a postmortem in `records/postmortems/` before closing the ticket |

These three responses are what separate a knowledge system that compounds from one that stagnates.

---

## Information entropy prevention

Three rules that do the most work:

**One canonical location per type of information.** Each layer has a contract. `records/debugging/` only accepts bug patterns. `records/decisions/` only accepts ADRs. `knowledge/snippets/` only accepts working code with no prose. When you are not sure where something goes, the answer is `scratch/` followed by a Friday review.

**Promote, do not duplicate.** If you find yourself copying a snippet from one document to another, that is a signal: the snippet belongs in `knowledge/snippets/` and both documents should link to it. Duplication is how knowledge systems rot.

**Date records, not knowledge.** Files in `knowledge/` are evergreen — no dates, updated in place. Files in `records/` are dated and append-only. This distinction tells you at a glance whether a note is "current" or "historical record." You never need to wonder whether a knowledge doc is stale — you just update it.

---

## How each layer maps to engineering growth

| Layer | What it builds |
|---|---|
| `systems/` | Operational reliability, consistency, and AI methodology |
| `agents/` | Per-task agent tuning and a reusable skill library |
| `knowledge/commands/` | Tool fluency and fast recall |
| `knowledge/architecture/` | Architectural judgment |
| `knowledge/snippets/` | Execution speed on familiar problems |
| `records/debugging/` | Pattern recognition and debugging speed |
| `records/decisions/` | Decision quality and institutional memory |
| `records/postmortems/` | Incident pattern recognition and production confidence |
| `records/evaluations/` | Disciplined experimentation before changing the stack |

The compounding effect is real but takes time. After three months the system starts paying back. After six months it is indispensable. After a year it is the clearest record of how you think and how you build.

---

## Migration from a flat structure

If you are starting from a single large reference document, migrate in this sequence without trying to do everything at once:

**Week 1** — Create the four folders. Move existing files without changing content. Add `records/debugging/template.md`, `records/decisions/template.md`, `records/postmortems/template.md`, `records/evaluations/template.md`. Add `scratch/` with a `.gitignore`.

**Week 2** — Split the large reference file into domain files under `knowledge/commands/` and `knowledge/setup/`. Keep the original as a redirect for one week, then delete it.

**Week 3** — Extract AI prompts from system documents into `systems/` and per-task agents into `agents/`. Update references in the system docs to point to the new location.

**Ongoing** — Write a debug note after every hard bug. Write an ADR after every significant decision. Write a postmortem after every incident. Run the Friday review.

The migration is complete when you never need to search — only navigate.

---

## Core principles

These apply across every document in the system:

1. **Retrieval over storage** — a note you cannot find in under ten seconds does not exist.
2. **Capture now, organize Friday** — friction at capture time kills the system.
3. **Date records, update knowledge** — the distinction prevents stale data from hiding behind fresh files.
4. **One canonical location** — duplication is how systems become untrustworthy.
5. **The system serves real work** — if a layer adds no value to actual engineering, remove it.

---

*This document describes the Engineering Operating System for AiNative. It should be treated as a living document: updated when the structure evolves, referenced when onboarding new contributors, and consulted when the purpose of any layer is unclear.*
