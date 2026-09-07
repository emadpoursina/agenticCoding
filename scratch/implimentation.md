# Hermes Kanban — Hands-Off V0 Implementation Plan

> **Purpose:** Give an autonomous coding agent everything required to implement the first working vertical slice of the Hermes Kanban architecture.
>
> **Execution mode:** Hands-off. The implementation agent should inspect, implement, test, debug, and iterate without asking the user for routine decisions.
>
> **Human escalation:** Stop and ask the user only when a genuinely consequential architectural/product/security decision cannot be resolved from this document, the existing repositories, or safe local experimentation.
>
> **Current system (2026-09-07):** Phases 1–8 plus the external-framework planning adapter are delivered in `personalAgent/` and specified in `specs/011-external-framework-planning/`. Live planning no longer uses an AiNative `specs-planner`. It uses one pinned external framework (GitHub Spec Kit) after AiNative `scout`. Building through Spec Kit is the next slice. Prefer those specs over older sections of this scratch file when they conflict.

---

# 1. Mission

Transform the current raw Hermes Docker deployment into the first working version of the Hermes Kanban autonomous software-development control plane.

The first milestone is:

```text
Human Task
    ↓
Hermes
    ↓
Project Registry
    ↓
Project Context
    ↓
Isolated worktree
    ↓
AiNative scout (discovery)
    ↓
Active external framework (Spec Kit) plan + task list
    ↓
PLANNING_COMPLETE (slot freed)
    ↓
[later slice] Implement
    ↓
Validate
    ↓
Debug / Retry if required
    ↓
Commit
    ↓
Push Feature Branch
    ↓
Create PR
    ↓
Telegram Report
    ↓
Human Review
```

The system must preserve AiNative as read-only methodology for the operator’s own agents. It must **not** copy external-framework planners or builders into live AiNative. Planning and later building come from **one** active external framework at a time, plus AiNative agents such as `scout` and `tester`.

---

# 2. Existing Environment

## Hermes

Hermes currently runs in Docker.

Current deployment:

```yaml
services:
  hermes-agent:
    build: .
    image: hermes-agent:local
    container_name: hermes-personal-agent
    tty: true
    stdin_open: true
    ports:
      - "8001:8000"
    volumes:
      - ~/.cache/huggingface:/root/.cache/huggingface
      - ./config:/app/config
    environment:
      - MODEL_NAME=NousResearch/Hermes-2-Pro-Llama-3-8B
      - LOG_LEVEL=INFO
    restart: unless-stopped
```

Hermes is currently mostly a raw installation/configuration.

Telegram is already connected.

Do not rebuild Telegram functionality unnecessarily.

---

# 3. Local Development Environment

AiNative:

```text
/Users/emad/Projects/playground/agenticCoding/AiNative
```

GitHub:

```text
https://github.com/emadpoursina/AiNative
```

Hermes/personal agent project:

```text
/Users/emad/Projects/playground/agenticCoding/personalAgent
```

Each managed software project has its own directory and GitHub repository.

Do not assume that all projects use the same language, framework, build system, or test system.

---

# 4. Architectural Invariants

These are non-negotiable.

## 4.1 AiNative ownership

AiNative owns:

* global engineering methodology for the operator’s own agents
* reusable AiNative agents (live roster may include `scout` and `tester` and omit `specs-planner` / `builder`)
* skills
* rules
* workflows that belong to AiNative
* reusable engineering knowledge

AiNative does **not** have to own the active planning or implementation framework.

Hermes must not become the owner of AiNative methodology.
Hermes must not add framework agents into live AiNative to fill missing planner/builder folders.

---

## 4.2 Project ownership

Each project repository owns:

* source code
* project architecture
* specifications
* project instructions
* project conventions
* technical decisions
* project-specific AI knowledge
* tests
* validation configuration

Hermes must load project-specific context from the project repository.

Do not duplicate entire project knowledge bases into Hermes.

---

## 4.3 Hermes ownership

Hermes owns:

* operational state
* Kanban
* task scheduling
* worker assignment
* workspace lifecycle
* execution state
* retries
* recovery
* notifications
* cross-project operational visibility
* GitHub workflow orchestration
* which **one** external framework is active, and the adapter that runs it
* workflow sequencing across AiNative steps, framework steps, and project validation

---

## 4.4 Human approval boundary

Hermes may automatically:

```text
read
edit
test
build
create worktree
create branch
commit
push feature branch
create PR
debug
retry
```

Hermes must not automatically:

```text
merge PR
deploy
modify production
push protected/main branches
make consequential product decisions
make consequential architectural decisions
```

---

# 5. Hands-Off Agent Rules

The implementation agent is expected to operate autonomously.

It MUST:

1. inspect the existing code before modifying it
2. inspect the current Hermes implementation/version
3. inspect AiNative before designing the adapter
4. prefer existing Hermes capabilities over rebuilding them
5. prefer existing AiNative components over duplicating them
6. run tests after meaningful changes
7. run the complete V0 end-to-end test before declaring success
8. debug failures autonomously
9. document decisions made during implementation
10. leave the system in a reproducible Docker Compose state

It MUST NOT:

* rewrite Hermes unnecessarily
* fork AiNative methodology into a second system
* copy Spec Kit, specs.md, or other framework agents into live AiNative
* run two external frameworks at the same time
* create a custom Kanban database if Hermes already provides the required functionality
* introduce Obsidian into V0
* introduce production deployment
* introduce automatic PR merging
* introduce multi-host distributed execution
* introduce autonomous modification of AiNative methodology
* add unnecessary infrastructure

