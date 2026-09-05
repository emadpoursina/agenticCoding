# Feature Specification: Live Hermes PIV Bridge

**Feature Branch**: `010-live-piv-bridge`

**Created**: 2026-09-05

**Status**: Draft

**Input**: User description: "Develop the live Hermes PIV bridge in personalAgent: first inspect the existing contracts and Hermes 0.20 extension points, then connect the native Kanban kanban.db board to PivOrchestrator through a real read-only SqliteTaskBoard adapter and a minimal runtime entry point used by the dispatcher; keep Kanban as the only task source of truth, never use MemoryTaskBoard in production, never create a second task database, and never modify AiNative. A live task must load project context, create an isolated feature/task-<id> worktree, run discovery → planning → implementation → validation, recover or block on failure, create a commit only in the feature worktree, push that branch through LiveGitHost, create or update a GitHub pull request, record PR_CREATED, and send the existing Telegram pr_created event; direct commits to main/master, automatic merge, deployment, secrets in records, and a second Telegram bot are forbidden. Add focused tests using temporary SQLite/Kanban fixtures and MemoryGitHost, preserve all existing tests and Ruff checks, add a safe live smoke-test command that requires an explicitly named disposable repository before any push, update documentation and CHANGELOG.md, and report the exact files changed, test results, runtime commands, and any external credentials still required."

## Clarifications

### Session 2026-09-05

- Q: When the live smoke test is allowed to push, what must the disposable repository name match so we never hit a real project by accident? → A: Both must match: the GitHub repository name (`owner/name`) and the enrolled project name. If either is missing or they disagree, refuse before any push.
- Q: When Hermes looks for the next live task on the Kanban board, which cards should it be allowed to start? → A: Only cards in the Ready / To Do column that already have the required fields. After inspection, map those names to the installed Hermes 0.20 column labels if they differ; do not start Backlog or parked cards.
- Q: If several eligible Ready cards exist, which one does next-ready start? → A: Highest priority first, then the oldest eligible card. Named start still selects that task id when it is eligible.
- Q: How should live work be started day to day? → A: The Hermes worker/tool calls the one dispatcher entry. The same entry MAY also be run from the command line for checks and smoke. No second start surface, no Telegram-only start for this slice.
- Q: If next-ready finds no eligible card? → A: Fail visibly at the trust boundary with 0 agent runs. Do not poll, wait, or fall back to Backlog.

## User Scenarios & Testing *(mandatory)*

Phases 1–7 plus the fixture end-to-end path already prove the control plane **in process**: enroll a project, prepare an isolated working copy, chain discovery → planning → implementation → validation, recover or block, publish a pull request, and notify the operator. Those checks inject an in-memory task board and a simulated hosting service so they never open the live Kanban file.

That is not enough for a **live** run. Today a Hermes worker cannot safely hand a real Kanban card to the orchestrator: production still has no read-only adapter over the native board, no minimal dispatcher entry, and no guarded live smoke path that refuses to push until an operator names a disposable repository.

This feature is the **first live vertical slice**: inspect the contracts and Hermes 0.20 extension points that already exist, then wire the native Kanban board to the existing orchestrator through a **read-only** live board adapter and a **minimal** runtime entry the dispatcher can call. One live task uses the real board as the only source of *what to do*, loads that project’s context, works only in `feature/task-<id>`, runs the existing chain through pull-request created, and sends the **existing** pull-request-created notice. Methodology stays read-only. No second task store. No in-memory board in production. No second bot.

This feature **does not** respecify enrollment, workspace safety, agent roles, recovery classification, GitHub merge bans, Telegram command surface, or restart reclaim. It **adds** live board wiring, a dispatcher entry, focused live-adapter checks, and a named-repo smoke gate. Later milestones in the whole-project plan (concurrent workers, Obsidian, learning, daily reports, multi-host) stay out of scope.

### User Story 1 - Native Kanban is the only live task source (Priority: P1)

An operator (or the dispatcher) starts work for a task that already exists on the **native Kanban board**. The orchestrator reads that card through a **read-only live board adapter**: identity, project, problem, expected result, platform, acceptance criteria, optional technical notes and dependencies, owner, reviewer, and priority. It MUST NOT invent those fields. It MUST NOT write execution churn into the human-readable card body.

