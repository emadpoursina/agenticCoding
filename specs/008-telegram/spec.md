# Feature Specification: Telegram Integration

**Feature Branch**: `008-telegram`

**Created**: 2026-09-02

**Status**: Draft

**Input**: User description: "go for Phase 6 — Telegram. in the /Users/emad/Projects/playground/agenticCoding/scratch/implimentation.md" (Phase 6 — Telegram: connect meaningful orchestration events to the existing Telegram integration; useful status commands if that architecture already supports them; human decision messages and resume after reply. Do not duplicate the existing transport.)

## Clarifications

### Session 2026-09-02

- Q: Which Telegram chats should get these notices and be allowed to send status questions or decision replies (like A / B)? → A: Only the already-connected chat (the one already used today).
- Q: If you send A or B in that chat when nothing is waiting for a decision, what should happen? → A: Reply that nothing is waiting; do not start or change any task.
- Q: If a notice fails to send (for example the chat is briefly unreachable), what should happen? → A: Retry that same notice a few times (three attempts total), then record the failure; do not change the task.
- Q: When nothing is running, what should `/status` show? → A: “Nothing running” plus the most recent finished item (last pull request, last block, or last failure).
- Q: When a task is waiting for A or B, which replies should count as a valid choice? → A: A single letter, with optional spaces, and optional trailing `.` or `)`. Sentences and “Option A” are not valid.

## User Scenarios & Testing *(mandatory)*

Phases 0–5 already deliver enrollment, isolated work copies, chained discovery → planning → implementation → validation, bounded recovery, parked human decisions, blocked escalation, and orchestrator-owned publish that ends in `PR_CREATED`. Those records exist on the control plane. They are **not yet delivered as operator-facing messages**. Parking still does not send a message. A pull request can exist while the operator never hears about it.

This feature is Phase 6: connect **meaningful orchestration events** to the **existing** messaging connection (already in use; already a first-class platform plugin with notify subscriptions). Do **not** rebuild the bot, do **not** add a second messaging stack, and do **not** log every internal operation (reading a file, running a command, “thinking”).

The people who benefit are operators: they learn when a task starts, when they must decide, when work is blocked, when recovery still failed, when a pull request is ready for human review, and when something failed unexpectedly. They can ask status without scanning every project repository. Methodology stays read-only. Project knowledge stays in the project. The existing task board stays the source of truth for *what* the work is. Execution state stays on the control plane. Messaging only **reports** that state and **carries** a decision reply back into the existing resume path.

This feature **adds** event delivery, status answers, and decision-message/resume-over-chat on top of the existing chain. It does not respecify enrollment, workspace prepare, agent runs, recovery classification, GitHub publish, container-restart persistence, or a future daily-report operations console.

### User Story 1 - Meaningful events reach the operator (Priority: P1)

When a workflow actually starts work, the operator receives a **task-start** message (once per run, not per internal step). When the workflow parks for a consequential choice, they receive a **human-decision** message. When the run enters blocked, they receive a **blocked** message. When a recovery cycle’s re-check still fails, they receive a **validation/recovery-failure** message. When a recovery cycle **starts**, they receive a **major recovery** message (once per cycle, not per edit). When publish succeeds, they receive a **PR-created** message with enough identity to open the review (number and link already recorded on the run). When the run ends as an unexpected `FAILED` (not an operator abandon), they receive an **unexpected-failure** message.

They MUST NOT receive chatter for reading files, running commands, or internal reasoning. A quiet run that never hits those events sends nothing extra. Notices go only to the **already-connected operator chat** (the same one already in use). Other chats MUST NOT receive these events.

If messaging is turned off, or the existing notify subscription has no delivery target, the workflow still completes; events are recorded as not sent. A failed send MUST NOT undo a pull request, MUST NOT change execution state to failed, and MUST NOT invent a second bot.

**Why this priority**: Phase 6 exists so operators hear the outcomes Phase 5 already records. Without these events, `PR_CREATED` and parked decisions stay invisible.