---

# 6. First Phase: Discovery Before Implementation

Do not start coding immediately.

Create a temporary discovery report.

Inspect:

```text
Hermes Docker image
Hermes source
Hermes configuration
Hermes Kanban implementation
Hermes worker/agent architecture
Hermes task APIs
Hermes persistence
Hermes scheduling
Hermes heartbeat/recovery
Hermes Telegram integration
Hermes tool system
Hermes model configuration
```

Determine exactly:

```text
- How tasks are represented
- How tasks are created
- How tasks are claimed
- How workers are represented
- How workers execute
- How Kanban state persists
- Whether dependencies already exist
- Whether retries already exist
- Whether scheduling already exists
- Whether task history already exists
- Whether multiple boards exist
- How Telegram commands/events work
- How custom tools/skills are registered
- How external commands are executed
```

Do not assume Hermes capabilities from documentation if the installed version behaves differently.

The implementation should adapt to the actual Hermes version.

---

# 7. Inspect AiNative

Inspect the complete relevant AiNative structure.

At minimum inspect:

```text
docs/8. agents/
docs/8. agents/_skills/
docs/8. agents/critic/
docs/8. agents/plan-reviewer/
docs/8. agents/pr-reviewer/
docs/8. agents/project-bootstrapper/
docs/8. agents/scout/
docs/8. agents/tester/
```

Also inspect whatever else is actually present. `specs-planner` / `builder` may be absent in live AiNative; that is expected.

Also discover:

```text
commands
workflows
references
planning
implementation
validation
PIV methodology
project context conventions
task conventions
```

Do not assume the directory structure is exactly as expected. Discover it.

Live AiNative is **not** required to contain `specs-planner` or `builder`. Those names exist in **test fixtures**, not as a requirement of the live methodology tree. Do not create them in live AiNative.

---

# 8. Existing AiNative Agent Roles

The live reusable roles that V0 actually runs from AiNative are:

```text
scout   → discovery
tester  → validation (when the later implement slice resumes PIV)
```

Other documented AiNative roles may exist in the methodology repo:

```text
critic
plan-reviewer
pr-reviewer
project-bootstrapper
task-groomer
```

They are **not** the live planner or builder. Missing `specs-planner` / `builder` in live AiNative is expected.

The existing agent template defines:

```text
AGENTS.md
rule.md
SKILL.md
```

Preserve this structure for AiNative agents.

Do not convert every AiNative agent into Hermes-specific prompts.
Do not copy Spec Kit or specs.md agents into `docs/8-agents/`.

---

# 9. AiNative Adapter

Create a small adapter layer between Hermes and AiNative.

Conceptually:

```text
Hermes
   │
   ▼
AiNative Adapter   (methodology only — not the generic executor)
   │
   ├── discover agents
   ├── load agent definition
   ├── load supporting rules
   ├── load skills
   └── construct execution context
```

The adapter should be responsible for translating:

```text
Hermes worker request for an AiNative role
        ↓
AiNative agent execution contract
```

Do not make Hermes understand the entire AiNative repository structure.

The adapter should expose a stable internal interface such as:

```text
list_agents()
get_agent(name)
resolve_agent_dependencies(name)
build_execution_context(...)
```

`execute_agent` / `execute_role` belong to the executor. The executor calls AiNative **or** the active external-framework adapter depending on the workflow step.

The exact implementation is up to the agent after inspecting both systems.

---

# 9a. External Framework Adapter

**Captured and implemented** in `specs/011-external-framework-planning/` and `personalAgent/` (`external_framework.py`, `speckit.py`).

Conceptually:

```text
Hermes orchestrator
   │
   ▼
External-framework adapter  (one active provider)
   │
   ├── github-spec-kit   (current)
   ├── [future] specs.md / other  (replace, never run two at once)
   └── never AiNativeAdapter as the generic framework adapter
```

Rules:

```text
exactly one active external framework
pinned version in the Hermes image/environment
HERMES_SPECKIT_RUNTIME points at the preinstalled runtime
bootstrap only inside the isolated task worktree
keep Spec Kit native plan/task files (do not invent PLAN.md / TASKS.md as source of truth)
keep bootstrap/setup files in that worktree
use Hermes’s existing model service
reject missing / two-active / unsupported / mismatched runtime before any model call
```

V0 live sequence with Spec Kit selected:

```text
scout (AiNative)
  ↓
Spec Kit plan
  ↓
Spec Kit tasks
  ↓
PLANNING_COMPLETE
  (slot free; no implement, validate, or GitHub publish)
```

---

# 10. AiNative Mounting Strategy

AiNative should be available to Hermes as a **read-only dependency**.

Preferred architecture:

```text
Host
 │
 ├── AiNative
 │
 └── personalAgent
       │
       ▼
     Docker
       │
       └── /ainative:ro
```

Use a read-only mount where practical.

Do not allow worker agents to modify AiNative during V0.

Example conceptual configuration:

```yaml
volumes:
  - /Users/emad/Projects/playground/agenticCoding/AiNative:/ainative:ro
```

However, do not hardcode the host path into the application.

Make it configurable.

---

# 11. AiNative Versioning

The adapter must make the AiNative version visible in execution context.

At minimum capture:

```text
AiNative repository
AiNative commit SHA
AiNative branch/ref
```

This allows later debugging of:

```text
Task execution
    ↓
AiNative version
    ↓
Agent version
    ↓
Result
```