The live adapter opens the **existing** native board file. It MUST NOT create a second task database, a second board file, or a parallel task table. The in-memory board used by existing checks MUST remain a **check-only** stand-in. The production / dispatcher path MUST NOT construct that in-memory board.

If the native file is missing, unreadable, or the task is not on the board, the start fails at the trust boundary with a visible error. Discovery MUST NOT begin. The adapter MUST NOT “repair” the board by inserting rows.

**Why this priority**: Without a real read of the native board, every later live step is still a fixture. Constitution and V0 require one board as source of truth.

**Independent Test**: Point the live adapter at a **temporary copy** of a Kanban-shaped board that contains one fixture card. Start (or look up) that task through the orchestrator’s existing start path. Confirm the loaded fields match the card. Confirm the adapter never wrote the file. Confirm production construction refuses the in-memory board. Confirm a missing file or unknown task fails before any agent run.

**Acceptance Scenarios**:

1. **Given** a temporary native-shaped board file with one ready fixture task, **When** the live adapter is asked for that task identity, **Then** it returns the card’s problem, expected result, platform, acceptance criteria, owner, reviewer, priority, and optional notes/dependencies exactly as stored — not invented by the caller.
2. **Given** that same file, **When** a workflow starts for that task, **Then** later steps receive those board fields, and the human-readable body, owner, reviewer, and priority are unchanged after the run (execution state lives on the control plane).
3. **Given** the dispatcher / production entry, **When** it constructs the orchestrator, **Then** it uses the live read-only board adapter pointed at the isolated Hermes home board file, and MUST NOT construct the in-memory check board.
4. **Given** a missing board file, a corrupt unreadable file, an unknown task identity, a card not in Ready / To Do (or installed equivalent), or next-ready with 0 eligible cards, **When** start or lookup is attempted, **Then** the call fails at the trust boundary with a visible error and 0 agent runs start.
5. **Given** any live start, **When** a reviewer inspects persistence, **Then** there is still exactly one task board file (the native Kanban file); 0 new task databases or task tables were created.

---

### User Story 2 - Dispatcher runs one live task through pull request and notice (Priority: P1)

The dispatcher has a **minimal runtime entry** (one start surface, not a second orchestrator). After inspecting Hermes 0.20 extension points, that entry is what a Hermes worker calls. The same entry MAY be invoked from the command line for checks and smoke. It MUST reuse the existing public start / next-ready / resume operations. It MUST NOT add a background worker of its own, and this slice MUST NOT add a Telegram-only start path.

**Next-ready** MAY start only a card that is in the Ready / To Do column (or the installed Hermes 0.20 equivalent) **and** already has the required fields. Incomplete cards, Backlog, and parked columns are not eligible. If several eligible cards exist, start the **highest priority**, and if tied, the **oldest**. If none are eligible, the start fails visibly and 0 agent runs begin. Named start still requires that the named card is on the board, complete, and in an eligible column.

A successful live task, in order:

1. Load **project context** from the enrolled project (instructions and conventions stay in the project).
2. Create or reuse an **isolated** working copy on branch `feature/task-<id>` (the task identity from the board). Unrelated tasks MUST NOT share that copy.
3. Run **discovery → planning → implementation → validation** using the existing chain. There is no plan-approval gate.
4. On check failure, **recover** within the existing bounded budget, or **block** and escalate — same as today. Do not invent a second recovery machine.
5. Create a **commit only** in that feature working copy / feature branch. The enrolled project location and default/protected branches are unchanged.
6. **Publish** that feature branch through the **live** hosting adapter (the production GitHub path). Create or update the pull request against the project’s default branch.
7. Record **`PR_CREATED`** on the operational record (number and HTML URL already required).
8. Send the **existing** Telegram **pull-request-created** event to the already-connected chat. Do not add a second bot or a new event kind.

Forbidden through this entry: commit or push to `main` / `master` / protected branches; automatic merge; deploy; secrets in operational records, pull-request bodies, or notices; writing methodology.