**Independent Test**: Drive fixture runs through start, park, recovery-start, recovery still-fail, blocked, publish, and unexpected fail. Confirm one message per required event, zero noisy internals, and that a simulated messaging channel (no live bot required for contract checks) received them. Confirm a disabled/unsubscribed path still returns `PR_CREATED` (or the same wait-return as today) with zero messages sent.

**Acceptance Scenarios**:

1. **Given** an eligible fixture and a start that begins work, **When** the workflow leaves idle and enters active work, **Then** exactly one task-start message is delivered for that run, naming the project and the task.
2. **Given** a run that parks at `HUMAN_DECISION_REQUIRED`, **When** that park is recorded, **Then** exactly one human-decision message is delivered containing the decision protocol in User Story 3 (not a one-line “paused”).
3. **Given** a run that enters `BLOCKED`, **When** that state is recorded, **Then** exactly one blocked message is delivered with enough of the existing escalation brief that the operator can choose `A` (abandon) or `B` (one more try).
4. **Given** a recovery cycle whose re-validation still fails, **When** that failure is recorded, **Then** exactly one validation/recovery-failure message is delivered for that cycle. If that failure also exhausts the budget and enters `BLOCKED`, the blocked message is still delivered (both events are required).
5. **Given** a recovery cycle that starts (diagnosis/debug, or a validate-only retry), **When** that cycle begins, **Then** exactly one major-recovery message is delivered for that cycle; file reads, command runs, and reasoning inside the cycle produce zero extra messages.
6. **Given** a successful publish, **When** the wait-return is `PR_CREATED`, **Then** exactly one PR-created message is delivered including the hosting pull-request number and the HTML URL already on the record.
7. **Given** a wait-return of `FAILED` that is not an operator abandon (`A` on blocked), **When** that failure is recorded, **Then** exactly one unexpected-failure message is delivered. Operator abandon MUST NOT send unexpected-failure.
8. **Given** a successful run, **When** the operator inspects the message log, **Then** there are 0 messages whose only content is reading a file, running a command, or thinking/reasoning.
9. **Given** messaging disabled or no delivery target on the existing notify subscription, **When** a run reaches `PR_CREATED`, **Then** the wait-return is still `PR_CREATED`, 0 messages were sent, and the send-skipped fact is visible on the operational record.
10. **Given** a send failure (channel unavailable), **When** publish already succeeded, **Then** execution state remains `PR_CREATED`, the pull request is not closed or rewritten because of the send failure, the same PR-created notice is retried up to three attempts total, and if it still fails the send error is visible on the operational record.

---

### User Story 2 - Status without scanning every repository (Priority: P2)

If the existing messaging architecture already routes slash-style commands cleanly, the operator can ask **from the already-connected chat only** (other chats MUST be ignored — no status answer, no workflow start):

- `/status` — what is happening now (active run, phase, next action)
- `/projects` — enrolled projects (operational registry, not a live disk walk of every repo)
- `/tasks` — tasks in play on the one existing board (not a rewrite of the board)
- `/blockers` — what is blocked or waiting on a human
- `/prs` — pull requests this control plane recorded as waiting for human review
- `/status project-a` — the same questions scoped to one enrolled project

Answers MUST come from control-plane operational state plus targeted lookup already owned by earlier phases — **not** by continuously rescanning every repository. Each answer covers: what is happening, what is blocked, what is running, what PRs are waiting, what needs a decision, what happened recently (for the active/recent run), and what happens next — at the granularity of that command.

If the existing gateway already accepts **natural-language equivalents** of those questions in the same chat, those phrases MUST return the same facts as the matching command. If the gateway does **not** already route free-text as commands, this feature MUST NOT invent a second language-understanding stack; slash commands (or the native command surface the gateway already has) are enough.

This is **not** a daily digest, not a full operations console, and not a second task board in chat.

**Why this priority**: Events tell the operator when something happened. Status lets them ask when they missed a message. It is independently valuable but secondary to event delivery.

**Independent Test**: With a fixture run in `RUNNING`, then parked, then `PR_CREATED`, invoke `/status`, `/projects`, `/tasks`, `/blockers`, `/prs`, and `/status` for one enrolled project name. Confirm answers match the operational record and that answering did not walk every enrolled working copy. If free-text routing already exists in the gateway, confirm one natural-language equivalent of `/status` returns the same facts; if it does not, confirm slash commands still work and no extra parser was required.

