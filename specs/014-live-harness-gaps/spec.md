# Feature Specification: Live Harness Adapter Gaps

> **Superseded by `018-unified-feature-loop` for execution shape.** Live
> execution is now the Hermes-owned feature loop with one new Pi session
> per agent state (`AiNative/docs/systems/feature-loop.md`). The
> whole-playbook execution described in this spec is retired from the live
> path; this document is kept for history.

**Feature Branch**: `014-live-harness-gaps`

**Created**: 2026-09-08

**Status**: Draft

**Input**: User description: "Close the live Harness Adapter gaps so a real Hermes run can reach Pi."

## Scope and inherited decisions

This is a gap-closure feature for the locked product decisions in
`specs/013-harness-adapter-pi/` and
`scratch/HarnessAdapterArchitecture.md`. It does not reopen those decisions.
Hermes remains the orchestration layer and Pi remains the execution harness.
Hermes must not restore the removed
`scout → plan → tasks → PLANNING_COMPLETE → implement` path, add a second
harness, or sequence Spec Kit stages itself.

Skip is active for this specification. The assumptions section records the
defaults used instead of asking clarification questions.

## Clarifications

### Session 2026-09-08

- Q: Should Hermes reject a timeout that is merely large, or accept any positive finite timeout including the checked-in 1800? → A: Accept any positive finite timeout; do not add a new upper cap.
- Q: After Pi settles with one structured result, what if the Pi process is still running? → A: End the harness attempt and stop the leftover process so it cannot keep writing.
- Q: Must the Docker live proof run the real project Pi program, or is a protocol stub in the container enough? → A: Live Docker proof must exec the real project `pi --mode rpc`; offline tests keep the fake Pi.
- Q: Is `pi --mode rpc` a one-shot JSON document exchange or a multi-turn session? → A: Hermes sends one prompt command for one job, privately consumes Pi's JSONL event stream until settlement, and extracts one final result; Hermes exposes no operator event stream or multi-turn harness session.
- Q: Does putting Pi in the Hermes image, or mounting the same container-runnable binary, both count as done? → A: Either image or mount satisfies availability; Pi only on the Mac host does not.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Start a real Pi process for one task (Priority: P1)

An operator starts an eligible task through Hermes. Hermes starts the Pi program
already available to the Hermes container as a separate process using
`pi --mode rpc`, with the task worktree as its working folder. Hermes sends one
JSON `prompt` command containing the task and any skip/resume notes, privately
consumes Pi's JSONL responses and events until the run settles, extracts one
structured final result, and maps that result to the existing generic harness
contract.

Pi owns the Spec Kit playbook and does not chat with the operator. If Pi needs
a person, it stops and Hermes parks the task. A marker file alone is not
treated as an executable Pi runtime.

**Why this priority**: A live Hermes run cannot reach Pi until the configured
runtime is an actually runnable program inside the container.

**Independent Test**: Run a disposable task through the Docker Hermes path with
the real project Pi program (`pi --mode rpc`). Verify the child process,
working folder, single job, single result, status mapping, leftover-process
stop, and worktree-only writes. Offline tests may still use the fake Pi.

**Acceptance Scenarios**:

1. **Given** the Hermes container has a runnable Pi program and a prepared task
   worktree, **When** Hermes starts the task, **Then** it launches one separate
   `pi --mode rpc` process with the task worktree as its working folder.
2. **Given** a task start with skip or saved resume context, **When** Hermes
   sends the Pi job, **Then** the job contains that context and no Spec Kit
   stage sequence is sent as a Hermes lifecycle script.
3. **Given** Pi returns a valid completion, failure, human-needed, or stuck
   result, **When** Hermes receives it, **Then** Hermes returns exactly one
   normalized result with the matching existing status.
4. **Given** Pi asks for a person, **When** Pi returns its question result,
   **Then** Hermes parks the task and Pi does not continue or directly contact
   the operator.
5. **Given** the configured path contains only a `manifest.json` marker and no
   runnable Pi program, **When** Hermes starts a task, **Then** it reports a
   visible startup failure and does not use the removed legacy path.

---

### User Story 2 - Load the checked-in timeout and start Pi (Priority: P1)

An operator uses the checked-in harness configuration without editing the
timeout format. Hermes accepts the configured timeout whether the subset YAML
reader represents it as a number or as a numeric string, and uses it before
starting Pi.

**Why this priority**: The current default timeout is valid configuration but
is rejected before the live adapter can start, so it blocks every real run.

**Independent Test**: Load the checked-in default configuration and focused
configuration fixtures for numeric values, numeric strings, and invalid values.
Then verify a valid live-style run reaches Pi startup.