**Why this priority**: This is the live vertical slice the operator asked for. Adapter-only without this path does not hand a human a reviewable change.

**Independent Test**: Drive a fixture that uses the live board adapter against a temp Kanban file, a disposable enrolled project, and a **simulated** hosting service for the automated check. Confirm the chain, isolated `feature/task-<id>`, commit only on that branch, `PR_CREATED`, and the existing pull-request-created notice. Confirm 0 default-branch commits, 0 merges, 0 deploys, 0 secrets in records. Confirm methodology files are unchanged.

**Acceptance Scenarios**:

1. **Given** an eligible enrolled project, a ready task on the native-shaped board, and a valid isolated working copy policy, **When** the dispatcher entry starts that task, **Then** project context is loaded, an isolated copy exists on `feature/task-<id>`, discovery then planning then implementation then validation run, and on validation pass the live hosting path publishes the feature branch and records `PR_CREATED`.
2. **Given** validation failure that is recoverable under existing rules, **When** the chain continues, **Then** recovery runs within the existing attempt budget; if the budget is exhausted, state is `BLOCKED` and no publish occurs.
3. **Given** a successful publish, **When** the operator inspects Git history, **Then** the new commit exists only on the feature branch in the isolated copy; 0 commits were created on `main` or `master`; 0 merges; 0 deploys.
4. **Given** `PR_CREATED`, **When** notices are inspected, **Then** exactly one existing pull-request-created event was emitted (or recorded as skipped if messaging is off), and 0 second bots or new event kinds were added.
5. **Given** any live run, **When** records and pull-request text are inspected, **Then** 0 secrets, tokens, or private keys appear there; methodology is unmodified.

---

### User Story 3 - Safe checks: temp board fixtures, simulated hosting, named-repo smoke (Priority: P1)

Automated checks MUST prove the live adapter and dispatcher entry without a production repository and without a live hosting account. They use:

- a **temporary** SQLite / Kanban-shaped board fixture (not the operator’s real board as the only gate);
- the existing **simulated** hosting service for push/PR contract behavior;
- the existing stand-in model where a live model is not required.

All **existing** checks and style checks MUST still pass.

A **live smoke** path MAY push to GitHub, but only after the operator **explicitly names a disposable repository**. If that name is missing, empty, or not the named disposable target, the smoke command MUST refuse **before any push**. It MUST NOT silently pick an enrolled production project. It MUST NOT push to `main` / `master`.

When implementation is done, the change set MUST update operator documentation and the version history log, and the implementer MUST report: files changed, check results, runtime commands, and which **external credentials** are still required (hosting SSH, already-connected chat, model provider) — none of those credentials MAY be written into the repo.

**Why this priority**: Live GitHub without a named disposable target is an irreversible external action. Checks that only use the in-memory board would miss adapter bugs.

**Independent Test**: Run new focused checks against a temp Kanban file and simulated hosting; run the existing suite and style checks. Invoke the smoke command without a disposable repository name and confirm 0 pushes. Invoke it with an explicit disposable name in a dry or fixture setting and confirm it would only target that name.

**Acceptance Scenarios**:

1. **Given** the new focused checks, **When** they run, **Then** they create a temporary native-shaped board, read it through the live adapter, and use simulated hosting — they MUST NOT require github.com, a live chat, or the operator’s real Kanban file.
2. **Given** the existing check suite and style checks, **When** this feature is complete, **Then** they still pass (no regressions).
3. **Given** the live smoke command with no disposable repository name (or a blank name), **When** it is invoked, **Then** it fails visibly and performs 0 pushes and 0 pull-request opens.
4. **Given** the live smoke command with an explicitly named disposable repository whose GitHub `owner/name` **and** enrolled project name both match that same identity, **When** it is allowed to proceed, **Then** every push and pull request targets that named repository’s feature branch only, never `main`/`master`, and never an unnamed enrolled production repository. If the GitHub name and enrolled name disagree (or either is missing), the command refuses before any push.
5. **Given** a finished delivery, **When** a reviewer reads documentation and the version history log, **Then** they can find how to run the dispatcher entry, the checks, and the smoke command, plus which external credentials remain outside git.

---

