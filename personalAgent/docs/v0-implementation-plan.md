# Hermes Kanban — Hands-Off V0 Implementation Plan

> **Live path (2026-09-09):** This document is historical. Hermes no longer
> runs Plan → Implement itself. Pi runs the Spec Kit playbook. Hermes owns
> task start, human questions, checks, and the pull request. Old leftover
> work is paused until a person says go. Follow `README.md` and specs
> `013-harness-adapter-pi` / `014-live-harness-gaps`. Do not restore the
> old Hermes stage list.

> **Purpose:** Give an autonomous coding agent everything required to implement the first working vertical slice of the Hermes Kanban architecture.
>
> **Execution mode:** Hands-off. The implementation agent should inspect, implement, test, debug, and iterate without asking the user for routine decisions.
>
> **Human escalation:** Stop and ask the user only when a genuinely consequential architectural/product/security decision cannot be resolved from this document, the existing repositories, or safe local experimentation.

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
AiNative Adapter
    ↓
Plan
    ↓
Implement
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

The system must preserve the existing AiNative methodology rather than replacing it.

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

* global engineering methodology
* reusable agents
* skills
* rules
* workflows
* planning methodology
* implementation methodology
* validation methodology
* reusable engineering knowledge

Hermes must not become the owner of this methodology.

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

At minimum inspect the current four semantic layers and agent roster:

```text
docs/{systems,agents,knowledge,records}/
docs/knowledge/snippets/
docs/records/{debugging,decisions,postmortems,evaluations}/
docs/agents/_skills/
docs/agents/critic/
docs/agents/plan-reviewer/
docs/agents/pr-reviewer/
docs/agents/project-bootstrapper/
docs/agents/scout/
docs/agents/specs-planner/
docs/agents/task-groomer/
docs/agents/tester/
```

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

---

# 8. Existing AiNative Agent Roles

Current reusable roles include:

```text
critic
plan-reviewer
pr-reviewer
project-bootstrapper
scout
specs-planner
task-groomer
tester
```

The existing agent template under `docs/agents/` defines:

```text
agent.md
rule.md
skill.md
```

and associates agents with Cursor commands where applicable.

Preserve this structure.

Do not convert every AiNative agent into Hermes-specific prompts.

---

# 9. AiNative Adapter

Create a small adapter layer between Hermes and AiNative.

Conceptually:

```text
Hermes
   │
   ▼
AiNative Adapter
   │
   ├── discover agents
   ├── load agent definition
   ├── load supporting rules
   ├── load skills
   ├── load workflow instructions
   └── construct execution context
```

The adapter should be responsible for translating:

```text
Hermes worker request
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
execute_agent(...)
```

The exact implementation is up to the agent after inspecting both systems.

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
Agent Executor
      ↓
AiNative Adapter
      ↓
Agent definition
      ↓
Model provider
      ↓
Workspace
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

Implement the core workflow:

```text
PLAN
  ↓
IMPLEMENT
  ↓
VALIDATE
```

The orchestrator controls the workflow.

Agents perform the actual role-specific work.

---

# 22. Planning Phase

For a standard P2 feature:

```text
Task
 ↓
Project discovery
 ↓
Scout/context gathering
 ↓
Specs planner
 ↓
Plan
```

The planner must produce a structured artifact containing:

```text
problem understanding
scope
files/components likely affected
implementation approach
acceptance criteria mapping
validation strategy
risks
open questions
```

If discovery identifies a genuinely consequential architectural/product decision:

```text
pause
→ Telegram
→ human decision
```

Otherwise continue automatically.

---

# 23. No Routine Plan Approval

The user does not want plan approval as a separate mandatory step.

Therefore:

```text
Discovery questions
      ↓
Human answers when required
      ↓
Plan
      ↓
automatic implementation
```

Do not add a plan approval gate.

The only pause should be for unresolved consequential decisions.

---

# 24. Implementation Phase

The builder should receive:

```text
original task
project context
plan
acceptance criteria
workspace
branch
relevant AiNative instructions
```

The builder should:

```text
inspect
implement
test locally where appropriate
review diff
commit
```