**Acceptance Scenarios**:

1. **Given** one active workflow in `RUNNING` (or `VALIDATING`), **When** the operator sends `/status`, **Then** the reply names the project, task, current phase, and that work is in progress — without starting a new workflow.
2. **Given** no active workflow, **When** the operator sends `/status`, **Then** the reply says nothing is running and includes the most recent finished item when one exists (last pull request waiting for review, last blocked run, or last unexpected failure); if there is no recent finished item, it only says nothing is running.
3. **Given** enrolled projects in the registry, **When** the operator sends `/projects`, **Then** the reply lists those enrolled projects from registry state (enabled/disabled as already recorded), not a fresh crawl of disk trees.
4. **Given** tasks on the one existing board, **When** the operator sends `/tasks`, **Then** the reply reflects board + execution overlay (what is running / parked / blocked), and the human-readable task bodies are not overwritten.
5. **Given** a run in `BLOCKED` or `HUMAN_DECISION_REQUIRED`, **When** the operator sends `/blockers`, **Then** the reply includes that run and what is waiting; if nothing is blocked or parked, the reply says so clearly.
6. **Given** at least one `PR_CREATED` record with number and HTML URL, **When** the operator sends `/prs`, **Then** the reply includes that identity; merge is still not offered as an action.
7. **Given** more than one enrolled project, **When** the operator sends `/status` with a known project name, **Then** the reply is scoped to that project; an unknown name fails visibly in chat without starting work.
8. **Given** any status command, **When** it is answered, **Then** 0 extra repositories were cloned or fully re-scanned solely to answer, and 0 workflows started as a side effect.
9. **Given** the existing gateway already routes free-text, **When** the operator asks a natural-language equivalent of `/status`, **Then** the facts match the `/status` reply. **Given** the gateway does not route free-text as commands, **When** this feature ships, **Then** slash (or native) commands still work and no second interpreter is added.

---

### User Story 3 - Decision message and resume after reply (Priority: P1)

When the control plane parks at `HUMAN_DECISION_REQUIRED` (discovery, planning, diagnosis, debug, or validation questions — already specified in earlier phases), the operator receives a structured decision request in the existing chat:

- Project
- Task
- Current phase
- Decision required
- Why it matters
- Options (labeled `A`, `B`, `C` in list order — the existing mutually exclusive list)
- Recommended option (when the parked brief already has one; do not invent a recommendation)
- Consequence of each option (when the parked brief already has consequences; if missing, the field is shown as not stated — do **not** invent product or architecture consequences)
- How to reply: the option letter (`A` / `B` / …)

The same **already-connected** chat is the resume path: a reply that is a listed letter (case-insensitive, optional surrounding whitespace, optional single trailing `.` or `)`) MUST invoke the **existing** resume behavior (re-run the parked step with that letter; no plan-approval gate; wait until the next park or terminal wait-return). After a valid letter, work continues automatically. A letter from any other chat MUST be ignored (no resume, no correction in that other chat). Sentences, “Option A”, “I pick A”, or other prose MUST NOT count as a letter.

A blocked run’s `A` / `B` escalation already exists. The blocked message (User Story 1) is that brief. A listed-letter reply in chat MUST invoke the existing blocked resume (`A` abandon, `B` one more cycle / validate-only as already specified). Invalid letters fail at the boundary: stay parked or blocked, send a short correction naming the listed letters, do not start the next phase.

Resume from chat MUST NOT merge, deploy, push a protected branch, or treat a free-form essay as a letter. Optional trailing `.` or `)` after a single listed letter is still a letter. If the operator replies in the existing programmatic resume call instead of chat, that path still works; chat is an additional entrance to the same resume, not a second state machine.

**Why this priority**: Events without a way to answer still leave the operator on a laptop-only resume. The product rule is: pause only for consequential decisions, then continue after the answer.