### User Story 4 - Inspect first; extend Hermes; do not rewrite methodology (Priority: P2)

Before changing runtime wiring, implementers inspect the **existing** control-plane contracts (board protocol, orchestrator, workspace, hosting, messaging, restart overlay) and **Hermes 0.20 extension points** (how workers, tools, and the dispatcher already attach). The live entry MUST fit those extension points. It MUST NOT fork Hermes, MUST NOT rebuild Telegram, and MUST NOT modify AiNative (no writes to the methodology tree).

If Hermes already provides the native board file, worker dispatch, or notify transport, this feature **adapts** to them. Duplicate Kanban, duplicate chat, or a second control plane are failures.

**Why this priority**: Platform-native over rebuild. The slice is a bridge, not a new product.

**Independent Test**: Review the change set: methodology tree diff is empty of writes; no second bot; dispatcher calls the one new/minimal entry; native board file remains the board. A short discovery note in research (planning phase) or operator docs is enough; this story does not require a live Hermes version bump.

**Acceptance Scenarios**:

1. **Given** the existing contracts and Hermes 0.20 extension points, **When** the live entry is added, **Then** it is the dispatcher-facing call into the existing orchestrator — not a second orchestrator and not a rewrite of Hermes.
2. **Given** a completed change set, **When** methodology is compared to before this feature, **Then** 0 methodology files were modified by the live bridge.
3. **Given** messaging on the success path, **When** pull-request-created is sent, **Then** it uses the existing transport and event kind; 0 new bots.

---

### Edge Cases

