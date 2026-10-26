# Feature Specification: Agentic validation loop

**Feature Branch**: `agentic-validation`

**Created**: 2026-10-26

**Status**: Draft

**Input**: User description: "skip" (operator skip flag). Full intent: make feature-loop Validation agentic — after Ship opens a PR, automatically run pr-reviewer and route the verdict; wire critic and tester into the speckit-orchestrate feature path; loop Implement-target failures through converge (not a new fix loop).

## Clarifications

### Session 2026-10-26

- Q: After a small already-specified change, should critic run before tests, or should that path stay tester-only? → A: Tester-only (no critic on the change path)
- Q: After REQUEST CHANGES is fixed and validation passes, how should the parent update the existing pull request? → A: Re-run parent ship with same-PR reuse (commit, push, refresh walkthrough; do not open a second PR)
- Q: If PR review says REQUEST CHANGES but lists no Critical findings, should the loop start a fix cycle? → A: No; route as APPROVE for loop purposes
- Q: If one FAIL report mixes implement-target and plan-target findings, what should the parent do? → A: Park (any plan-target finding wins)
- Q: After PR review APPROVE, is UAT still an operator pass/fail gate, or only a finish-report park? → A: Existing operator UAT pass/fail confirmation

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Feature path runs Validation then automatic PR review (Priority: P1)

An operator starts a feature run. After implement and converge report `converged`, the parent automatically runs critic, then tester, then ships, then PR review, then parks for human UAT. The operator does not have to remember to invoke critic, tester, or pr-reviewer.

**Why this priority**: This is the done-when graph. Without it, Validation stays optional and PR review stays on-demand-only.

**Independent Test**: Read the documented feature graph and a tabletop dispatch of a happy path: after `CONVERGE_OUTCOME: converged`, the next stages are critic → tester → ship → pr-review → uat, with no operator prompt between them except the existing UAT pass/fail confirmation.

**Acceptance Scenarios**:

1. **Given** a feature run whose implement↔converge loop has just reported `converged`, **When** the parent continues, **Then** it launches critic, then tester (only after critic PASS), then ship (only after tester PASS), then pr-review (only after `SHIP: ok`), then parks for UAT.
2. **Given** the live feature-loop graph, **When** an operator reads it, **Then** it shows `converge(converged) → critic → tester → ship → pr-review → uat` and no longer describes pr-reviewer as on-demand-only after Ship.
3. **Given** workers for critic, tester, and pr-reviewer, **When** they run, **Then** each stays stage-dumb (reports a compact verdict; does not dispatch the next stage, write `tasks.md`, ship, or implement).

---

### User Story 2 - PR review verdicts route without a new fix loop (Priority: P1)

After Ship opens a PR, pr-reviewer runs automatically. APPROVE continues to the existing UAT pass/fail confirmation. REQUEST CHANGES with Criticals sends those Criticals into the existing implement↔converge loop, then re-validates and parent-ships the same PR for re-review. BLOCKED from Phase 1.5 parks for the operator.

**Why this priority**: Automatic review is useless unless the parent knows where each verdict goes. Reusing converge avoids a second repair path.

**Independent Test**: Tabletop three verdicts after `SHIP: ok`. Confirm REQUEST CHANGES never invents a new loop and never feeds Criticals straight to implement without converge.

**Acceptance Scenarios**:

1. **Given** `SHIP: ok` on the feature path (and the run is not `keep-local`), **When** ship finishes, **Then** the parent launches pr-reviewer automatically.
2. **Given** pr-reviewer reports APPROVE, **When** the parent routes, **Then** the run parks for the existing operator UAT pass/fail confirmation on the open PR. Merge stays human and outside the loop. APPROVE does not complete the run by itself.
3. **Given** pr-reviewer reports REQUEST CHANGES **with at least one Critical**, **When** the parent routes, **Then** it starts converge with those Criticals as the converge worker's `$ARGUMENTS`, then implement ↔ converge, then critic → tester, then **parent ship with same-PR reuse** (commit, push, refresh walkthrough; do not open a second PR), then re-review (passing the previous pr-reviewer report as extra context).
4. **Given** pr-reviewer reports REQUEST CHANGES **with zero Criticals** (Warnings/Suggestions only), **When** the parent routes, **Then** it treats the verdict as APPROVE for loop purposes and parks for UAT. It does not start converge or a change retry.
5. **Given** pr-reviewer reports BLOCKED (Phase 1.5), **When** the parent routes, **Then** the run parks for the operator. It does not auto-retry.
6. **Given** REQUEST CHANGES findings, **When** converge writes work items, **Then** converge source-refs stay spec/plan/constitution (`FR-###`, `US1/AC2`, `plan: …`, `Constitution …`). Validator IDs appear only in the task description, for example `[pr-review: C1]`. The system does not invent PR-review source-refs.
7. **Given** a re-review after a same-PR ship, **When** pr-reviewer runs, **Then** it uses the existing previous-report extra-context path. Merge gate remains Critical-only (Warning/Suggestion never change the verdict).

