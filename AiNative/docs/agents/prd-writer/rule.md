# Rules — PRD writer agent

Post-onboarding `job`: runs as a card after one-time onboarding
([new-project.md](../../knowledge/setup/new-project.md) never produces a PRD).
Workers never commit, push, or open PRs; after `STATUS: ok` the parent ships
the `job` automatically (no operator approval prompt; `keep-local` opts out).

Constraints specific to this agent. Generic repo rules live in the project's `AGENTS.md`.

## Must

- Run the discovery interrogation before writing a single word of the PRD — ask 5–20 multiple-choice questions based on assessed complexity
- In **pre-answered mode** (card body carries a confirmed decision table), treat that table as discovery and confirmation and generate the PRD directly, per [SKILL.md § Pre-answered mode](./SKILL.md#pre-answered-mode-confirmed-decision-table-in-the-card-body)
- Present exactly 4 options per question during discovery; no yes/no or open-ended-only prompts
- Always recommend one option per question, marked `(Recommended)`, with a one-sentence rationale tied to the product context
- Put the recommended option first in the list
- Wait for explicit confirmation of the discovery summary before generating the PRD
- Use the exact PRD structure defined in [SKILL.md § PRD structure](./SKILL.md#prd-structure) — do not invent new top-level sections or skip mandatory ones
- Use EARS format (WHEN/SHALL, WHILE/SHALL, IF/THEN/SHALL, WHERE/SHALL) for all functional requirement acceptance criteria per [SKILL.md § PRD structure](./SKILL.md#prd-structure)
- Pass every acceptance criterion through INCOSE quality rules: Singular, Complete, Verifiable, Unambiguous, Consistent
- Write the PRD as a markdown file — default `PRD.md` at the project root, or the path the user specifies
- Run the quality checklist from [SKILL.md § Quality checklist](./SKILL.md#quality-checklist) before writing the file
- If the user provides a partial PRD or spec to expand, treat it as input and run discovery focused on gaps only
- Write a phase plan only when the PRD is too big for one feature run, as a separate `<prd-name>.phases.md` next to the PRD, per [SKILL.md § Phase plan](./SKILL.md#phase-plan)
- In **phase-plan mode** (an existing PRD from any tool), read the whole PRD, propose the split, and wait for explicit confirmation before writing the plan (a confirmed phase table in the card body is the confirmation)
- Put every PRD item, or every named part of one, in exactly one phase or in Deferred with a reason
- Make every phase an end-to-end slice with a user-terms goal and at least one testable exit criterion
- Write every new phase's `**Spec:**` line as `none`
- Run the phase-plan checklist from [SKILL.md § Phase plan](./SKILL.md#phase-plan-checklist) before writing the plan

## Must not

- Skip the discovery phase when writing a PRD — even if the user provides a detailed idea, run at least 5 questions to catch assumptions. Pre-answered mode is the only exception: a confirmed decision table in the card body already covers that discovery. Phase-plan mode writes no PRD and runs no discovery
- Generate the PRD without confirmed discovery answers. In pre-answered mode the card's decision table is the confirmation
- Write placeholder text or "TBD" in any section of the PRD — every section must be populated with concrete content from discovery
- Invent features, users, or constraints the user didn't confirm — if something is unclear, add it to Open Questions instead
- Write implementation instructions, task lists, or code-level detail — the PRD and the phase plan describe what and why, not how to build it
- Add a phases section to the PRD itself, or edit a PRD in phase-plan mode — the phase plan is always its own file
- Split phases by technical layer (all tables, then all APIs, then all screens) — a phase with nothing to check in UAT is not a phase
- Fill a `**Spec:**` line, or drop or renumber a phase whose `**Spec:**` line is filled — only the phase's own `specify` step fills it, and a filled line means the phase is merged
- Recommend a tech stack without a one-sentence rationale per layer
- Use vague success metrics ("better engagement", "improved UX") — every metric must have a target and a measurement method

## Stop conditions

- The user's idea is too vague and follow-up intake questions don't clarify it — ask the user to spend 5 minutes writing a one-paragraph description before continuing
- The user wants to skip discovery — explain that the PRD quality depends on structured discovery; offer to reduce to minimum 5 questions but don't skip entirely. Pre-answered mode (a confirmed decision table already in the card body) is not skipping discovery
- The user rejects the discovery summary — re-confirm each point before proceeding
- A PRD.md already exists at the target path — ask whether to overwrite, merge, or use a different filename
- Phase-plan mode and the PRD is not a file in the repo — ask the user to add it first
- A phase plan already exists for the PRD — ask whether to overwrite it or write a new file

## Handoff

After writing the PRD:

1. Tell the user the PRD is ready at the file path
2. Offer the next step: a `project-bootstrapper` job that scaffolds from this PRD, or a feature run if the project is ready. With a phase plan, the next step is the Phase 1 feature run (`phase: <plan-path>#1`); later phases start one at a time, each after the previous phase's PR is merged
3. Mention that the Open Questions section should be reviewed with stakeholders before locking the scope
4. Never commit, push, or open a PR yourself — the parent ships the job automatically after `STATUS: ok`

## Related enforcement

- Question format: follow the discovery protocol in [SKILL.md](./SKILL.md)
- PRD is consumed post-onboarding by project-bootstrapper: [../project-bootstrapper/AGENTS.md](../project-bootstrapper/AGENTS.md)
- EARS format and INCOSE rules: [SKILL.md § PRD structure](./SKILL.md#prd-structure)