Do not copy AiNative into every task workspace.

---

# 12. Project Registry

Implement a hybrid project registry.

Hermes owns operational project metadata.

Projects own project-specific truth.

Conceptually:

```text
Hermes Project Registry
        │
        ├── project ID
        ├── name
        ├── repository
        ├── local/workspace configuration
        ├── default branch
        ├── enabled/disabled
        └── operational settings
                 │
                 ▼
          Project repository
                 │
                 ├── architecture
                 ├── instructions
                 ├── conventions
                 ├── tests
                 └── project AI knowledge
```

Use a simple configuration-backed registry for V0.

Do not introduce a database unless Hermes' existing persistence architecture requires it.

---

# 13. Project Manifest

If the project repositories do not already have an appropriate project-context file, introduce a minimal standard manifest.

Prefer something like:

```text
.ainative/project.yaml
```

or an existing project-specific convention discovered during inspection.

The manifest may contain:

```yaml
name: example-project
description: ...
repository: github.com/owner/repository
default_branch: main

workflow:
  default: piv

validation:
  commands:
    - ...

development:
  commands:
    - ...

ai:
  context:
    - ...
```

Do not blindly create this exact schema.

First inspect existing project conventions.

If a suitable existing project metadata mechanism exists, reuse it.

---

# 14. Project Context Loading

Before executing a task, Hermes must construct:

```text
Task context
+
Project context
+
AiNative context
+
Workflow context
+
Execution context
```

The execution agent must never operate on a project without first discovering the project's instructions and conventions.

At minimum inspect:

```text
README
AI/agent instructions
project documentation
architecture documentation
contributing instructions
test configuration
build configuration
package/dependency configuration
```

Use project-specific conventions when available.

---

# 15. Workspace Manager

Implement isolated Git worktree support.

Preferred structure:

```text
workspace-root/
    project-a/
        task-123/
            repository/
            worktree/
```

or an equivalent clean structure.

Each task must have:

```text
repository
workspace
branch
task ID
```

Worktree creation should be deterministic.

Example conceptual branch:

```text
feature/task-123
```

or:

```text
feature/<task-id>-<slug>
```

Do not allow unrelated tasks to share mutable worktrees.

---

# 16. Git Safety

The workspace manager must enforce:

```text
never work directly on main/master
never push protected branch
never share worktrees
never reuse dirty worktrees
never overwrite unrelated task changes
```

Before execution:

```text
git status
git branch
git remote
git fetch
base branch validation
```

After execution:

```text
git status
git diff
git branch
```

The implementation should detect and safely handle dirty or invalid worktrees.

---

# 17. SSH GitHub Authentication

GitHub access is SSH-based.

The Docker environment therefore needs controlled access to the required SSH credentials.

Do not copy private keys into images.

Prefer:

```text
host SSH agent
```

or another secure runtime credential forwarding mechanism.

The implementation must test:

```bash
ssh -T git@github.com
git fetch
git push
```

from the actual Hermes execution environment.

Do not consider Git integration complete until this works from the container.

---

# 18. Agent Execution Adapter

Build an execution abstraction:

```text
Hermes Worker
      ↓
Agent Executor / PIV orchestrator
      ↓
      ├── AiNative Adapter (scout, tester, other AiNative roles)
      └── External-framework adapter (Spec Kit plan + tasks; later implement)
      ↓
Model provider (existing Hermes / OpenAI-compatible service)
      ↓
Isolated workspace
```

The executor must provide the agent with:

```text
task
project
workspace
branch
AiNative version
project context
workflow phase
previous phase outputs
validation results
```

The exact mechanism for invoking the model/agent must be based on the actual Hermes extension/tool architecture discovered during Phase 0.

Do not hardcode Cursor as the runtime.

Cursor is only the current human development harness.

---

# 19. Model Provider

The existing model provider is a 9router OpenAPI-compatible model provider.

Do not hardcode model names into individual agents.

Create configuration for:

```text
provider
base URL
API key
planning model
implementation model
validation model
debugging model
```

The provider must be injected through environment/configuration.

Never commit API keys.

---

# 20. Initial Model Routing

V0 should use a simple policy.

```text
Planning
    → stronger reasoning model

Implementation
    → efficient implementation model

Validation
    → independent validation model/agent where practical

Debugging
    → reasoning-capable model
```

Do not build sophisticated dynamic cost optimization yet.

The routing interface should be designed so that better routing can be added later.

---

# 21. PIV Workflow

The orchestrator still owns the long-term workflow:

```text
PLAN
  ↓
IMPLEMENT
  ↓
VALIDATE
```

**Current delivered live slice** stops after plan + task list:

```text
discovery (scout)
  ↓
plan (Spec Kit)
  ↓
tasks (Spec Kit)
  ↓
PLANNING_COMPLETE
```

Do not start implementation, validation, or GitHub publish from this slice.
The later implement slice should consume Spec Kit native artifact paths, not a Hermes `PLAN.md`.

Agents / the active framework perform the role-specific work. Hermes sequences them.

---

# 22. Planning Phase

For a standard P2 feature:

```text
Task
 ↓
Project discovery
 ↓
Scout/context gathering   (AiNative)
 ↓
Spec Kit plan + task list (active external framework)
 ↓
PLANNING_COMPLETE
```

Do **not** look up `specs-planner` in live AiNative.

The planner (Spec Kit) must produce its **native** implementation plan and task list inside the isolated worktree. Hermes records those paths plus provider name, pinned version, and framework revision.