---

### User Story 3 - Critic and tester compact reports name a loop-back target (Priority: P1)

Critic and tester still report PASS/FAIL. They also report `LOOP_BACK: implement | plan | none`. The parent uses that field: Implement-target FAIL goes through converge; Plan-target FAIL parks.

**Why this priority**: Without a parseable target, the parent cannot loop failures through converge instead of a new fix loop.

**Independent Test**: Inspect critic and tester compact-report contracts: PASS/FAIL remain; `LOOP_BACK` is present; parent routing matches the table below.

**Acceptance Scenarios**:

1. **Given** critic or tester FAIL with `LOOP_BACK: implement`, **When** the parent routes, **Then** it sends the findings to converge (append-only `tasks.md`), then implement ↔ converge, then re-runs critic → tester. It does not launch implement directly with the findings, and it does not create a separate fix loop.
2. **Given** critic or tester FAIL with `LOOP_BACK: plan`, **When** the parent routes, **Then** the run parks for the operator. It does not re-run critic, tester, or pr-review until a human unparks.
3. **Given** one FAIL report that mixes implement-target and plan-target findings, **When** the parent routes, **Then** it parks (any plan-target finding wins). It does not start converge while a plan-target finding is open.
4. **Given** critic or tester PASS, **When** the compact report is emitted, **Then** `LOOP_BACK: none` (or equivalent none) and existing PASS/FAIL fields remain.
5. **Given** a validator FAIL, **When** converge returns `converged` while that FAIL is still open, **When** the parent sees that combination, **Then** it parks. It does not re-run critic, tester, or pr-review.
6. **Given** validators, **When** they finish, **Then** they never write `tasks.md`. Only converge appends tasks.

---

### User Story 4 - Change path retries without converge; job path skips PR review (Priority: P1)

A change-path run stays tester-only (no critic). Tester FAIL or pr-review REQUEST CHANGES with Criticals retries through the change worker plus FINDINGS. It does not use `tasks.md` or converge. A job-path run never runs pr-review.

**Why this priority**: Path isolation is a hard constraint. Mixing converge into change, or PR review into jobs, would break the thin paths.

**Independent Test**: Tabletop a change REQUEST CHANGES and a job `STATUS: ok` after ship; confirm no converge artifacts and no pr-review on job.

**Acceptance Scenarios**:

1. **Given** a change-path run, **When** validation starts, **Then** the parent launches tester only. Critic does not run on the change path.
2. **Given** change-path tester FAIL, **When** the parent retries, **Then** it relaunches the change worker with FINDINGS. No `tasks.md` is written; converge does not run.
3. **Given** change-path `SHIP: ok` (not `keep-local`), **When** pr-reviewer reports REQUEST CHANGES with at least one Critical, **Then** retry is change worker + FINDINGS, then tester, then parent ship with same-PR reuse, then re-review. Still no critic and no converge.
4. **Given** a job-path run that ships a PR, **When** ship completes, **Then** the parent does not launch pr-reviewer. UAT is not a job-path stage.
5. **Given** three failed change retries of the same findings, **When** the stuck limit is hit, **Then** the run parks (same three-attempt stuck policy as other steps).

---

### User Story 5 - Converge treats repeated validator findings as the same stuck point (Priority: P2)

Converge's fingerprint includes validator finding IDs so the same Critical or failed flow counts as the same stuck point. After three attempts, the run parks.

**Why this priority**: Without IDs in the fingerprint, the loop can oscillate forever on the same critic/tester/pr-review finding.

**Independent Test**: Two converge passes with the same `[tester: flow-2]` / `[critic: C1]` / `[pr-review: C1]` IDs produce the same fingerprint component; a third unchanged attempt parks.

