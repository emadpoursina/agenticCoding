# Feature Specification: Unified feature loop (Hermes stages + Pi per step)

**Feature Branch**: `018-unified-feature-loop`

**Created**: 2026-09-21

**Status**: Draft

**Input**: Operator locked a single live loop. **This spec’s
implementation slice is Hermes only** (`personalAgent`): state machine,
one new Pi session per agent state, retire the one-shot
`speckit-orchestrate` playbook, wrap Spec Kit with Ready / critic /
tester / UAT / pr-review / GitHub. Cursor `/speckit-orchestrate` already
parents the same pattern in the IDE — **do not edit it in this pass**.
Methodology stays in AiNative `feature-loop.md`; do not fork it into
Hermes.

**Canonical methodology** (do not fork this text into Hermes):

- `AiNative/docs/systems/feature-loop.md`
- `AiNative/docs/records/decisions/2026-09-feature-loop.md`

This spec is the **apply work order** for code and remaining docs.

## Clarifications

### Session 2026-09-21

- Q: Who owns the loop definition vs execution? → A: AiNative owns what
  the loop is. Hermes owns current state, checks, human park, and starting
  Pi. Pi owns only the named step.
- Q: Does Pi run the whole Spec Kit playbook? → A: No. One new Pi session
  per agent state (Ready, specify, clarify, plan, tasks, analyze,
  implement, converge, critic, tester, pr-review).
- Q: Canonical V0 stages? → A: Ready → Spec Kit (specify → clarify →
  confirm → plan → tasks → optional analyze → implement ↔ converge) →
  critic → tester → UAT (human) → pr-review → publish.
- Q: Does Hermes execute skills itself? → A: Never. Always Pi for agent
  states. Confirm, UAT, and publish are not Pi.
- Q: Publish vs pr-review? → A: **Default:** pr-review the feature
  **branch**, then Hermes opens/updates the PR.
- Q: This apply pass includes Cursor `/speckit-orchestrate`? → A: **No.**
  Cursor already works as a parent. Change Hermes only.
- Q: How does Ready resolve its skill (FR-011)? → A: **Promote AiNative
  `docs/agents/ready/` in this change.** Do not keep the global
  `speckit-ready` skill as a Hermes map-only option. One Ready definition,
  living in AiNative.
- Q: What happens when UAT finds a problem? → A: **Not decided as a full
  failure-state machine yet.** For now UAT is simple QA for a human:
  Hermes presents a feature-derived QA checklist to the operator, the
  operator verifies the agent work, and the loop does not auto-loop on
  UAT feedback.
- Q: What happens after pr-review (FAIL or otherwise)? → A: **The human
  decides.** After pr-review completes, Hermes parks for operator
  decision; Hermes does not auto-loop back into implement or
  re-validation after pr-review.
- Q: Where do `validation_commands` execute (FR-008)? → A: **The Pi tester
  runs them.** Hermes passes the declared command list to the tester as
  inputs; Hermes does not run them in-process as a substitute.

## User Scenarios & Testing *(mandatory)*

`013` made Pi own the entire Spec Kit playbook so Hermes would not grow a
stage machine. That forked Cursor (per-stage workers) from Hermes
(one-shot playbook) and from AiNative (homemade PIV). This feature
**restores Hermes-owned stages** with Pi as the per-stage harness — the
same parent/worker split as `/speckit-orchestrate`.

### User Story 1 - Hermes dispatches one Pi session per state (Priority: P1)

An eligible Kanban task starts. Hermes prepares the isolated worktree,
sets state `ready`, and starts Pi with only the Ready skill. Pi returns
`READY: ok` (or blocked). Hermes advances to `specify` and starts a
**new** Pi session, and so on through the graph in
`feature-loop.md`.

**Why this priority**: This is the runtime contract. Without it, docs and
code stay forked.

**Independent Test**: Fixture Pi that records each start (step name +
session). Drive one fake successful run. Assert N starts, N new sessions,
order matches the graph, and no start whose prompt includes a later step
name as an instruction to run it.