**Independent Test**: Park a fixture on a two-option planning question. Confirm the chat message includes the protocol fields. Reply `A` in the simulated chat. Confirm the existing resume path runs (planning re-runs with `A`, chain continues). Reply `Z` on another parked run and confirm it stays parked with a correction message. Confirm blocked `A`/`B` from chat matches the existing abandon / one-more-try rules.

**Acceptance Scenarios**:

1. **Given** a parked workflow with options `A` and `B`, **When** the human-decision message is delivered, **Then** it includes project, task, current phase, decision required, why it matters, labeled options, recommended option when present (else omitted or marked not stated), consequence per option when present (else not stated), and “reply with the letter”.
2. **Given** that parked workflow, **When** the operator replies `A`, `a`, `A.`, or `A)` (optional surrounding whitespace) in the same existing chat, **Then** the workflow leaves `HUMAN_DECISION_REQUIRED` and follows the existing resume rules for that park; the start/resume wait still ends at `PR_CREATED`, `FAILED`, `HUMAN_DECISION_REQUIRED`, or `BLOCKED`.
3. **Given** a parked workflow, **When** the operator replies with an unlisted letter, option prose (“Option A”, “I pick A”), a sentence, or an empty message treated as a decision reply, **Then** the workflow stays parked, a short correction is sent, and the isolated copy is not published as a side effect.
4. **Given** a blocked workflow, **When** the operator replies `A` or `B` in chat, **Then** the existing blocked resume applies (`A` → `FAILED` and release slot; `B` → one more recovery or validate-only cycle as already specified). An unlisted letter stays blocked with a correction.
5. **Given** a valid chat resume, **When** work continues, **Then** there is still no plan-approval gate; methodology is unchanged; merge is not performed.
6. **Given** a parked workflow, **When** the operator resumes with the existing programmatic resume (letter) instead of chat, **Then** behavior is unchanged from earlier phases; chat is not required for resume to work.
7. **Given** a parked or blocked workflow, **When** a listed letter arrives from a chat that is not the already-connected operator chat, **Then** the workflow stays parked or blocked, no resume runs, and that other chat receives no notice or correction.
8. **Given** no parked or blocked run (idle, running, or already finished), **When** the operator sends a listed option letter in the already-connected chat, **Then** the control plane replies that nothing is waiting for a decision, starts no workflow, and changes no execution state.

---

### Edge Cases