**Acceptance Scenarios**:

1. **Given** converge computing a fingerprint, **When** validator findings are in play, **Then** the fingerprint includes those finding IDs (for example tester flow ids, critic C-ids, pr-review C-ids) so a repeated finding is the same stuck point.
2. **Given** the same fingerprint on the original attempt plus two resumes, **When** the third attempt still matches, **Then** the parent parks. It does not continue critic/tester/pr-review.
3. **Given** converge source-refs, **When** tasks are appended, **Then** source-refs remain spec/plan/constitution only; validator IDs stay in the task description text as `[tester: …]` / `[critic: …]` / `[pr-review: …]`.

---

### User Story 6 - Critic and PR review stay distinct gates (Priority: P2)

Operators can tell the two reviews apart: critic checks code against spec/plan **before** tests; pr-reviewer checks architecture, risk, and evidence **after** the PR opens. Critic implementation review is not dropped.

**Why this priority**: Collapsing the two reviews would either skip spec/plan alignment or skip post-PR architecture/risk/evidence.

**Independent Test**: Feature-loop, validation-layer, critic, and pr-reviewer docs state the split; implementation review remains required before tester.

**Acceptance Scenarios**:

1. **Given** implementation is complete and converge has reported `converged`, **When** Validation starts, **Then** critic implementation review runs before tester and still FAILs on spec/plan mismatch.
2. **Given** `SHIP: ok`, **When** pr-reviewer runs, **Then** its job is architecture, risk, and evidence on the opened PR — not a second spec/plan implementation critique that replaces critic.
3. **Given** existing critic implementation-review rules, **When** this feature ships, **Then** those rules remain; the feature does not drop critic implementation review.

---

### User Story 7 - keep-local skips ship and automatic PR review (Priority: P2)

An operator who passed `keep-local` (or `no-ship`) still gets the path's validation stages (feature: critic then tester; change: tester only). After they PASS, the parent leaves work uncommitted, reports `SHIP: declined`, and does **not** run automatic pr-review or UAT.

**Why this priority**: keep-local is the only opt-out of ship; automatic pr-review must not fire without a PR.

**Independent Test**: Tabletop a feature run with `keep-local` after tester PASS: no commit/push/PR, no pr-reviewer launch, finish report includes `SHIP: declined`. Same for change after tester PASS, with no critic.

**Acceptance Scenarios**:

1. **Given** `keep-local` on a **feature** run, **When** critic and tester PASS, **Then** the parent does not ship and does not launch pr-reviewer.
2. **Given** `keep-local` on a **change** run, **When** tester PASS, **Then** the parent does not run critic, does not ship, and does not launch pr-reviewer.
3. **Given** that run, **When** the finish report is written, **Then** it includes `SHIP: declined` and does not park for UAT.

---

### User Story 8 - Operator docs and changelog describe the new Validation graph (Priority: P2)

The operator can follow one graph in the system docs and matching skill/rule text. The methodology changelog records this as 0.4.0.

**Why this priority**: Dispatcher behavior is defined by those documents; drift would split parent vs worker contracts.

**Independent Test**: The listed canonical files describe the graph, routing, compact-report fields, fingerprint, source-ref convention, critic vs pr-review split, keep-local, and change/job exceptions. Changelog has a 0.4.0 entry for this work.

**Acceptance Scenarios**:

1. **Given** an operator opening the feature-loop and validation-layer docs, **When** they look for Validation, **Then** they see critic → tester as required feature-path stages and pr-review as a loop state after Ship (not on-demand-only).
2. **Given** speckit-orchestrate SKILL and rule, critic/tester/pr-reviewer skills and rules, and the change skill, **When** they are compared to the graph, **Then** parent routing, compact-report fields, and worker dumbness match this spec.
3. **Given** the methodology changelog, **When** this feature is delivered, **Then** it is recorded as **0.4.0** following the existing Keep a Changelog + SemVer scheme. No extra git bootstrap, and no second changelog at the playground repo root unless that repo already follows a scheme this work is not changing.

---

### Edge Cases

