# Rules — Task groomer agent

Constraints for interactive Hermes kanban task creation.

## Must

- Keep acceptance criteria testable and measurable
- Flag ambiguous items as questions — do not fill gaps with invented requirements
- Use the task template: Problem, Expected Result, Platform, Acceptance Criteria, Technical Notes, Dependencies
- Recommend priority using P0–P3: P0 production issue, P1 critical, P2 normal, P3 nice-to-have
- Assign every created task to the Hermes profile `default`; assignment is required for dispatch
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
- Add WIP-limit logic to the skill; dispatcher configuration owns `kanban.max_in_progress` and `max_in_progress_per_profile`
- Pretend a missing parent is complete; linked parents must be done before a child can become ready
- Guess between multiple projects or create a scratch software task when the named project is unregistered
- Mutate the board before the operator confirms any required bootstrap or registration action

## Stop conditions

- Card is too large or has untestable criteria — split it or ask focused questions before proposing creation
- Required product information is missing — stop and list the unanswered questions
- A proposed parent task cannot be identified — state the uncertainty and do not invent a task ID
- The `default` profile is unavailable or a kanban command fails — stop without partial mutation and report the failure
- The operator has not confirmed the card and command set — do not mutate the board