- **Noisy internals**: File reads, command runs, model “thinking”, per-file edits, and per-test lines MUST NOT become messages. Recovery internals stay off-chat except the one major-recovery message when a cycle starts.
- **Double events on last retry**: Exhausting recovery may emit validation/recovery-failure **and** blocked. That is required, not a defect. They MUST remain two distinct events.
- **Idempotent delivery**: Re-reading the same recorded state MUST NOT spam duplicate copies of the same event for the same run and event kind. A retry of a failed send MAY retry that one send up to three attempts total; it MUST NOT invent a second event kind.
- **Messaging off / no subscriber**: Skip send; do not fail the workflow; record skipped.
- **Send failure after success**: Leave execution state as already recorded (`PR_CREATED`, parked, blocked, or failed). Retry that **same** notice up to three attempts total (not a new event kind). If it still fails, record the send error. MUST NOT roll back a pull request.
- **Secrets**: Tokens, keys, and private URLs MUST NOT appear in messages, status replies, or operational send logs beyond what earlier phases already forbid on records.
- **Unknown project on `/status <name>`**: Visible chat error; no workflow start.
- **Empty board / nothing running**: `/tasks`, `/blockers`, `/prs` MUST say so clearly, not invent work. `/status` when nothing is running MUST say so and MUST include the most recent finished item when one exists (last pull request, last block, or last unexpected failure).
- **Slash commands vs free-text**: Use the existing gateway’s command surface. Do not add a second bot. Natural-language equivalents only if that gateway already treats free-text as commands.
- **Chat resume vs programmatic resume**: One resume state machine. Two entrances. Invalid chat text is not a third interpreter of architecture.
- **Abandon**: Blocked `A` is expected; do not label it unexpected-failure.
- **One-at-a-time**: Unchanged. Chat MUST NOT start a second workflow while the slot is occupied. Status commands do not occupy or release the slot.
- **Wait-returns**: Unchanged: `PR_CREATED`, `FAILED`, `HUMAN_DECISION_REQUIRED`, `BLOCKED`. This phase MUST NOT introduce a background worker.
- **Restart persistence**: Still out of scope. This phase MUST NOT claim that a killed container resumes from chat.
- **Concurrent workers**: Still one-at-a-time.
- **Live bot vs simulated channel**: Contract checks MAY use a simulated delivery channel so a live messaging account is not required. A live proof MAY use the already-connected chat; it MUST NOT silently create a second bot or a production-only dependency for checks.
- **Methodology writes**: Still forbidden.
- **Merge / deploy / protected push**: Still impossible through this workflow, including via chat text.
- **Wrong chat**: Events, status answers, and decision/resume letters are accepted only from the already-connected operator chat. A message from any other chat MUST NOT deliver notices there, MUST NOT answer status, MUST NOT resume, and MUST NOT start a workflow.
- **Letter while nothing is waiting**: A listed option letter in the already-connected chat when no run is parked or blocked MUST get a short “nothing is waiting” reply. It MUST NOT start a workflow, MUST NOT resume anything, and MUST NOT change execution state.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: When a workflow starts active work, the control plane MUST deliver exactly one **task-start** event on the existing messaging connection for that run (project + task). It MUST NOT deliver one event per internal operation.
- **FR-002**: When execution state becomes `HUMAN_DECISION_REQUIRED`, the control plane MUST deliver exactly one **human-decision** event whose body follows User Story 3 (project, task, phase, decision required, why it matters, labeled options, recommended option when known, consequence per option when known otherwise not stated, how to reply with a letter).
- **FR-003**: When execution state becomes `BLOCKED`, the control plane MUST deliver exactly one **blocked** event including the existing `A`/`B` escalation brief.
- **FR-004**: When a recovery cycle’s validation still fails, the control plane MUST deliver exactly one **validation/recovery-failure** event for that cycle. When a recovery cycle starts, it MUST deliver exactly one **major-recovery** event for that cycle. Both MAY occur on the same run; internals of the cycle MUST NOT emit extra events.
- **FR-005**: When the wait-return is `PR_CREATED`, the control plane MUST deliver exactly one **PR-created** event including the hosting pull-request number and HTML URL already on the record. Merge MUST NOT be offered.
- **FR-006**: When the wait-return is `FAILED` and the failure is not an operator abandon from blocked `A`, the control plane MUST deliver exactly one **unexpected-failure** event. Abandon MUST NOT use that event kind.
- **FR-007**: The control plane MUST NOT deliver events whose only content is reading a file, running a command, or thinking/reasoning.
- **FR-008**: Event delivery MUST use the **existing** messaging integration (existing gateway / notify subscription). This feature MUST NOT add a second bot, second transport, or duplicate messaging stack. It MUST NOT rebuild Telegram functionality that already exists. Events, status answers, and chat resume MUST use **only the already-connected operator chat**. Other chats MUST NOT receive events, MUST NOT receive status answers, and MUST NOT resume or start work.
- **FR-009**: If messaging is disabled or has no delivery target, the control plane MUST skip send, MUST still complete the workflow with the same wait-return as earlier phases, and MUST record that the event was not sent. If a send fails while messaging is enabled and a target exists, the control plane MUST retry **that same** notice up to three attempts total, MUST NOT invent a second event kind, MUST NOT change execution state, MUST NOT close or rewrite a pull request, and MUST record the error if all attempts fail.
- **FR-010**: If the existing messaging architecture routes commands cleanly, the control plane MUST answer `/status`, `/projects`, `/tasks`, `/blockers`, `/prs`, and `/status <project>` from operational state (registry, board, execution record, recorded pull-request identity). Answers MUST NOT continuously rescan every repository. Status MUST NOT start a workflow. Unknown project name on scoped status MUST fail visibly in chat. When nothing is running, `/status` MUST say so and MUST include the most recent finished item when one exists (last pull request waiting for review, last blocked run, or last unexpected failure).
- **FR-011**: Natural-language equivalents of those status questions MUST work only when the existing gateway already supports conversational commands. If it does not, this feature MUST NOT add a second language-understanding system.
- **FR-012**: A listed option letter received on the existing chat for a parked or blocked run MUST invoke the **existing** `resume_workflow` behavior (same letter rules, same wait-returns, no plan-approval gate). A valid chat letter is one listed option character, case-insensitive, with optional surrounding whitespace and optional single trailing `.` or `)`. Unlisted letters, empty decision replies, sentences, and phrases such as “Option A” MUST fail at the boundary, keep the run parked or blocked, and send a short correction. A listed option letter when **no** run is parked or blocked MUST send a short “nothing is waiting” reply, MUST NOT start a workflow, and MUST NOT change execution state. Chat MUST NOT be a second state machine.
- **FR-013**: Messages, status replies, and send records MUST NOT contain secrets. Execution state remains on the control plane; the human-readable task body MUST NOT be overwritten with notification churn.
- **FR-014**: This feature MUST reuse existing enrollment, workspace isolation, PIV/recovery, GitHub publish, single V0 slot, and resume. It MUST NOT duplicate the task board, MUST NOT write methodology, MUST NOT merge, MUST NOT deploy, MUST NOT push protected or default branches, and MUST NOT start concurrent workflows.
- **FR-015**: Contract checks MAY inject a stand-in model service, fixture board, simulated remote, and **simulated messaging channel** so a live bot account is not required to prove FR-001–FR-014. A live messaging proof MAY use the already-connected chat. The system MUST NOT silently choose a production repository or create a second bot for checks.
- **FR-016**: `run_workflow` / `run_next_workflow` / `resume_workflow` remain the trust boundary for starting and resuming work. Chat status is read-only. Chat resume is an entrance to the same resume boundary (validate letter, then resume). Invalid project, task, or letter still fails there with a visible error.

