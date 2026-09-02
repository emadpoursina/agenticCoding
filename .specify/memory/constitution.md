<!--
Sync Impact Report
- Version change: (none) → 1.0.0 (initial ratification; prior file was an unfilled template)
- Modified principles: (none — first fill of template placeholders)
  - [PRINCIPLE_1_NAME] → I. Spec-First
  - [PRINCIPLE_2_NAME] → II. Least Code (Ponytail)
  - [PRINCIPLE_3_NAME] → III. Platform-Native Over Rebuild
  - [PRINCIPLE_4_NAME] → IV. Trust-Boundary Tests
  - [PRINCIPLE_5_NAME] → V. Human Authority
- Added sections: Hard Constraints; Development Workflow
- Removed sections: none
- Follow-up TODOs: none
-->

# Agentic Coding Constitution

## Core Principles

### I. Spec-First

Feature work MUST start from a written spec before implementation.
Multi-file or architectural changes MUST follow Spec Kit order:
constitution → specify → (clarify as needed) → plan → tasks → implement.
Agents MUST NOT write application source from a vague prompt when a spec
or plan is required. The constitution is the evaluation bar for later
phases: a spec, plan, or task that contradicts these principles is invalid.

Rationale: Cheap to correct a spec; expensive to unwind code that was
never agreed.

### II. Least Code (Ponytail)

The best code is the code never written. Before adding code, agents MUST
climb this ladder and stop at the first rung that holds:

1. Does this need to be built at all? (YAGNI)
2. Does it already exist in this codebase? Reuse it.
3. Does the standard library already do this? Use it.
4. Does a native platform feature cover it? Use it.
5. Does an already-installed dependency solve it? Use it.
6. Can this be one line? Make it one line.
7. Only then: write the minimum code that works.

The ladder runs AFTER tracing the real flow end to end. Agents MUST NOT
add abstractions, dependencies, or boilerplate that were not requested.
Deletion over addition. Shortest working diff wins only when the change
is in the right place. Bug fixes MUST target the shared root cause, not
the symptom path named in a ticket.

Deliberate simplifications that cut a real corner MUST be marked with a
`ponytail:` comment naming the ceiling and the upgrade path.

### III. Platform-Native Over Rebuild

Agents MUST prefer capabilities already in the host platform over building
equivalents. For Hermes Kanban work this means: native Kanban
(`kanban.db`), project registry (`projects.db`), worktrees, retries,
heartbeats, Telegram gateway, and GitHub skills. A second task database
MUST NOT be introduced. AiNative is a read-only methodology mount;
workers MUST NOT modify it. Lessons become proposals, not automatic PRs.
Do not fork or rewrite Hermes. Do not duplicate AiNative into application
repos.

Rationale: V0 is adapters plus orchestration, not a new control plane.

### IV. Trust-Boundary Tests

External input (task payloads, manifests, GitHub/Telegram events, env)
MUST be validated at the trust boundary. Non-trivial logic MUST leave
ONE runnable check behind — the smallest thing that fails if the logic
breaks (assert-based demo or one small test file; no extra frameworks).
Trivial one-liners need no test. Python public APIs MUST be type-annotated.
The default check tools for Python packages in this workspace are pytest
and ruff. Integration-style checks are REQUIRED when a change touches
library contracts, inter-service communication, or shared schemas.

Agents MUST NOT be lazy about: understanding the problem, input
validation, error handling that prevents data loss, security,
accessibility, or hardware/runtime calibration.

### V. Human Authority

AI is a partner, not the authority. Humans own merge, release, and
production deploy. Agents MUST NOT push protected or main branches,
merge pull requests, deploy to production, commit secrets, copy SSH
private keys into images, or expose credentials in output. For ambiguous
tasks that change architecture, security, merge/deploy authority, or
AiNative methodology: ask, do not guess. Implementation details (file
layout, naming, tests, adapter internals) MAY be chosen and documented
without asking.

V0 target projects MUST be disposable fixtures until the owner names a
non-critical repo. Do not silently pick a real production repository.

## Hard Constraints

- Python packages in this workspace use Python 3.12 (`>=3.12,<3.14`) via uv.
- No new external dependencies without explicit owner approval.
- Never commit secrets, tokens, or credentials. Operational keys live
  outside git (e.g. `$HOME/.hermes/personal-agent/.env`).
- Isolated Hermes home: `~/.hermes/personal-agent`. Do not write to
  `~/.hermes` root.
- Model routing is configured inside Hermes. Do not hardcode provider
  or model names into agents.
- Out of scope until explicitly reversed: Obsidian, automatic merge,
  production deploy, concurrent workers, autonomous AiNative modification,
  installing specs.md, emitting editor-specific agent config into app
  repos, extra databases/queues/dashboards Hermes does not require.
- Surgical edits only: never rewrite an entire file to change one function.
- Terminal commands: no destructive defaults.

## Development Workflow

- Humans developing this workspace follow **PIV**: Plan → Implementation →
  Validation. Multi-file feature work requires a written plan and
  confirmation before implementation.
- Spec Kit is the planning framework for this playground. After
  implementation, Validation uses the AiNative critic then tester agents.
- Hermes *runtime* PIV on managed projects has no plan-approval step —
  only pause for unresolved consequential decisions.
- Commit style: Conventional Commits (`feat:`, `fix:`, `chore:`,
  `refactor:`, `test:`).
- Capture raw notes in `scratch/` during work; promote on Friday review.
  Never commit `scratch/` contents except tracked README files.
- After making changes, update related documentation if it exists.
- One canonical location for each fact. Duplication is how systems rot.
- Finish before you start: fewer parallel items, smaller tasks.

## Governance

This constitution supersedes conflicting informal practice, agent
defaults, and prior chat instructions. Specs, plans, and tasks MUST be
checked against it before implementation.

Amendments:

1. Propose the change in writing (principle add, rewrite, or removal).
2. Classify the version bump: MAJOR for incompatible removals or
   redefinitions; MINOR for new principles or material expansion; PATCH
   for clarifications and wording.
3. Run `/speckit.constitution` (or the Cursor skill `speckit-constitution`)
   so `.specify/memory/constitution.md` is the single updated artifact.
4. Dependent Spec Kit commands read this file at runtime. Do not
   propagate constitution text into templates.

Compliance: every PR and agent review MUST verify the change does not
violate Core Principles or Hard Constraints. Unjustified complexity
MUST be rejected or recorded as a dated ADR under AiNative decisions.
Runtime development guidance for Hermes Kanban lives in
`personalAgent/AGENTS.md`; this constitution wins on conflict.

**Version**: 1.0.0 | **Ratified**: 2026-08-28 | **Last Amended**: 2026-08-28