If discovery or the framework identifies a genuinely consequential architectural/product decision:

```text
pause
→ Telegram
→ human decision
```

Otherwise finish the planning slice automatically. Do not wait for plan approval. Do not start building yet.

---

# 23. No Routine Plan Approval

The user does not want plan approval as a separate mandatory step.

Therefore:

```text
Discovery questions
      ↓
Human answers when required
      ↓
Spec Kit plan + tasks
      ↓
PLANNING_COMPLETE (current slice)
      ↓
[later] automatic implementation from native artifacts
```

Do not add a plan approval gate.

The only pause should be for unresolved consequential decisions.

Stopping at `PLANNING_COMPLETE` is **not** a plan-approval gate. It is a slice boundary until Spec Kit implementation is wired.

---

# 24. Implementation Phase

The builder should receive:

```text
original task
project context
native Spec Kit plan path
native Spec Kit task-list path
acceptance criteria
workspace
branch
relevant AiNative instructions when that step is AiNative
```

**Not yet live.** Implementation through the active framework is the next product slice. Until then, do not invent an AiNative `builder` folder and do not auto-run implementation after `PLANNING_COMPLETE`.

When implementation is wired:

```text
inspect
implement
test locally where appropriate
review diff
commit
```

Do not allow the builder/framework implement step to push directly.

The orchestrator owns the GitHub boundary.

---

# 25. Validation Phase

Validation should be independent from implementation where possible.

The validator receives:

```text
task
acceptance criteria
plan
implementation diff
project validation configuration
```

It should determine:

```text
PASS
FAIL
BLOCKED
```

Validation must run the project's real checks.

Do not invent generic test commands when project-specific commands exist.

---

# 26. Failure State Machine

Implement explicit execution states:

```text
QUEUED
RUNNING
BLOCKED
RETRYABLE_FAILURE
FAILED
VALIDATING
PLANNING_COMPLETE
COMPLETED
PR_CREATED
HUMAN_DECISION_REQUIRED
```

`PLANNING_COMPLETE` means Spec Kit plan + task list succeeded, the slot is free, and implementation has not started. It is not PIV-complete and not `PR_CREATED`.

Do not rely solely on free-form text to determine execution state.

---

# 27. Debugging Loop

When validation fails:

```text
VALIDATE
   ↓
FAIL
   ↓
DIAGNOSE
   ↓
DEBUG
   ↓
IMPLEMENT FIX
   ↓
VALIDATE
```

Set a bounded retry limit.

Suggested V0 default:

```text
3 recovery attempts
```

After the limit:

```text
BLOCKED
   ↓
Telegram
   ↓
human
```

The diagnostic report should contain:

```text
task
phase
attempt count
failure
what was attempted
current state
decision required
```

---

# 28. Retry Classification

Every failure should be classified:

```text
TRANSIENT
RETRYABLE
NON_RETRYABLE
HUMAN_DECISION_REQUIRED
```

Examples:

```text
network timeout
dependency install interruption
test failure caused by code
missing environment variable
architectural ambiguity
authentication failure
```

Do not blindly retry all failures.

---

# 29. Task Completion

**Planning slice (delivered):** a planning run is done when:

```text
discovery succeeded
AND
native Spec Kit plan exists in the isolated worktree
AND
native Spec Kit task list exists in the isolated worktree
AND
state is PLANNING_COMPLETE
AND
the single-task slot is free
AND
implementation, validation, and GitHub publish did not run
```

**Full V0 task (later):** a task is complete only when:

```text
implementation exists
AND
validation passes
AND
working tree is clean except intentional artifacts
AND
feature branch exists
AND
commit exists
AND
branch is pushed
AND
PR exists
```

Only then should Hermes transition the task to the completed/PR state. Do not treat `PLANNING_COMPLETE` as that state.

---

# 30. Pull Request Creation

Hermes automatically creates a PR.

PR should include:

```text
Summary
Changes
Validation performed
Known limitations
Task reference
```

PR must target the project's default branch.

Never target a protected branch for direct push.

---

# 31. PR Boundary

Hermes may:

```text
create PR
update PR
push additional feature commits
```

Hermes may not:

```text
merge PR
approve PR as human
deploy
```

Human review remains the final boundary.

---

# 32. Telegram Integration

Telegram already exists.

Extend it with meaningful events rather than logging every internal operation.

Notify on:

```text
task started
human decision required
blocked
validation failed after recovery
major recovery event
PR created
unexpected failure
```

Avoid:

```text
"reading file..."
"running command..."
"thinking..."
```

---

# 33. Telegram Commands

Implement useful status commands if Hermes' Telegram architecture supports them cleanly.

Examples:

```text
/status
/projects
/tasks
/blockers
/prs
/status project-a
```

Natural-language equivalents should also work if Hermes already supports conversational commands.

---

# 34. Human Decision Protocol

When the agent genuinely requires a human decision, Hermes should produce:

```text
PROJECT
TASK
CURRENT PHASE
DECISION REQUIRED
WHY IT MATTERS
OPTIONS
RECOMMENDED OPTION
CONSEQUENCE OF EACH OPTION
```

Example:

```text
Project: Project A
Task: #123
Phase: Planning

Decision required:
Should this API remain backwards compatible?

A: Preserve compatibility
B: Introduce breaking change

Recommendation:
A

Reason:
Existing clients cannot be migrated atomically.

Reply with:
A / B
```

After receiving the answer, resume execution automatically.

---

# 35. V0 Scheduling

Do not implement concurrent execution in V0.