**Acceptance Scenarios**:

1. **Given** the checked-in default configuration contains
   `timeout_seconds: 1800`, **When** Hermes loads it, **Then** configuration
   loading succeeds and the timeout is available to the harness.
2. **Given** a timeout is a positive numeric string, **When** Hermes loads the
   configuration, **Then** it accepts the value as a number for the run.
3. **Given** the timeout is missing, zero, negative, non-numeric, infinite, or
   otherwise invalid, **When** Hermes loads the configuration, **Then** it
   rejects the configuration before Pi starts.

---

### User Story 3 - Resume acknowledged leftover work after restart (Priority: P1)

An operator sees a task parked because it was left in the removed legacy
short-path workflow. The operator acknowledges the parking decision. A new
Hermes process can then start a fresh generic harness run for that task rather
than parking it again.

Hermes must not auto-start Pi while the leftover task is waiting for human
acknowledgement, and it must not revive the old stage machine.

**Why this priority**: Acknowledgement currently leaves the old-path marker
behind, so a restart cannot make progress through the new generic path.

**Independent Test**: Create a persisted legacy short-path record, start Hermes,
verify it parks without starting Pi, acknowledge it, start a new Hermes
process, and verify the new process starts the generic harness path once.

**Acceptance Scenarios**:

1. **Given** a persisted task record identifies removed legacy short-path work,
   **When** a new Hermes process loads it, **Then** Hermes parks it for human
   acknowledgement and does not start Pi.
2. **Given** the operator acknowledges the parked legacy record, **When** the
   acknowledgement is saved, **Then** the old-path marker is cleared while the
   task's retained worktree and review context remain available.
3. **Given** the acknowledgement was saved and a new Hermes process starts,
   **When** it reclaims the task, **Then** it begins a fresh generic harness
   run and does not park the task again because of the cleared marker.
4. **Given** a task has not been acknowledged, **When** a new Hermes process
   starts, **Then** it continues to park the task and does not auto-start Pi.

---

### User Story 4 - Keep offline proof on the fake Pi boundary (Priority: P1)

Maintainers can run the existing offline tests without installing or importing
the Pi TypeScript SDK. The fake Pi remains the test stand-in, while the live
path proves process execution through the generic request/result contract.

**Why this priority**: The feature must close the production wiring gap without
making tests depend on live credentials, Docker, or a new SDK dependency.

**Independent Test**: Run the focused pytest and Ruff checks with the fake Pi,
then inspect the generic contract and imports for Pi SDK types, Cursor model
slugs, and embedded Spec Kit stage scripts.

**Acceptance Scenarios**:

1. **Given** the offline test suite, **When** it runs, **Then** tests use the
   fake Pi and complete without live model credentials or a TypeScript SDK.
2. **Given** generic harness request/result data, **When** it is inspected,
   **Then** it contains no Pi SDK types, Cursor model slugs, private reasoning,
   tokens, or secrets.
3. **Given** the live adapter proof, **When** it returns `completed`, **Then**
   Hermes may continue to its existing validation path; live GitHub publishing
   remains owned by the existing Hermes-after-validation workflow.

---

### Edge Cases

- Pi is missing, not executable, cannot be started, exits before returning
  JSON, or returns malformed JSON: Hermes returns `failed` and does not fall
  back to the removed short path.
- Pi returns an unknown status, more than one result, or unsafe artifact/change
  paths: Hermes rejects the result and does not validate or publish it.
- Pi times out or is terminated: Hermes returns `failed`, retains inspectable
  worktree artifacts, and does not report `completed`.
- Pi settles with one valid structured result but the process is still running:
  Hermes ends the harness attempt, maps that one result, and stops the
  leftover process so it cannot keep writing in the worktree.
- A rejected prompt, malformed RPC event, second structured result, missing
  final result, or mixed non-JSON output: Hermes rejects the run as malformed
  and does not treat it as `completed`.
- The timeout is a boolean, blank string, whitespace-only string, decimal with
  invalid content, zero, negative, infinite, or non-numeric: Hermes rejects it
  before process start. A positive finite timeout, including the checked-in
  1800, is accepted; this feature does not add a new maximum.
- The task worktree is missing, is the enrolled project root, is a sibling
  task worktree, or is a protected/default branch: Hermes refuses to start Pi.
- A legacy record contains partial native Spec Kit artifacts: Hermes keeps them
  for review, parks until acknowledgement, and never treats them as permission
  to resume the old stage machine.
- Acknowledgement is replayed: it remains safe and does not create a second
  task database, second harness run, or duplicate human transition.
