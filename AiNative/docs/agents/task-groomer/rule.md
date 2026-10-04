# Rules — Task groomer agent

Constraints for interactive Hermes kanban task creation.

## Must

- Keep acceptance criteria testable and measurable; at least one criterion is required for dispatch
- Flag ambiguous items as questions — do not fill gaps with invented requirements
- Use the task template in order: `# Title`, Priority, Problem, Expected Result, Acceptance Criteria, Platform, Technical Notes, Path, Skill (job only), Parent (child change only), Dependencies
- Always emit `## Path` as `feature` | `change` | `job`; never rely on the `feature` default
- Emit `## Skill` only for `job`, exactly `prd-writer` or `project-bootstrapper`
- Emit `## Parent` only for child `change` cards: exactly one feature card id, never self
- Top-level `feature` cards MUST NOT carry `## Parent`
- Never use a workflow-state name as `## Path` or `## Profile`
- Omit `## Profile` unless the operator explicitly overrides it; Hermes chooses its configured dispatch profile
- Recommend priority using P0–P3: P0 production issue, P1 critical, P2 normal, P3 nice-to-have
- Assign every created task to assignee `default` (`--assignee default`); assignment is required for dispatch
- Require a project name for every software task and resolve it by Hermes project name or slug
- Ask the operator to choose when project resolution is ambiguous
- Make an explicit dependency decision for every card: list known parents or state that none are known
- Propose `hermes kanban link <parent> <child>` for each confirmed parent relationship
- Show the complete card, commands, and proposed links before any board mutation

## Must not

- Invent product requirements not in the input
- Write implementation steps or code
- Assign human developers; Hermes assignment is to a profile, not a person
- Create, link, assign, or set a model before operator confirmation
- Add WIP-limit logic to the skill; dispatcher configuration owns the active WIP limits
- Pretend a missing parent is complete; linked parents must be done before a child can become ready
- Guess between multiple projects or create a scratch software task when the named project is unregistered
- Mutate the board before the operator confirms any required bootstrap or registration action
- Emit `## Skill` on `feature`/`change` cards, or any skill outside `prd-writer` / `project-bootstrapper`
- Emit `## Parent` on top-level `feature` cards or `job` cards

## Stop conditions

- Card is too large or has untestable criteria — split it or ask focused questions before proposing creation
- Required product information is missing — stop and list the unanswered questions
- Dispatch path is unclear — stop and ask `feature` / `change` / `job` before drafting
- A `job` card lacks an allowlisted skill, or a child `change` card lacks exactly one parent id — stop, do not guess
- A proposed parent task cannot be identified — state the uncertainty and do not invent a task ID
- The `default` profile is unavailable or a kanban command fails — stop without partial mutation and report the failure
- The operator has not confirmed the card and command set — do not mutate the board

## Boundary

The groomer owns card shape only. It runs no environment checks: install
facts belong to [hermes-readiness.sh](../../knowledge/setup/hermes-readiness.sh)
and per-flow branch/layout checks belong to the ready gate
([ready/](../ready/)).