- **Read-only board**: Live adapter MUST NOT insert, update, or delete Kanban rows. Execution overlay remains the place for run state.
- **Unknown / incomplete card**: Missing required headings or invalid priority fails at the trust boundary (same completeness rules as today). Do not start discovery.
- **Wrong column**: Next-ready and named start MUST NOT start a card that is not in Ready / To Do (or the installed equivalent). Backlog and parked cards fail at the boundary.
- **Several ready cards**: Next-ready picks highest priority, then oldest. It MUST NOT start two cards.
- **No eligible card**: Next-ready fails visibly; 0 agent runs; do not poll or fall back to Backlog.
- **Wrong project**: Named start whose board `project_id` does not match the enrolled project fails at the boundary.
- **Occupied slot**: One active live run at a time; second start refused (existing slot rules, including restart reclaim).
- **Dirty or missing worktree**: Reuse existing workspace recover/prepare rules; do not share copies; do not work on default/protected branches.
- **Publish before validation pass**: Forbidden (existing GitHub rules).
- **Smoke without name**: Refuse before network publish.
- **Messaging off or send failure**: `PR_CREATED` still stands; existing skip/retry rules; do not close the pull request because a notice failed.
- **Hermes schema drift**: If 0.20 board columns differ from the documented native shape, adapt the reader to the **installed** schema after inspection; do not create a parallel store “to be safe.”
- **In-memory board in tests**: Allowed. Production entry MUST fail closed if someone wires the in-memory board as the live board.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: Production and dispatcher construction MUST attach the orchestrator to a **read-only live board adapter** over the existing native Kanban file (`kanban.db` in the isolated Hermes home). That file remains the only task source of truth. The adapter MUST implement the existing board read protocol (`get` / `list`) and MUST NOT write the board.
- **FR-002**: The in-memory board used by checks MUST NOT be constructed on the production / dispatcher path. Using it as the live board is a trust-boundary failure.
- **FR-003**: The system MUST NOT create a second task database, second board file, or second task table. Operational overlay stays the execution record (unchanged).
- **FR-004**: A **minimal runtime entry** MUST exist for the Hermes dispatcher / worker to start one task (named or next-ready) and to resume. The same entry MAY be run from the command line for checks and smoke. It MUST call the existing orchestrator operations and MUST NOT start a second background worker, a second orchestrator, or a Telegram-only start path in this slice.
- **FR-004a**: Next-ready MUST consider only cards in Ready / To Do (or the installed Hermes 0.20 equivalent) that already have required fields. Selection among eligible cards is highest priority, then oldest. Zero eligible cards MUST fail at the trust boundary with 0 agent runs (no polling, no Backlog fallback). Named start MUST refuse a card that is missing, incomplete, or not in an eligible column.
- **FR-005**: Before that entry is designed, implementers MUST inspect existing contracts and Hermes 0.20 extension points and adapt to them (native board, notify transport, worker hook). Hermes MUST NOT be forked; methodology MUST NOT be modified.
- **FR-006**: A live task MUST load project context from the enrolled project, then ensure an isolated working copy on branch `feature/task-<id>` where `<id>` is the board task identity. Default/protected branches MUST NOT be used as the work branch.
- **FR-007**: The live path MUST run discovery → planning → implementation → validation with the existing orchestrator. No plan-approval gate. Consequential questions still park at `HUMAN_DECISION_REQUIRED`.
- **FR-008**: Check failure MUST use the existing recover-or-block behavior (bounded recovery, then `BLOCKED`). This feature MUST NOT add a second failure machine.
- **FR-009**: After validation pass, the orchestrator MUST ensure a commit **only** on the feature branch in the isolated copy, publish through the **live** hosting adapter, create or update the pull request, and wait-return `PR_CREATED` with number and HTML URL. Implementation/debug MUST still not publish.
- **FR-010**: Direct commit or push to `main`/`master`/protected branches, automatic merge, and deploy MUST remain impossible through this entry.
- **FR-011**: On `PR_CREATED`, the system MUST emit the **existing** Telegram pull-request-created event (same kind, same already-connected chat). A second bot and a new event kind are forbidden.
- **FR-012**: Secrets, tokens, and private keys MUST NOT appear in operational records, pull-request bodies, notices, or the version history log.
- **FR-013**: Focused automated checks MUST cover the live adapter against **temporary** SQLite/Kanban fixtures and MUST use the simulated hosting service for publish/PR behavior. They MUST NOT require a live hosting account, live chat, or the operator’s real board file.
- **FR-014**: All existing automated checks and style checks MUST still pass.
- **FR-015**: A live smoke command MUST require an **explicitly named disposable repository** before any push. The name MUST match **both** the GitHub repository identity (`owner/name`) **and** the enrolled project name. Missing name, blank name, missing enrollment, or a mismatch between GitHub identity and enrolled name → refuse with 0 pushes. Named matching target → feature-branch only. Silent selection of a production repository is forbidden.
- **FR-016**: Delivery MUST update operator documentation and `CHANGELOG.md`, and MUST report files changed, check results, runtime commands, and remaining external credentials (those credentials stay outside git).
- **FR-017**: `run_workflow` / `run_next_workflow` / `resume_workflow` remain the trust boundary. Invalid board, missing file, occupied slot, merge/protected-push, and unnamed smoke MUST fail there with a visible error.

### Key Entities

- **Native Kanban board**: The existing Hermes task board file. Sole source of *what* the work is.
- **Live board adapter**: Read-only reader of that file into the existing board protocol. Production only.
- **In-memory board**: Check-only stand-in. Forbidden in production construction.
- **Dispatcher entry**: Minimal start/resume surface the Hermes worker calls.
- **Task work branch**: `feature/task-<id>` on the isolated copy.
- **Live hosting adapter**: Production GitHub path (SSH to github.com). Checks keep the simulated host.
- **Pull-request-created notice**: Existing messaging event; not a new kind.

### Out of Scope

- Concurrent workers, capacity-aware scheduling, multi-host execution
- Obsidian, daily reports, operations console beyond existing status commands
- Learning / retrospectives / automatic methodology PRs
- Automatic merge, deploy, production modification
- A second Telegram bot or rebuilt notify transport
- A second task store
- Rewriting the PIV/recovery/GitHub/Telegram/restart specs
- Silently choosing a real production repository for smoke
- Installing an extra planning framework or editor-specific agent files
- Changing enrolled project source in place

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: 100% of production/dispatcher starts read tasks from the native board via the live adapter; 0% construct the in-memory check board; 0 second task stores exist after the change.
- **SC-002**: An operator (or dispatcher) can finish one ready live task in a single start wait: context loaded, isolated `feature/task-<id>` used, discovery through validation run, recover or block on failure, feature-branch commit only, pull request created or updated, record is `PR_CREATED`, existing pull-request-created notice sent or recorded skipped.
- **SC-003**: 0 live-path commits land on `main`/`master`; 0 merges; 0 deploys; 0 secrets in records or notices; 0 methodology writes.
- **SC-004**: 100% of new focused checks pass against temp Kanban fixtures and simulated hosting without github.com or live chat; 100% of previously passing checks and style checks still pass.
- **SC-005**: 100% of smoke invocations without an explicit disposable repository name, or where the GitHub `owner/name` and enrolled project name do not both match that name, perform 0 pushes; 100% of allowed smoke pushes target only that named disposable repository’s feature branch.
- **SC-006**: A reviewer can follow documented commands to run checks, the dispatcher entry, and smoke, and can see which external credentials are still required — without those secrets appearing in the repository.