- **`keep-local` (feature)**: critic and tester still run; ship and automatic pr-review do not.
- **`keep-local` (change)**: tester still runs; critic, ship, and automatic pr-review do not.
- **Ship blocked** (`SHIP: blocked`): do not launch pr-reviewer; report the blocker and stop. This is not an implicit keep-local.
- **Phase 1.5 BLOCKED**: park for the operator; do not count as REQUEST CHANGES and do not start converge.
- **REQUEST CHANGES with zero Criticals**: route as APPROVE for loop purposes; park for UAT; do not start converge or a change retry.
- **Converged + open validator FAIL**: park immediately; do not re-enter critic, tester, or pr-review.
- **Unchanged converge fingerprint** (including the same validator finding IDs): stuck after three attempts, then park.
- **`CONVERGE_OUTCOME: blocked`**: park immediately (existing rule).
- **Plan-target FAIL**: park; do not treat it as implement-target.
- **Mixed LOOP_BACK on one FAIL**: if any finding is plan-target, park; do not start converge while that finding is open.
- **Missing `LOOP_BACK` on a FAIL**: assume `implement` for tester assertion-style failures and `plan` when the report already says the spec/plan is wrong; if still ambiguous, park (do not guess a new loop). Documented as an assumption for parent parsing.
- **Job path**: never pr-review, even if a PR was opened.
- **Change path**: no critic. REQUEST CHANGES with Criticals: FINDINGS to the change worker; never append `tasks.md`.
- **Re-review**: parent ship with same-PR reuse; previous report as extra context; review new work; merge gate Critical-only.
- **Spec directory ≠ git branch**: parent uses `FEATURE_DIR` / `.specify/feature.json` from specify; never infers the spec directory from `BRANCH`.
- **Parent never implements** and never writes spec/plan/tasks or ships from a worker session.
- **Tiny `$ARGUMENTS` convention** for converge (Criticals as arguments) is in scope; wholesale edits of `.pi/prompts` are out of scope.
- **Auto-merge**: never. UAT remains the existing operator pass/fail confirmation; merge stays human and outside the loop.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The documented feature graph MUST be `converge(converged) → critic → tester → ship → pr-review → uat`.
- **FR-002**: The parent dispatcher MUST launch critic automatically after feature-path `CONVERGE_OUTCOME: converged`, then tester only after critic PASS, then ship only after tester PASS (unless `keep-local`).
- **FR-003**: After feature-path `SHIP: ok`, the parent MUST launch pr-reviewer automatically. pr-reviewer MUST NOT remain on-demand-only for this path.
- **FR-004**: pr-reviewer APPROVE MUST route to the existing operator UAT pass/fail confirmation on the open PR. APPROVE MUST NOT complete the run by itself. Merge MUST remain human and outside the loop. Auto-merge MUST NOT be introduced.
- **FR-005**: pr-reviewer REQUEST CHANGES with at least one Critical MUST route to converge with those Criticals as `$ARGUMENTS`, then implement ↔ converge, then critic → tester, then parent ship with same-PR reuse (commit, push, refresh walkthrough; MUST NOT open a second PR), then re-review with the existing previous-report extra-context mechanism.
- **FR-006**: pr-reviewer BLOCKED (Phase 1.5) MUST park for the operator and MUST NOT start converge or implement.
- **FR-007**: The parent MUST NOT feed validator Criticals directly to implement. Implement-target failures MUST enter converge first.
- **FR-008**: Change-path tester FAIL and change-path REQUEST CHANGES with at least one Critical MUST retry via the change worker plus FINDINGS, then tester, then parent ship with same-PR reuse, then re-review. The change path MUST NOT write `tasks.md`, MUST NOT run converge, and MUST NOT run critic.
- **FR-009**: The job path MUST NOT run pr-reviewer.
- **FR-010**: Critic and tester compact reports MUST keep existing PASS/FAIL and MUST add `LOOP_BACK: implement | plan | none`.
- **FR-011**: `LOOP_BACK: implement` FAIL MUST go to converge then implement ↔ converge then critic → tester. `LOOP_BACK: plan` FAIL MUST park. PASS MUST use `LOOP_BACK: none`. If one FAIL report mixes implement-target and plan-target findings, the parent MUST park (any plan-target finding wins).
- **FR-012**: If converge returns `converged` while a validator FAIL is still open, the parent MUST park and MUST NOT re-run critic, tester, or pr-review.
- **FR-013**: Converge fingerprint MUST include validator finding IDs so a repeated finding is the same stuck point. Three attempts (original + two resumes) then park, matching existing stuck policy.
- **FR-014**: Converge source-refs MUST stay spec/plan/constitution (`FR-###`, `US1/AC2`, `plan: …`, `Constitution …`). Validator IDs MUST appear in the task description only (`[tester: flow-2]`, `[critic: C1]`, `[pr-review: C1]`). The system MUST NOT invent PR-review source-refs.
- **FR-015**: Converge MUST remain append-only to `tasks.md`. Validators MUST never write `tasks.md`.
- **FR-016**: Critic MUST check code against spec/plan before tests (implementation review remains required). pr-reviewer MUST check architecture, risk, and evidence after the PR opens. These MUST stay distinct.
- **FR-017**: Workers MUST stay stage-dumb. The parent MUST remain dispatcher-only: it MUST NOT implement, MUST NOT write spec/plan/tasks, and MUST NOT ship from a worker session.
- **FR-018**: `keep-local` MUST skip ship and automatic pr-review (and UAT). Feature-path critic and tester still run. Change-path tester still runs; change-path critic MUST NOT run.
- **FR-019**: pr-reviewer merge gate MUST remain Critical-only. REQUEST CHANGES with zero Criticals MUST be routed as APPROVE for loop purposes (UAT park; no converge; no change retry).
- **FR-020**: Re-review MUST use the existing pr-reviewer previous-report extra-context path. After critic+tester PASS (feature) or tester PASS (change), the parent MUST re-run ship with same-PR reuse and MUST NOT open a second PR.
- **FR-021**: Scope is parent dispatcher contracts and the listed docs/skills. Hermes runtime wiring is out of scope. `.pi/prompts` edits are out of scope except a tiny `$ARGUMENTS` convention if converge needs Criticals in arguments.
- **FR-022**: Spec/tasks outrank YAGNI during implement: the smallest diff that satisfies this spec, not a smaller product.
- **FR-023**: `AiNative/CHANGELOG.md` MUST bump to **0.4.0** for this deliverable. No extra git bootstrap, and no new project changelog unless an existing scheme already requires it.
- **FR-024**: Downstream stages MUST use `FEATURE_DIR` / `feature.json` from specify and MUST NOT infer the spec directory from `BRANCH`.
- **FR-025**: The change path MUST NOT run critic. Change-path validation remains tester-only.