- The harness asks for a human after a restart: Hermes parks the current
  generic attempt and resumes only through the existing human-decision flow.
- Pi attempts to push, merge, open a pull request, deploy, write AiNative, or
  write outside the current task worktree: the operation is refused and the
  run cannot become `completed`.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: Hermes MUST start the Pi program already available to the
  running Hermes container as a separate process using `pi --mode rpc` for one
  task work attempt. The task worktree MUST be the process working folder. Pi
  MAY be baked into the Hermes image or mounted as the same container-runnable
  binary. A Mac-host-only Pi program MUST NOT be treated as available.
- **FR-002**: Hermes MUST send exactly one JSON `prompt` command per harness
  attempt, containing the task context, task worktree context, execution
  constraints, and optional skip/resume notes. Hermes MUST privately consume
  Pi's JSONL responses/events until settlement and extract exactly one
  structured final result. The live path MUST NOT expose a Pi event stream or
  operator chat channel.
- **FR-003**: Hermes MUST map one valid Pi result to exactly one existing
  generic `HarnessResult` status: `completed`, `failed`, `needs_human`, or
  `stuck`. The generic result MUST retain the existing contract's safe reason,
  next action, retry guidance, and worktree-relative artifact/change data.
- **FR-004**: Hermes MUST verify that the configured Pi runtime is runnable
  inside the Hermes container. A valid `manifest.json` marker without a
  runnable Pi program MUST be treated as unavailable and MUST NOT permit a
  live run.
- **FR-005**: Pi MUST own the full Spec Kit orchestrate playbook. Hermes MUST
  not send or expose separate specify, clarify, plan, tasks, analyze,
  implement, converge, or `PLANNING_COMPLETE` lifecycle operations, and MUST
  not use the removed short path as a fallback.
- **FR-006**: When Pi needs a person, Hermes MUST receive `needs_human`, park
  the task, and prevent further Pi work until the existing human decision flow
  resumes it. Pi MUST NOT chat with the operator.
- **FR-007**: The harness MUST keep writes inside the current task worktree and
  feature branch. It MUST NOT push, merge, open or update a pull request,
  deploy, modify AiNative, modify Hermes control-plane state, or write another
  task's worktree.
- **FR-008**: `load_harness_config` MUST accept `timeout_seconds` as either a
  number or a numeric string, convert accepted values to a numeric timeout,
  and reject missing, blank, zero, negative, non-numeric, or non-finite
  values before Pi starts. A positive finite value, including the checked-in
  1800, MUST be accepted. This feature MUST NOT add a new maximum timeout.
- **FR-009**: A check MUST prove that the checked-in
  `personalAgent/config/default.yaml` loads successfully with its configured
  timeout and active Pi settings.
- **FR-010**: After a human acknowledges a parked legacy short-path record,
  Hermes MUST clear the record's old-path marker while preserving the retained
  task and worktree context. A new Hermes process MUST then be able to start
  the generic harness path.
- **FR-011**: Before acknowledgement of a parked legacy short-path record,
  Hermes MUST NOT start Pi or any replacement run. Acknowledgement MUST NOT
  revive or resume the removed legacy stage machine.
- **FR-012**: The feature MUST keep offline tests on the existing fake Pi
  boundary. Hermes Python MUST NOT import the Pi TypeScript SDK or
  `@mariozechner/pi-coding-agent`, and generic contract data MUST NOT contain
  Pi SDK types, Cursor model slugs, provider secrets, or a Spec Kit stage
  script.
- **FR-013**: The feature MUST reuse the existing `HarnessStartRequest`,
  `HarnessResult`, and `PiHarnessAdapter` boundary. It MUST NOT add a second
  harness, queue, Hermes event channel, task database, or Hermes fork.
- **FR-014**: A successful live Pi result MUST remain only harness/playbook
  completion. Hermes MUST continue to own existing validation and any later
  commit, push, and pull-request workflow.
- **FR-015**: Focused checks MUST cover the live process proof, one-prompt/
  one-result mapping, leftover-process stop after settlement, marker-only
  runtime failure, accepted and rejected timeout forms, default-config
  loading, legacy park/ack/restart behavior, fake-Pi offline execution, and
  contract leakage restrictions.
- **FR-016**: The Docker live-path proof MUST exec the real project Pi program
  with `pi --mode rpc`. Offline pytest MUST keep using the fake Pi and MUST NOT
  require live model credentials. A protocol-only stub in Docker does not
  satisfy the live proof.