**Acceptance Scenarios**:

1. **Given** an eligible task, **When** the live dispatcher starts it,
   **Then** Hermes does not start playbook id `speckit-orchestrate` as
   “run the whole flow.”
2. **Given** Ready succeeds, **When** specify starts, **Then** it is a
   new Pi process/session, not a continuation of the Ready process.
3. **Given** a Pi prompt for specify, **When** inspected, **Then** it
   names specify only and does not instruct Pi to run clarify or plan.
4. **Given** implement then converge, **When** converge returns
   `tasks_appended` with new work, **Then** Hermes starts a new implement
   Pi session; it does not tell the converge session to implement.

---

### User Story 2 - Human gates stay in Hermes (Priority: P1)

Clarify questions, the one continuation `confirm`, and `uat` park as
`needs_human`. Hermes relays questions one at a time (existing Telegram /
resume path). After answers, Hermes starts the **next** Pi session. Pi
never owns skip/confirm/UAT policy.

**Why this priority**: This is how context stays small and the graph
stays in Hermes.

**Independent Test**: Fixture clarify returns a question queue. Assert
park, recorded answers, then a new Pi start for encode-answers or plan
after confirm — never Pi chatting with the operator.

**Acceptance Scenarios**:

1. **Given** clarify `STATUS: blocked` with questions, **When** Hermes
   handles it, **Then** state is human, 0 further Spec Kit stages start
   until resume.
2. **Given** `skip`, **When** specify/clarify run, **Then** workers
   self-answer, Hermes shows the choice report, and `confirm` still runs
   before plan.
3. **Given** tester pass, **When** UAT starts, **Then** no Pi session is
   started for UAT; Hermes presents a feature-derived QA checklist and
   the operator must confirm pass before pr-review.
4. **Given** the UAT checklist, **When** the operator works through it,
   **Then** it is plain human QA over the implemented feature (no
   auto-loop, no UAT failure-state machine in V0).

---

### User Story 3 - Validation is critic then tester then UAT (Priority: P1)

After `CONVERGE_OUTCOME: converged`, Hermes starts Pi(critic), then
Pi(tester). Tester runs (or includes) the project’s declared
`validation_commands`. There is no separate Hermes “shell validation
phase” that skips those agents. After tester pass, UAT, then
Pi(pr-reviewer), then Hermes publish.

**Why this priority**: This was the missing wrap around Spec Kit.

**Independent Test**: Fixture converge `converged`. Assert next starts
are critic, tester, (no Pi), pr-review, then GitHub path. Assert
`validation_commands` are not run as a substitute for critic.

**Acceptance Scenarios**:

1. **Given** converge succeeded, **When** the graph continues, **Then**
   critic runs before tester, and tester before UAT.
2. **Given** critic FAIL, **When** classified retryable, **Then** recovery
   follows existing bounded retries without skipping to publish.
3. **Given** pr-review PASS, **When** publish runs, **Then** commit/push/PR
   happen only on the feature branch; Pi is not started for publish.
4. **Given** pr-review completes (PASS or FAIL), **When** the graph
   continues, **Then** Hermes parks for operator decision; Hermes does
   not auto-loop into implement or re-validation after pr-review.

---

### User Story 4 - Hermes docs match the loop (Priority: P1)

AiNative `feature-loop.md` is the SoT. `personalAgent/AGENTS.md` and
README describe dispatcher behavior and **link** to that file; they do
not paste the full loop. They must not say live execution is one Pi
playbook or forbid Hermes-owned stages. Live AiNative PIV
(`piv-gate.mdc`, `agentic-coding.md`) must not be treated as what Hermes
runs. Cursor `/speckit-orchestrate` is **out of scope** for this story.

**Why this priority**: The original bug was three written loops.

**Independent Test**: Grep live path docs for “one Pi playbook” /
“scout → plan → tasks → implement as Hermes stages forbidden” / “PIV
before multi-file” as the live contract. Those claims must be gone or
marked historical.