### Key Entities

- **Parent dispatcher**: The speckit-orchestrate controller. Routes compact reports. Never implements or writes spec/plan/tasks.
- **Validator**: Critic, tester, or pr-reviewer. Stage-dumb. Emits compact reports. Never writes `tasks.md`.
- **LOOP_BACK**: Compact-report field on critic/tester: `implement`, `plan`, or `none`.
- **Validator finding ID**: Stable id inside a compact report (for example `C1`, `flow-2`) used in task descriptions and converge fingerprints, not as converge source-refs.
- **Converge fingerprint**: Identity of the current stuck point, including validator finding IDs when present.
- **PR-review verdict**: `APPROVE` | `REQUEST CHANGES` | `BLOCKED` (Phase 1.5).
- **Same PR**: The pull request opened by this run's first Ship step; later parent ship passes reuse it (commit, push, refresh walkthrough) rather than opening another.
- **Same-PR ship**: Parent-owned ship after a post-review validation PASS: commit, push, refresh walkthrough, keep the existing PR URL.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: An operator reading the feature-loop graph can recite the feature Validation-and-ship sequence as critic → tester → ship → pr-review → uat without being told to invoke pr-reviewer by hand.
- **SC-002**: In a tabletop happy path, zero extra operator prompts occur between `converged` and the UAT pass/fail confirmation (except `keep-local`, which ends after tester PASS with `SHIP: declined`).
- **SC-003**: In a tabletop REQUEST CHANGES path with Criticals, those Criticals enter converge before any implement pass, parent ship reuses the same PR, and re-review sees the previous report. A REQUEST CHANGES tabletop with zero Criticals parks for UAT with no converge.
- **SC-004**: In a tabletop Implement-target tester FAIL, the next worker is converge (not implement, not a new fix loop); a Plan-target FAIL parks; a mixed implement+plan FAIL parks.
- **SC-005**: In a tabletop where converge reports `converged` while a validator FAIL remains, the run parks and critic/tester/pr-review do not run again.
- **SC-006**: Two consecutive REQUEST CHANGES or tester FAILs that cite the same finding ID produce the same fingerprint component; the third unchanged attempt parks.
- **SC-007**: A change-path REQUEST CHANGES tabletop never creates or edits `tasks.md` and never launches critic; a job-path ship tabletop never launches pr-reviewer.
- **SC-008**: Critic docs still require implementation review before tests; pr-reviewer docs still describe architecture, risk, and evidence after Ship — an operator can distinguish the two in one sitting.
- **SC-009**: Changelog 0.4.0 exists for this work; the listed canonical files all describe the same routing rules (no contradictory “on-demand-only” leftover for the feature path).