- **FR-017**: After Hermes extracts the one structured result from Pi's settled
  run, or when the attempt times out, Hermes MUST end the harness attempt and
  stop a still-running Pi child process so it cannot keep writing.

### Key Entities

- **Pi runtime**: The runnable program and its container-visible execution
  location. A metadata marker describes it but cannot replace it.
- **Harness attempt**: One Hermes start-to-result interaction for one task
  worktree, with one JSON prompt command and one extracted structured result.
- **Generic harness result**: The existing normalized result with one closed
  status, safe diagnostics, and optional worktree-relative outputs.
- **Harness timeout**: The positive execution limit loaded from the checked-in
  configuration and applied before Pi starts.
- **Legacy short-path marker**: Persisted state showing that a task was parked
  because it belonged to the removed Hermes stage machine.
- **Acknowledged restart**: A human-approved transition that clears the
  legacy marker and permits a later Hermes process to begin a fresh generic
  harness attempt.

## Out of Scope

- Reopening or changing the locked product decisions in
  `013-harness-adapter-pi`.
- Cursor Hermes MCP registration or `.cursor/mcp.json` transport choices.
- SQLite WAL errors caused by multiple gateway database writers.
- A second harness implementation, a second task database, a queue, or a
  Hermes-visible live event stream.
- Importing `@mariozechner/pi-coding-agent` or any TypeScript/Pi SDK into
  Hermes Python.
- Rebuilding Telegram, Kanban, GitHub, validation, or the existing publication
  workflow.
- Auto-converting or auto-starting Pi for leftover tasks without human
  acknowledgement.
- Live GitHub publishing as part of the first proof when Pi returns
  `failed`, `needs_human`, or `stuck`.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: In the Docker live-path proof, 100% of valid task starts launch
  one real project `pi --mode rpc` process in the task worktree, send one JSON
  prompt command, privately consume Pi's JSONL run to settlement, extract one
  structured result, produce one matching generic harness result, and leave no
  still-running leftover Pi process.
- **SC-002**: In 100% of marker-only runtime fixtures, Hermes fails visibly
  before execution and never invokes the removed legacy short path.
- **SC-003**: The checked-in default configuration loads successfully in the
  focused configuration check, and 100% of numeric-string, zero, negative,
  missing, and non-numeric timeout fixtures receive the required accept/reject
  outcome before Pi starts.
- **SC-004**: In 100% of legacy restart fixtures, an unacknowledged record
  remains parked without starting Pi, while an acknowledged record starts the
  generic harness path once after process restart and does not re-park because
  of the old marker.
- **SC-005**: In 100% of offline fixture runs, the fake Pi completes without
  live credentials, a TypeScript SDK import, or a second task database.
- **SC-006**: In 100% of contract inspection fixtures, generic request/result
  data contains none of the forbidden Pi SDK types, Cursor model slugs, stage
  scripts, tokens, secrets, or unsafe paths.
- **SC-007**: In 100% of human-needed and timeout fixtures, Hermes parks or
  fails respectively, does not claim completion, and performs no validation
  or publication before the existing rules permit it.
- **SC-008**: The focused test suite and Ruff checks pass without a live
  GitHub account, production repository, or live model credentials.

## Assumptions

- The Pi program can be made available inside the Hermes container by baking
  it into the image or mounting the same container-runnable binary. Either
  satisfies availability. Host-only Pi is insufficient.
- There is no new maximum `timeout_seconds` in this feature. Positive finite
  values are accepted; invalid values are missing, blank, zero, negative,
  non-numeric, or non-finite.
- `pi --mode rpc` is one prompt command followed by a private JSONL response/
  event run. After settlement/result or a timeout, Hermes stops a leftover Pi
  process.
- The Docker live proof uses the real project Pi program. Offline tests keep
  the fake Pi.
- The available Pi program accepts one JSON `prompt` command and emits the
  documented JSONL response/event stream for `pi --mode rpc`; Hermes keeps that
  stream private and extracts one final structured result.
- The current `personalAgent` subset YAML reader may return an unquoted scalar
  such as `1800` as text. Numeric strings are therefore treated as valid
  configuration values after strict validation.
- The existing generic harness contract, task worktree isolation, human
  decision record, validation path, and publication ownership remain
  authoritative from feature 013.
- Acknowledgement means the existing listed human decision that authorizes
  handling the parked leftover task; it does not mean automatic completion.
- The fake Pi is sufficient for offline tests. The first live proof uses a
  controlled runnable Pi process and disposable task/worktree data, not live
  credentials or a production repository.
- Pi's internal Spec Kit prompt and skills remain inside Pi. Hermes receives
  only the generic request/result boundary and safe resume context.