### Key Entities

- **Messaging connection**: The already-connected operator chat and its notify subscription. Not rebuilt. One delivery path. The sole allowed chat for events, status, and decision replies.
- **Orchestration event**: A meaningful, once-per-occurrence notice: task started, human decision required, major recovery, validation/recovery failure, blocked, PR created, unexpected failure.
- **Decision protocol message**: The structured human-decision event body (project, task, phase, decision, why, options, recommendation, consequences, how to reply).
- **Status answer**: A read-only snapshot from operational state for `/status`, `/projects`, `/tasks`, `/blockers`, `/prs`, or scoped `/status <project>`.
- **Chat resume**: An operator letter on the existing chat that enters the existing resume path.
- **Send record**: Whether an event was sent, skipped, or failed — stored with the run, not in the task body.

### Out of Scope

This specification covers connecting meaningful events to the existing messaging integration, status commands when that architecture already supports them, and decision/resume over that same chat. Explicitly deferred:

- Rebuilding the bot or transport
- A second messaging stack or second bot
- Phase 7 container restart / interrupted-run persistence
- Phase 8 full end-to-end declaration of V0
- Obsidian
- Automatic merge, human-equivalent approval, production deploy
- Concurrent execution of more than one workflow
- Future “Telegram operations interface / daily reports / PR summaries” console
- Inventing natural-language understanding if the gateway does not already route free-text
- Continuously rescanning every repository to answer status
- Learning / retrospectives / methodology-change proposals
- Silently selecting a production repository
- A second task database or a second task board

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: 100% of fixture runs that start active work produce exactly one task-start notice and 0 notices whose only content is a file read, command run, or thinking line.
- **SC-002**: 100% of parks at `HUMAN_DECISION_REQUIRED` produce one decision notice with the required protocol fields; 100% of valid chat letters (`A`, `a`, `A.`, `A)` with optional spaces) resume using the existing resume rules; 100% of unlisted letters, sentences, and “Option A” style phrases stay parked with a correction; 100% of listed-letter replies when nothing is parked or blocked get a “nothing is waiting” reply and start 0 workflows.
- **SC-003**: 100% of entries to `BLOCKED` produce a blocked notice; 100% of recovery cycles produce one major-recovery notice at start; 100% of recovery re-validations that still fail produce one validation/recovery-failure notice.
- **SC-004**: 100% of `PR_CREATED` wait-returns produce one PR-created notice that includes pull-request number and review link; 0 of those notices offer merge.
- **SC-005**: 100% of unexpected `FAILED` wait-returns (excluding operator abandon) produce one unexpected-failure notice; 100% of abandons produce 0 unexpected-failure notices.
- **SC-006**: When messaging is disabled or has no delivery target, 100% of otherwise successful publishes still wait-return `PR_CREATED` with 0 messages sent. When send fails after publish, 100% remain `PR_CREATED` (pull request not undone); that same notice is attempted at most three times, then the failure is recorded.
- **SC-007**: 100% of `/status`, `/projects`, `/tasks`, `/blockers`, `/prs`, and scoped `/status <project>` replies (when commands are in scope) match operational state without a full rescan of every enrolled repository and without starting a workflow. Operators can obtain that snapshot in one command round-trip (ask once, receive one answer). When nothing is running, 100% of `/status` replies say so and include the most recent finished item when one exists.
- **SC-008**: 0 second bots or second transports are introduced. 0 methodology writes. 0 merges. 0 protected-branch pushes caused by chat. 0 events, status answers, or resumes delivered to or accepted from a chat other than the already-connected operator chat.