Use:

```text
one active task
```

Scheduling order:

```text
1. dependency-ready tasks
2. highest priority
3. oldest/earliest-created task
```

Priority:

```text
P0
P1
P2
P3
```

This gives deterministic behavior while leaving room for future capacity-aware scheduling.

---

# 36. Hermes Kanban Integration

Use Hermes native Kanban as the operational task source of truth.

Do not create a second task database.

If Hermes Kanban already supports:

```text
dependencies
assignment
heartbeat
recovery
history
```

reuse those capabilities.

Only build adapters/extensions where necessary.

---

# 37. Task Contract

Preserve the human-readable task format:

```md
## Problem
What is happening?

---

## Expected Result
What should happen?

---

## Platform
- Backend
- Desktop
- Android
- iOS
- Website

---

## Acceptance Criteria
- [ ]

---

## Technical Notes
Optional.

---

## Dependencies
Optional.
```

Also preserve:

```text
Owner
Reviewer
Priority
```

Do not pollute the task with constantly changing execution details.

Execution state belongs to Hermes.

---

# 38. Execution State

Execution state should track:

```yaml
execution:
  state: running
  workflow: piv
  current_phase: planning
  current_worker: github-spec-kit
  attempt: 1

workspace:
  repository: project-a
  path: ...
  branch: feature/task-123

validation:
  status: pending

blockers: []

next_action: validate

pull_request: null
```

Use Hermes-native state mechanisms where possible.

Only add custom state fields where Hermes does not provide an appropriate representation.

---

# 39. Project Status

Implement a project status abstraction capable of answering:

```text
What is happening?
What is blocked?
What is running?
What PRs are waiting?
What needs a decision?
What happened recently?
What happens next?
```

Do not continuously rescan every repository to answer these questions.

Use Hermes operational state plus targeted project inspection.

---

# 40. Learning System

V0 should implement learning as:

```text
execution
   ↓
retrospective
   ↓
lesson classification
   ↓
proposal
```

Classify lessons as:

```text
PROJECT_SPECIFIC
GLOBAL_AINATIVE
TRANSIENT
```

Project-specific lessons should generate proposed project documentation changes.

Global lessons should generate proposed AiNative changes.

Transient lessons remain execution history.

---

# 41. No Autonomous AiNative Modification

V0 must never automatically modify AiNative methodology.

Instead:

```text
execution
 ↓
lesson
 ↓
AiNative improvement proposal
 ↓
human review
 ↓
future AiNative PR
```

The same principle applies to project-specific knowledge when changing it would materially alter project behavior.

---

# 42. Obsidian

Do not implement Obsidian integration in V0.

Hermes Kanban remains authoritative.

Obsidian may be added later as a visualization/UI layer.

---

# 43. Security

Apply least privilege.

Never:

```text
commit secrets
copy SSH private keys into images
store API keys in Git
allow workers to modify AiNative
allow arbitrary main branch pushes
allow automatic merge
allow automatic deployment
```

Configuration and credentials must come from:

```text
environment
Docker secrets
mounted runtime configuration
SSH agent
```

where appropriate.

---

# 44. Docker Architecture

Keep the system Docker-first.

Target:

```text
Docker Compose
│
├── hermes-agent
│
├── Hermes persistence
│
└── supporting services only where required
```

Mount:

```text
AiNative → read-only
project/workspace root → writable
configuration → writable/configurable
credentials → secure runtime mechanism
pinned Spec Kit runtime → read-only (HERMES_SPECKIT_RUNTIME)
```

Do not add infrastructure unless required.

---

# 45. Workspace Mounting

The Docker container needs access to task workspaces.

Design this around a configurable:

```text
WORKSPACE_ROOT
```

Example:

```text
/workspaces
```

Do not hardcode:

```text
/Users/emad/...
```

inside the application.

The host-specific mapping belongs in Docker Compose/environment configuration.

---

# 46. V0 Test Project

The user has not selected the V0 project yet.

Therefore the implementation agent must:

1. finish the platform implementation first
2. verify the system using a disposable local fixture repository if necessary
3. make the V0 project configurable
4. ask the user for a real non-critical project only when actual end-to-end GitHub execution is required

The system must not silently choose a real production repository.

---

# 47. Test Fixture

Create a small disposable Git repository for automated integration testing.

The fixture should contain a trivial feature task that requires:

```text
small code change
test change
validation
commit
branch
PR simulation where possible
```

Use it to validate:

```text
workspace creation
agent execution
validation
failure recovery
Git operations
state transitions
```

Do not depend entirely on a real project to test the orchestration platform.

---

# 48. Failure Injection

The test suite must deliberately simulate at least:

```text
validation failure
retryable command failure
worker interruption
dirty worktree
missing project configuration
missing credentials
```

The purpose is to verify recovery rather than only happy-path execution.

---

# 49. End-to-End V0 Test

The final automated/integration scenario for **full** V0 must still demonstrate the later implement slice. Until then, the live automated scenario is:

```text
Task enters Kanban
      ↓
Hermes claims task
      ↓
Project discovered
      ↓
Workspace created
      ↓
Feature branch created
      ↓
AiNative scout
      ↓
Spec Kit bootstrapped in worktree if needed
      ↓
Spec Kit plan + task list
      ↓
PLANNING_COMPLETE
      ↓
Slot free for another task
```

The older full chain (builder → tester → push → PR → Telegram) remains the **later** target, using Spec Kit implement rather than an AiNative builder.

---

# 50. Interrupted Execution Test