Do not allow the builder to push directly.

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
COMPLETED
PR_CREATED
HUMAN_DECISION_REQUIRED
```

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

A task is complete only when:

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

Only then should Hermes transition the task to the completed/PR state.

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
  current_phase: implementation
  current_worker: builder
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

The final automated/integration scenario must demonstrate:

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
AiNative loaded
      ↓
Planner executes
      ↓
Builder executes
      ↓
Tester executes
      ↓
Validation passes
      ↓
Commit
      ↓
Push
      ↓
PR creation
      ↓
Telegram notification
      ↓
Task state updated
```

Record every state transition.

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
  validation:
```

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
```

Use free-form Markdown for human-readable artifacts, but machine-readable execution status must be explicit.

---

# 56. Agent Mapping

Initial mapping should be approximately:

```text
scout
    → discovery/context

specs-planner
    → planning

critic / plan-reviewer
    → optional plan quality/reasoning support

builder
    → implementation
```

If no dedicated builder exists in AiNative yet, create the adapter contract for a builder profile rather than inventing a large new methodology.

```text
tester
    → validation

debugger
    → recovery
```

If a debugger agent does not currently exist, implement recovery around the executor first and add a dedicated AiNative debugger only when justified.

```text
pr-reviewer
    → later human/automated PR review phase

task-groomer
    → task preparation, not V0 execution

project-bootstrapper
    → project onboarding, not standard task execution
```

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
specs.md agents
```

Therefore do not assume that an AiNative `agent.md` is itself an executable process.

The adapter must bridge:

```text
agent definition
→ execution instructions
→ Hermes worker/model
```

rather than attempting to "run Markdown."

---

# 58. Specs.md Compatibility

The existing `specs-planner` workflow uses the specs.md framework.

Investigate exactly how it is currently invoked.

The adapter should preserve compatibility with that workflow where practical.

Do not rewrite specs.md into a Hermes-specific implementation.

If direct execution is impossible from Hermes, create a compatibility wrapper.

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

Implement:

```text
agent executor
model provider adapter
agent context
agent output contract
specs-planner integration
implementation integration
tester integration
```

Use fixture tasks.

---

## Phase 3 — PIV Orchestrator

Implement:

```text
task
 ↓
discovery
 ↓
plan
 ↓
implementation
 ↓
validation
```

Add explicit state transitions.

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

Verify:

```text
container restart
worker interruption
task recovery
workspace recovery
duplicate prevention
```

---

## Phase 8 — Full V0 E2E

Run the complete fixture scenario.

Only declare V0 complete after the entire flow succeeds.

---

# 61. Definition of Done

V0 is complete only when all of the following are true.

## Architecture

* [ ] AiNative remains an external read-only dependency.
* [ ] Project knowledge remains in project repositories.
* [ ] Hermes owns operational state.
* [ ] Hermes Kanban remains the task source of truth.
* [ ] No duplicate task database exists.

## Execution

* [ ] Hermes can discover a project.
* [ ] Hermes can load project context.
* [ ] Hermes can load AiNative.
* [ ] Hermes can identify the AiNative revision.
* [ ] Hermes can create an isolated worktree.
* [ ] Hermes can execute a planner.
* [ ] Hermes can execute implementation.
* [ ] Hermes can execute validation.

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

* [ ] Hermes restart does not corrupt task state.
* [ ] Interrupted execution can recover.
* [ ] Worktrees remain isolated.
* [ ] Duplicate execution is prevented.

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
How agents should work

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
                       AiNative
                          │
                reusable methodology
                          │
                          ▼
                    Agent Adapter
                          │
                          ▼
                 Plan → Build → Test
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

The goal is to make Hermes a reliable operational control plane that can continuously execute the reusable engineering system defined by AiNative across independent project repositories.

The first milestone is deliberately narrow:

```text
ONE TASK
   ↓
ONE PROJECT
   ↓
ONE WORKTREE
   ↓
PLAN
   ↓
IMPLEMENT
   ↓
VALIDATE
   ↓
RECOVER IF NEEDED
   ↓
PR
   ↓
TELEGRAM
```

Make this path extremely reliable before expanding the system.