## Assumptions

- **Scope is the live bridge, not later milestones.** Whole-project `scratch/implimentation.md` is context. This spec covers native board → orchestrator → dispatcher entry → live publish → existing notice, plus tests and named-repo smoke. Concurrent workers, Obsidian, learning, and daily ops are out.
- **Phases 1–7 and the fixture end-to-end path already exist.** This feature wires live I/O; it does not rebuild the orchestrator, recovery, GitHub rules, Telegram kinds, or restart overlay.
- **`SqliteTaskBoard` is the live adapter name** already reserved in earlier planning (`ponytail` upgrade). It is stdlib SQLite, read-only, pointed at the isolated Hermes home board file. Schema follows the **installed Hermes 0.20** board after inspection; if columns differ, the reader adapts — still no second store.
- **`MemoryTaskBoard` remains checks-only.** Existing tests keep it. Production `from_config` / dispatcher entry MUST take the live adapter (or fail if the live file cannot be opened).
- **`LiveGitHost` is production publish; `MemoryGitHost` stays in automated checks.** Smoke is the only automated-adjacent path that may call live publish, and only after an explicit disposable repository name.
- **Branch name is `feature/task-<id>`** as requested. If an older workspace already used a different allowed pattern for the same task identity, reuse that copy rather than creating a second worktree (existing isolation rules).
- **Dispatcher “minimal entry”** is a thin function or module the Hermes 0.20 worker/tool can call (for example a single `main` / `run` that loads config, `become_ready`, then `run_workflow` / `run_next_workflow`). The same entry is what operators run from the command line for checks and smoke. Exact hook file follows inspection. No extra scheduler and no Telegram-only start in this slice.
- **Next-ready eligibility** is Ready / To Do (mapped to installed column names) plus existing completeness rules. Tie-break: highest priority, then oldest. Empty eligible set fails closed.
- **Hermes 0.20** is the installed platform to adapt to. Do not assume docs over the running image; inspect extension points first.
- **AiNative is read-only.** Workers and this bridge MUST NOT modify it. Lessons stay out of this slice.
- **One active task** remains the V0 rule. Restart reclaim still applies.
- **Telegram**: reuse existing `pr_created` kind and already-connected chat. No new kinds for this slice (task-start and others already specified earlier stay as previously implemented).
- **Smoke target**: operator must pass the disposable repository identity as an explicit argument or environment value that is empty-by-default. Allowed smoke requires that identity to match **both** GitHub `owner/name` and the enrolled project name. Enrolled `ich-mag-dich` (or any real project) MUST NOT be used unless that same identity is explicitly passed as the disposable name **and** enrollment agrees — default is refuse.
- **External credentials still required after this feature** (not stored in git): GitHub SSH (agent forwarding), existing Telegram bot token/chat already used by Hermes, model provider key already used by Hermes. Smoke documents these; it does not commit them.
- **Isolated Hermes home** remains `~/.hermes/personal-agent`. Do not write the default `~/.hermes` root.
- **No new third-party libraries** without an explicit owner request. Python 3.12, pytest, ruff unchanged.
- **Specify iteration 1 records defaults; parent clarify may refine later.** No blocking questions in this spec.
- **Constitution invariants hold:** spec-first; least code; platform-native Kanban; trust-boundary tests; human authority on merge/deploy; no secrets in git.