Kill/restart the Hermes container during an active task.

Verify that:

```text
task state is recoverable
workspace is discoverable
branch is recoverable
worker does not create duplicate execution
task can resume or safely restart
```

This is an important V0 reliability requirement.

---

# 51. Repository Structure

The exact structure should follow the existing Hermes project after inspection.

A conceptual target is:

```text
personalAgent/
│
├── docker-compose.yml
├── Dockerfile
├── config/
│
├── hermes/
│   ├── adapters/
│   │   └── ainative/
│   ├── orchestration/
│   ├── projects/
│   ├── workspaces/
│   ├── scheduling/
│   ├── workflows/
│   ├── execution/
│   ├── recovery/
│   ├── github/
│   └── notifications/
│
├── tests/
│   ├── unit/
│   ├── integration/
│   └── e2e/
│
└── docs/
```

Do not force this exact tree if Hermes already has a strong extension architecture.

Adapt to the existing codebase.

---

# 52. Configuration

Configuration should be externalized.

Conceptually:

```yaml
ainative:
  path: /ainative
  read_only: true

workspace:
  root: /workspaces

github:
  auth: ssh
  allow_push: true
  allow_pr: true
  allow_merge: false

execution:
  max_retries: 3
  max_concurrent_tasks: 1

workflow:
  default: piv

external_framework:
  providers:
    - id: github-spec-kit
      version: 1.0.1
      active: true
  runtime:
    path_env: HERMES_SPECKIT_RUNTIME

learning:
  enabled: true
  auto_modify_ainative: false

notifications:
  telegram:
    enabled: true
```

Adapt to Hermes' existing configuration system.

---

# 53. Observability

Every task execution should have a correlation identity:

```text
task_id
execution_id
project_id
workspace_id
worker_id
```

Logs should allow reconstructing:

```text
what happened
when
for which task
in which workspace
with which agent
using which AiNative revision
```

Avoid dumping model reasoning into operational logs.

Log actions/results, not private chain-of-thought.

---

# 54. Agent Context Contract

Every worker should receive a predictable context.

Minimum:

```yaml
task:
  id:
  title:
  description:
  acceptance_criteria:
  priority:

project:
  id:
  name:
  repository:
  default_branch:

workspace:
  path:
  branch:

ainative:
  path:
  revision:

workflow:
  name:
  phase:

previous_outputs:
  plan:
  tasks:
  validation:
```

For Spec Kit, `plan` and `tasks` are native file paths in the worktree, not Hermes `PLAN.md` / `TASKS.md`.

This should be implemented through the adapter/executor rather than duplicated manually in every agent.

---

# 55. Agent Output Contract

Where practical, agent outputs should be structured.

Example:

```yaml
status: success

summary: ...

artifacts:
  - path: ...

validation:
  status: passed

next_action: validate

questions: []

provider:
  name: github-spec-kit
  version: ...
  revision: ...
```

Use free-form Markdown for human-readable artifacts, but machine-readable execution status must be explicit.

---

# 56. Agent / Provider Mapping

Initial mapping:

```text
scout (AiNative)
    → discovery/context

github-spec-kit (active external framework)
    → planning
    → task-list generation
    → [later] implementation

tester (AiNative or project validation commands)
    → validation
```

Do **not** map live planning to AiNative `specs-planner`.
Do **not** add `builder` to live AiNative. Implementation is a later Spec Kit lifecycle step (or a future replacement framework), not a methodology folder.

Optional AiNative-only roles remain out of the standard V0 execution path:

```text
critic / plan-reviewer
pr-reviewer
task-groomer
project-bootstrapper
```

If a debugger agent does not currently exist, implement recovery around the executor first.

Never configure two external frameworks as active at once. Replacing Spec Kit later means switching the one active provider, not combining Spec Kit with specs.md.

---

# 57. Important Current-State Constraint

The current AiNative agents are primarily documentation/instruction based.

Current human usage involves:

```text
Cursor
+
Cursor commands
+
symlinked AiNative references
+
one external framework at a time (Spec Kit in Hermes; Cursor Spec Kit skills in this repo)
```

Therefore do not assume that an AiNative `AGENTS.md` is itself an executable process.

The adapter must bridge:

```text
agent definition or framework lifecycle step
→ execution instructions
→ Hermes worker/model
```

rather than attempting to "run Markdown."

---

# 58. External Framework Compatibility

**Do not** install specs.md into the control plane or copy it into AiNative.

The live planner is GitHub Spec Kit, pinned in the Hermes environment.

If a better framework appears later:

```text
deactivate Spec Kit
activate the new provider
keep AiNative agents
```

Multiple adapters may exist in code. Only one external framework may be selected at runtime.

Do not rewrite Spec Kit into a Hermes-specific planning language. Pass native artifacts through.

If the project is not Spec Kit-enabled, bootstrap inside the isolated worktree only and keep those setup files with the plan and tasks.

---

# 59. Cursor Independence

The final architecture must not depend on Cursor.

Current Cursor commands are a development convenience.

Long-term:

```text
AiNative
   │
   ├── Cursor harness
   ├── Hermes harness
   └── future harnesses
```

The Hermes adapter should consume AiNative methodology without requiring Cursor to be running.

---

# 60. Phase Ordering

Implement in this exact broad order.

## Phase 0 — Discovery

```text
inspect Hermes
inspect Kanban
inspect persistence
inspect workers
inspect Telegram
inspect AiNative
inspect existing execution workflows
write discovery report
```