**Acceptance Scenarios**:

1. **Given** `personalAgent/AGENTS.md`, **When** read, **Then** it says
   one Pi session per agent state and forbids Hermes from running skills.
2. **Given** `013` / `011` live-path sentences, **When** an implementer
   follows them, **Then** they are marked superseded by this spec.
3. **Given** `docs/systems/agentic-coding.md`, **When** opened, **Then**
   the top points to `feature-loop.md` as the live workflow.

---

### Edge Cases

- Mid-playbook overlay records from `013` stay parked until a human
  acknowledges; do not auto-migrate them onto the new graph.
- Stable `READY: blocked` is not retried.
- Repeated converge fingerprint is stuck (same as orchestrate).
- Missing Spec Kit layout in the worktree: Ready fails; Hermes does not
  bootstrap Spec Kit into AiNative.
- `analyze` skipped when `ANALYZE: no`.
- Operator `skip` does not skip plan, tasks, implement, converge, critic,
  tester, UAT, or pr-review.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: Live execution MUST be a Hermes-owned state machine whose
  agent states are exactly those in `feature-loop.md`.
- **FR-002**: Each agent state MUST start a new Pi session (or equivalent
  isolated harness job) with only that state’s skill.
- **FR-003**: Hermes MUST NOT run Spec Kit or AiNative skills in-process.
- **FR-004**: Pi prompts MUST NOT include instructions to run a later
  graph state.
- **FR-005**: Playbook-as-whole-flow (`speckit-orchestrate` as one Pi
  job that specify…converge) MUST be removed from every live command,
  fallback, and recovery path (same removal posture as `013` used against
  the old short path).
- **FR-006**: `confirm`, `uat`, and `publish` MUST NOT start Pi.
- **FR-007**: After converge, Hermes MUST run critic then tester (Pi),
  then UAT (human), then pr-review (Pi), then publish (Hermes).
- **FR-008**: Project `validation_commands` MUST run as part of tester,
  not as a replacement for critic/tester. The **Pi tester runs** the
  commands; Hermes passes the declared command list to the tester as
  inputs and MUST NOT execute them in-process as a substitute for
  critic/tester.
- **FR-009**: Publish MUST occur only after pr-review PASS, on the
  feature branch, never `main`/`master`, never merge unless the operator
  clearly asked.
- **FR-010**: Methodology text MUST live in AiNative. Hermes MUST link,
  not duplicate, `feature-loop.md`.
- **FR-011**: Ready MUST resolve to the **AiNative `docs/agents/ready/`
  agent promoted in this same change**. Do not keep the global
  `speckit-ready` skill as a Hermes map-only Ready option, and do not
  leave Ready as an undocumented path.
- **FR-012**: In-flight `013` playbook runs MUST stay parked for a human;
  do not finish them on the old machine.
- **FR-013**: This implementation slice MUST NOT edit Cursor
  `/speckit-orchestrate` or `/pi-harness`.
- **FR-014**: The retired Hermes playbook name `speckit-orchestrate`
  (whole Spec Kit in one Pi) MUST be removed from the live path. Do not
  treat the Cursor command of the same name as that playbook.
- **FR-015**: UAT MUST be simple human QA in V0: Hermes MUST present a
  feature-derived QA checklist to the operator so the human can verify
  the agent work. Hermes MUST NOT auto-loop on UAT feedback and MUST NOT
  implement a UAT failure-state machine yet.
- **FR-016**: After pr-review completes, Hermes MUST park for operator
  decision. Hermes MUST NOT auto-loop into implement or re-validation
  after pr-review; the human decides what happens next.

### Key Entities

- **State**: one node on the feature-loop graph.
- **Agent state**: a state executed by Pi.
- **Human state**: confirm or UAT.
- **Compact report**: parseable Pi result for that state.
- **Session**: one Pi process lifetime; one agent state.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: A fixture full run records a new Pi start for every agent
  state and zero Pi starts for confirm, UAT, and publish.