## Assumptions

- **Existing connection is the delivery path.** Discovery already recorded a first-class messaging plugin and notify subscriptions. Phase 6 extends *what* is sent, not *how* the chat exists. Operators keep the already-connected chat. That chat is the **only** allowed source and destination for notices, status, and A/B replies. Other chats are ignored.
- **Simulated channel is enough for contract checks.** Same pattern as the simulated Git remote in the previous phase. A live chat proof is optional and must use the existing connection.
- **Status commands are in scope because the gateway is command-capable.** If inspection during planning finds no clean command hook, planning MUST fall back to delivering events + decision/resume only, and MUST record that status commands were skipped rather than inventing a second command parser. The default assumption is that commands **are** supported and will be specified as in FR-010.
- **Natural language is reuse-only.** No new interpreter. If free-text already reaches the same command surface, map the listed questions; otherwise slash/native commands only.
- **Consequences are not invented.** The implementation plan’s decision template includes consequences. Earlier phases may not have stored them. The message always has a place for them; missing means “not stated.”
- **Recommendation is not invented.** Same rule as consequences.
- **Skip-send does not fail the run.** Notifications are operator visibility, not a publish precondition. Definition of Done still requires the events to *work* when messaging is enabled and a target exists. A failed send is retried up to three attempts for that same notice, then recorded as failed; the task outcome stays unchanged.
- **Major recovery vs recovery-failure vs blocked** are three event kinds (start of cycle, cycle still failing, entered blocked). Overlap on the last attempt is intentional.
- **Unexpected failure** means terminal `FAILED` other than blocked-abandon. Discovery/planning/implementation hard stops and other unexpected stops use this event.
- **One event per kind per occurrence**, not per poll of state. Status commands are pull; events are push.
- **Chat resume is the same letter protocol** already used programmatically (`A`/`B`/`C`, case-insensitive, optional spaces, optional trailing `.` or `)`). Free-form discussion, “Option A”, and “I pick A” are not auto-parsed as decisions. A letter when nothing is waiting is a “nothing is waiting” reply, not a new task.
- **Config flag already exists** conceptually (`notifications.telegram.enabled`). Disabled means skip-send.
- **No rescan for status.** Project registry, board, and execution records from earlier phases are sufficient. Targeted inspect of a recorded pull-request identity is allowed; walking every clone is not. Idle `/status` uses those records for “nothing running” plus the most recent finished item.
- **V0 still one active workflow.** Chat cannot queue a second run while the slot is occupied.
- **Out of scope stays out.** Persistence/restart, full E2E declaration, Obsidian, auto-merge, production deploy, concurrency, and the future daily-report operations interface are not this feature.
- **Hands-off implementation later.** Specify only. Planning will inspect the live gateway before choosing send hooks. This spec does not name libraries, languages, or file paths as requirements.