Do not modify architecture before this phase is complete.

---

## Phase 1 — Foundation

Implement:

```text
configuration
AiNative read-only mount
AiNative adapter
project registry
workspace manager
Git safety
execution identity
```

Test each independently.

---

## Phase 2 — Agent Execution

**Implemented.** Executor + model seam exist. Planning integration is the Spec Kit adapter (`specs/011-external-framework-planning/`), not `specs-planner` in live AiNative. Implementation integration is **not** in this slice.

```text
agent executor
model provider adapter
agent context
agent output contract
Spec Kit plan + tasks adapter
tester integration (existing)
```

Use fixture tasks. Focused checks: `personalAgent/tests/test_external_framework_planning.py`.

---

## Phase 3 — PIV Orchestrator

**Implemented, then narrowed for live planning.** The orchestrator still knows the full PIV chain. With Spec Kit selected, a live start currently does:

```text
task
 ↓
discovery (scout)
 ↓
plan (Spec Kit)
 ↓
tasks (Spec Kit)
 ↓
PLANNING_COMPLETE
```

Do not auto-continue to implementation until the next slice.

---

## Phase 4 — Recovery

Implement:

```text
validation failure
 ↓
diagnosis
 ↓
debug
 ↓
retry
```

Add:

```text
retry limits
failure classification
blocked state
human escalation
```

---

## Phase 5 — GitHub

Implement:

```text
branch
 ↓
commit
 ↓
push
 ↓
PR
```

Verify SSH from inside Docker.

---

## Phase 6 — Telegram

Connect meaningful orchestration events to the existing Telegram integration.

Do not duplicate the existing Telegram transport.

---

## Phase 7 — Persistence / Restart Recovery

**Captured** in Spec Kit `specs/009-restart-recovery/` (`spec.md`, `plan.md`, `research.md`, `data-model.md`, `contracts/restart-recovery.md`, `quickstart.md`, `tasks.md`). Implement from those artifacts, not from this outline alone.

**Implemented** (converge 2026-09-02): T001–T033 done. Atomic `overlay.json` + 60s `alive` under `execution.overlay_dir`; `become_ready()` reclaims one interrupted run; `recover_workspace` (dirty OK, no fetch); `SlotHeldError` vs `WorkflowBusyError`. Contract: `personalAgent/tests/test_restart_recovery.py`. Live Docker kill remains Phase 8.

Verify:

```text
container restart
worker interruption
task recovery
workspace recovery
duplicate prevention
```

Decided contract (pytest, not live Docker kill):

```text
execution.overlay_dir → overlay.json (atomic os.replace) + alive (60s silence = dead)
become_ready() at start-up, before any new start; no Resume press
reclaim grain = whole phase (resume next if complete; else safe-restart once)
same execution_id / workspace_id; recover_workspace not prepare_workspace
no git fetch; dirty copy of this task is allowed; missing copy+branch → BLOCKED
fresh alive → SlotHeldError (second copy must refuse)
occupied slot → WorkflowBusyError
crash does not bump Phase 4 attempt or open a second PR
no second task store; no new Telegram kind
```

---

## Phase 8 — Full V0 E2E

**Captured** as a pytest fixture path (not a new product feature): `personalAgent/tests/test_v0_e2e.py`.

**Implemented** (2026-09-02): one disposable fixture task can still exercise board → discover → plan → implement → validate → simulated push/PR → Telegram on **fixture methodology that includes planner/builder names**. That is not the live AiNative roster.

**Live path after 011:** board → discover (`scout`) → Spec Kit plan/tasks → `PLANNING_COMPLETE`. No implement/PR on that path yet.

Live `docker compose restart`, github.com SSH, and a real Telegram chat remain operator proof, not the offline fixture gate.

Run the complete fixture scenario for the slice under test.

Do not declare full V0 complete until Spec Kit implementation, validation, and PR work again on the live (scout-only) methodology.

---

## Phase 9 — Spec Kit implementation (next)

Do not copy a builder into AiNative.

Wire the already-stable external-framework contract for Spec Kit **implement** (and then existing validation + GitHub publish), consuming native plan/task paths left in the isolated worktree.

Keep:

```text
one active framework
isolated worktree only
builder-never-publish
PLANNING_COMPLETE is not PIV-complete
```

---

# 61. Definition of Done

V0 is complete only when all of the following are true.

## Architecture

* [x] AiNative remains an external read-only dependency.
* [x] Project knowledge remains in project repositories.
* [x] Hermes owns operational state.
* [x] Hermes Kanban remains the task source of truth.
* [x] No duplicate task database exists.
* [x] Exactly one external framework is active (GitHub Spec Kit).
* [x] Live AiNative is not required to contain `specs-planner` or `builder`.

## Execution

* [x] Hermes can discover a project.
* [x] Hermes can load project context.
* [x] Hermes can load AiNative.
* [x] Hermes can identify the AiNative revision.
* [x] Hermes can create an isolated worktree.
* [x] Hermes can execute planning via the active Spec Kit adapter (after scout).
* [ ] Hermes can execute implementation via the active framework (Phase 9).
* [x] Hermes can execute validation (fixture / existing tester path; not on the live planning-complete path).

## Recovery

* [ ] Validation failures are detected.
* [ ] Retryable failures are retried.
* [ ] Debugging can modify the workspace.
* [ ] Retry count is bounded.
* [ ] Repeated failure produces a blocked state.
* [ ] Human escalation works.

## GitHub