## Assumptions

- **Skip clarify**: Operator `skip` was active. Session 2026-10-26 recorded five recommended answers in Clarifications. No `[NEEDS CLARIFICATION]` markers.
- **Actors**: “Operator” is the human running `/speckit-orchestrate`. “Parent” is that orchestrate dispatcher. Workers are specify/plan/implement/converge/change/critic/tester/pr-reviewer stages.
- **Product surface**: Methodology and agent contracts in AiNative (and host skill mirrors that already point at those files). Not Hermes in-process wiring.
- **pr-reviewer model profile**: Same Validation profile as critic/tester (fresh session, not the implement worker model).
- **When pr-review runs on change**: After change-path `SHIP: ok`, same automatic launch as feature; retries stay on the change worker (no critic). Job remains excluded.
- **Change path critic**: Never. Existing path isolation stands.
- **Stuck policy**: Existing three attempts (original + two resumes) apply to validator-driven converge fingerprints and to change-path FINDINGS retries.
- **Missing LOOP_BACK on FAIL**: Parent treats tester assertion/code failures as `implement` and explicit spec/plan contradictions as `plan`; if the report is still ambiguous, park.
- **APPROVE with Warnings**: Allowed; merge gate stays Critical-only (existing 0.2.3 rule). REQUEST CHANGES with zero Criticals is routed as APPROVE for the loop.
- **UAT after APPROVE**: Same operator pass/fail confirmation already used after Ship; not a finish-report-only park.
- **Re-review extra context**: Use the existing pr-reviewer `--extra previous-report` (or equivalent extra-context) mechanism; do not invent a new review protocol.
- **Same-PR ship**: After a successful post-REQUEST-CHANGES validation PASS, the parent re-runs ship (commit, push, refresh walkthrough) against the existing PR; workers still never ship.
- **FEATURE_DIR**: This specify run creates `specs/002-agentic-validation` independently of git branch `agentic-validation`. Downstream must read `.specify/feature.json`.
- **Changelog location**: Only `AiNative/CHANGELOG.md` (0.4.0). Speckit-orchestrate exception: do not add a playground-root changelog for this job.
- **Cursor/OpenCode copies**: Update AiNative canonical files; host skills that are the same file (symlink/mount) change with them. Do not maintain a second divergent copy.
- **Constitution**: Project constitution file is still a placeholder template; this feature follows the user-stated constraints instead.

## Out of Scope (explicit)

- Auto-merge; UAT and merge stay human.
- Hermes / personalAgent runtime wiring.
- Job-path pr-review.
- Critic on the change path.
- Dropping critic implementation review (feature path).
- Feeding Criticals directly to implement.
- A new fix loop distinct from implement↔converge (feature) or change+FINDINGS (change).
- Editing `.pi/prompts` except a tiny `$ARGUMENTS` convention for converge.
- Extra git bootstrap, new changelog files, or version bumps other than AiNative 0.4.0.

## In Scope (file list)

- `AiNative/docs/systems/feature-loop.md`
- `AiNative/docs/systems/validation-layer.md`
- `AiNative/docs/systems/pr-review-system.md` (only as needed so pr-review is a loop state after Ship, not on-demand-only)
- `AiNative/docs/agents/speckit-orchestrate/SKILL.md`
- `AiNative/docs/agents/speckit-orchestrate/rule.md`
- `AiNative/docs/agents/critic/` (`SKILL.md`, `rule.md`, compact-report / LOOP_BACK)
- `AiNative/docs/agents/tester/` (`SKILL.md`, `rule.md`, compact-report / LOOP_BACK)
- `AiNative/docs/agents/pr-reviewer/SKILL.md` and `rule.md`
- `AiNative/docs/agents/change/SKILL.md`
- `AiNative/CHANGELOG.md` (0.4.0)