- **SC-002**: 100% of live dispatcher entries refuse a whole-playbook
  Spec Kit job.
- **SC-003**: An operator can open `feature-loop.md` and
  `personalAgent/AGENTS.md` and not find a contradictory live loop.
- **SC-004**: Existing hermetic tests still pass; new tests cover
  per-state starts, human park, and critic-before-publish.

## Assumptions

- Isolated worktrees, Kanban, GitHub, Telegram, recovery budget, and
  read-only AiNative mount stay as they are.
- Spec Kit skills remain in the enrolled project / worktree.
- Models per Hermes step may follow the same Ready/specify/… mapping as
  today; do not pull Cursor Task slugs into the container.
- Scout and plan-reviewer stay **out of V0**.
- Cursor `/speckit-orchestrate` is **out of this implementation slice**.
- This spec supersedes live-path claims in `011`, `012`, `013`, and
  `014` that say Pi owns the whole Spec Kit playbook or that scout must
  run before Spec Kit.

## Apply checklist (for the implementing agent)

Do this in order. Do not implement a second methodology file in Hermes.

### 1. AiNative (methodology)

Already added (keep, do not rewrite from scratch):

- `docs/systems/feature-loop.md`
- `docs/records/decisions/2026-09-feature-loop.md`

Still do:

- Point `docs/systems/agentic-coding.md`, `docs/systems/README.md`,
  `docs/README.md`, `ENGINEERING-OS.md`, `.cursor/rules/piv-gate.mdc`,
  `.cursor/rules/ai-rules.mdc`, `docs/systems/cursor-rules.md`,
  `docs/systems/ai-rules-template.md` at the feature loop as **live**.
  Mark old PIV as historical / optional for tiny Cursor-only work, not
  what Hermes runs.
- `docs/agents/README.md`: Ready (the promoted `docs/agents/ready/`
  agent per FR-011), critic, tester, pr-reviewer as **live loop
  agents**. Scout/plan-reviewer optional, not on the live graph.
- **Decided (FR-011)**: add `docs/agents/ready/` (modeled on
  `~/.cursor/skills/speckit-ready`) as the promoted AiNative Ready
  agent in this change. Do NOT keep the global `speckit-ready` skill as
  a Hermes map-only option; document the single Ready agent in
  `feature-loop.md`. One Ready definition, not two.

### 2. personalAgent (this slice — required)

- Rewrite live execution in `AGENTS.md`, `README.md`,
  `docs/context/SYSTEM.md` (reference copy): **one Pi session per agent
  state**; link `/ainative/docs/systems/feature-loop.md`; delete “do not
  restore Hermes-owned stages” and “one speckit-orchestrate playbook.”
- Replace harness start: request a **step id**, not playbook-as-flow.
  Keep worktree, timeout, safety limits, overlay record.
- Implement the state machine + compact-report parsing (stuck policy
  from `feature-loop.md`).
- Wire critic / tester / pr-reviewer via the existing AiNative adapter
  (`docs/agents/<name>/`).
- Move `_run_validation` shell into tester’s state (or tester invokes
  it). Do not publish on “project checks passed” without critic + tester
  + UAT + pr-review.
- Park legacy whole-playbook overlays (`FR-012`).
- Tests: per-state session starts; no later-step leakage in prompts;
  human confirm/UAT; converge loop; no publish before pr-review.

### 3. Cursor (not this slice)

- Leave `/speckit-orchestrate` and `/pi-harness` unchanged.

### 4. This repo’s older specs

- Banner on `011`, `012`, `013`, `014` live-path sections:
  superseded by `018` for execution shape. Do not rewrite all historical
  scenarios.

### Out of scope

- Obsidian, auto-merge, production deploy, concurrent workers.
- Autonomous AiNative modification at runtime.
- Rebuilding Telegram or a second task database.
- Implementing scout/plan-reviewer on the live graph.
- Editing Cursor `/speckit-orchestrate` or `/pi-harness`.