* [ ] SSH works inside Docker.
* [ ] Feature branches are created safely.
* [ ] Commits are created.
* [ ] Feature branches can be pushed.
* [ ] PRs can be created.
* [ ] Merge is impossible through the autonomous V0 workflow.

## Telegram

* [ ] Task-start event works.
* [ ] Human-decision event works.
* [ ] Blocked event works.
* [ ] Validation/recovery failure event works.
* [ ] PR-created event works.

## Reliability

* [x] Hermes restart does not corrupt task state.
* [x] Interrupted execution can recover.
* [x] Worktrees remain isolated.
* [x] Duplicate execution is prevented.

## Learning

* [ ] Execution lessons can be captured.
* [ ] Lessons are classified.
* [ ] AiNative changes become proposals only.
* [ ] No autonomous AiNative methodology modification occurs.

---

# 62. Human Escalation Rules

The implementation agent may make decisions autonomously when they are:

```text
implementation details
file organization
class/function naming
internal interfaces
test structure
logging structure
configuration naming
Docker implementation details
retry implementation
adapter implementation
```

It must ask the user only when the decision changes:

```text
architecture invariants
security boundary
GitHub permissions
production behavior
merge/deployment authority
fundamental project behavior
fundamental AiNative methodology
irreversible external behavior
```

If multiple technically equivalent implementation choices exist, choose one and document it.

Do not ask the user merely because something was not explicitly specified.

---

# 63. Stop Conditions

The implementation agent should stop and report only when:

### Success

```text
V0 definition of done is satisfied.
```

### Human decision

```text
A consequential unresolved decision is genuinely required.
```

### Safety

```text
Continuing would risk data loss,
production changes,
credential exposure,
protected branch modification,
or another high-impact action.
```

### External blocker

```text
Required external access/credential/service is unavailable
and cannot be safely mocked or locally validated.
```

Everything else should be investigated and resolved autonomously.

---

# 64. Final Report Required From Implementation Agent

When finished, produce:

```text
## Implementation Summary

## Architecture Implemented

## Files Added/Changed

## Hermes Capabilities Discovered

## AiNative Integration

## Project Registry

## Workspace Strategy

## Agent Execution

## PIV Workflow

## Recovery

## GitHub Integration

## Telegram Integration

## Tests Executed

## End-to-End Result

## Known Limitations

## Decisions Made Autonomously

## Human Decisions Still Required

## How To Run The System
```

Include exact commands needed to:

```text
start
stop
restart
run tests
inspect logs
run V0
```

---

# 65. Future Phases — Do Not Implement Yet

After V0 works:

## Phase 2

```text
advanced failure recovery
```

## Phase 3

```text
multi-project registry
concurrent workers
capacity-aware scheduling
cross-project status
```

## Phase 4

```text
Telegram operations interface
daily reports
decision workflows
PR summaries
```

## Phase 5

```text
learning
retrospectives
AiNative improvement proposals
evaluation metrics
```

## Phase 6

```text
advanced autonomy
dynamic model routing
task prioritization
cross-project optimization
```

Do not implement these early.

---

# 66. Core Mental Model

The implementation must preserve this separation:

```text
AiNative
    =
How the operator’s own agents should work

Active external framework (Spec Kit today)
    =
How planning (and later building) is performed

Project
    =
What this project is

Task
    =
What needs to be done

Hermes
    =
What is happening and what should happen next
```

The final system should allow the user to communicate primarily:

```text
goals
decisions
priorities
```

while Hermes handles:

```text
discovery
planning
implementation
validation
debugging
workspace management
Git
GitHub
notifications
execution state
recovery
```

while maintaining the human boundary around:

```text
architecture decisions
product decisions
merge
deployment
production
```

---

# 67. Final Target

The implementation should result in:

```text
                         YOU
                          │
                   goals / decisions
                          │
                          ▼
                    ┌───────────┐
                    │  HERMES   │
                    │           │
                    │ control   │
                    │ plane     │
                    └─────┬─────┘
                          │
                    Hermes Kanban
                          │
             ┌────────────┼────────────┐
             ▼            ▼            ▼
         Project A    Project B    Project C
             │            │            │
             ▼            ▼            ▼
       Project context / project truth
             │
             └────────────┬────────────┘
                          │
              ┌───────────┴───────────┐
              ▼                       ▼
          AiNative              Spec Kit
     (scout / tester /        (plan + tasks;
      operator agents)         later implement)
              │                       │
              └───────────┬───────────┘
                          ▼
                 Hermes adapters
                          │
                          ▼
          Discover → Plan/Tasks → [later Build → Test]
                          │
                    Debug / Recover
                          │
                          ▼
                         PR
                          │
                          ▼
                    HUMAN REVIEW
                          │
                    Merge / Deploy
```

The goal is **not** to make Hermes contain all intelligence.

The goal is to make Hermes a reliable operational control plane that runs **one** external framework plus AiNative agents across independent project repositories.

The **current** live milestone:

```text
ONE TASK
   ↓
ONE PROJECT
   ↓
ONE WORKTREE
   ↓
SCOUT
   ↓
SPEC KIT PLAN + TASKS
   ↓
PLANNING_COMPLETE
```

The **remaining** V0 milestone (Phase 9, then existing GitHub/Telegram):

```text
IMPLEMENT (Spec Kit)
   ↓
VALIDATE
   ↓
RECOVER IF NEEDED
   ↓
PR
   ↓
TELEGRAM
```

Make the current planning path extremely reliable, then extend the same adapter into implement. Do not put framework agents into AiNative.

