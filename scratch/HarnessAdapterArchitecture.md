# Harness Adapter Architecture

## Objective

Refactor Hermes so that **Hermes is an orchestration layer, not an agent execution engine**.

The immediate goal is to introduce a generic **Harness Adapter architecture** and use **Pi SDK as the first execution harness**.

The architecture must allow the execution harness to be replaced later without requiring changes to Hermes' orchestration logic.

The first proof is: Hermes starts one Pi run for a real task; Pi follows the full Spec Kit orchestrate playbook; Hermes then uses the existing validation and pull-request workflow.

---

# Locked decisions

These decisions are settled for this next step:

1. **Pi runs the full Spec Kit pipeline**, matching the global Cursor skill `speckit-orchestrate`:
   specify → clarify (questions return to a human) → one continue confirmation → plan → tasks → analyze when needed → implement ↔ converge until done or stuck.
2. **Remove the Hermes short path.** Hermes must not own or sequence `scout → Spec Kit plan → tasks → PLANNING_COMPLETE → implement`.
3. **The Spec Kit orchestrate playbook lives in Pi**, not as a Hermes command. Hermes only starts work on a task.
4. **Do not copy Cursor wiring** (Cursor Task workers, Cursor model slugs, Cursor parent-session tricks). Copy the **stage order and stop rules** only.
5. **Human moments stay in Hermes:** skip/clarify questions, the one continue confirmation, parking, and stop-after-three-failures.
6. **Pi must not chat with the operator.** If it needs a person, it stops and returns questions to Hermes.
7. **Existing project checks and Git/PR stay in Hermes.** Pi saying “I finished” is not the same as the work being good.

---

# 1. Architectural Principle

Hermes owns **orchestration**.

The selected harness owns **execution**.

Spec Kit is a **framework** (the working method). Pi is a **harness** (the agent loop that follows that method).

```text
                         HERMES
                    Orchestration Layer
                           │
                  Harness Execution Contract
                           │
             ┌─────────────┼─────────────┐
             ▼             ▼             ▼
         Pi Adapter    Future Adapter   Future Adapter
             │
             ▼
          Pi SDK
             │
             ▼
      Agent Execution Loop
             │
       ┌─────┼─────┐
       ▼     ▼     ▼
     Model  Tools  Spec Kit orchestrate playbook
```

Hermes must not reproduce the execution loop implemented by the harness.

Hermes must not reproduce Spec Kit stage sequencing.

---

# 2. Responsibilities

## Hermes

Hermes remains responsible for:

* Task selection
* Task lifecycle/state
* Workspace/worktree management
* Git branch management
* Selecting the harness
* Preparing the work folder and limits
* Starting **one** harness execution per work attempt
* Thin monitoring (started / running / finished / needs-human)
* Receiving normalized execution results
* Human approval boundaries (questions, continue, park, escalate)
* Bounded retry/recovery of **whole harness runs** (not Spec Kit stages)
* Validation orchestration (existing project checks)
* Commit/push/PR workflow

Hermes should know **what needs to happen**, but not **how Spec Kit or Pi perform the work**.

Hermes must **not** remain responsible for:

* Spec Kit specify / clarify / plan / tasks / analyze / implement / converge
* AiNative `scout` as a required step before Spec Kit
* `PLANNING_COMPLETE` as a Hermes-owned Spec Kit checkpoint
* Calling plan, then tasks, then implement as separate framework steps
* A `/speckit-orchestrate` command inside Hermes

## Harness (Pi, first implementation)

A harness is responsible for:

* Agent execution loop
* Model and stopping conditions
* Harness-specific configuration and execution state
* The Spec Kit orchestrate playbook (command lives here)
* Writing native Spec Kit files into the task worktree as it goes
* Returning compact status when a stage succeeds, is stuck, is blocked, or needs a human

The harness decides **how the agent performs the work**.

---

# 3. Where the command lives

```text
Hermes:  "work this task"   (start / stop / human / checks / PR)
                │
                ▼
         Harness contract
                │
                ▼
Pi:  speckit-orchestrate playbook
     specify → clarify-return → plan → tasks → analyze? → implement ↔ converge
```

The playbook is the same idea as `~/.cursor/skills/speckit-orchestrate/SKILL.md`.

Reuse from that skill:

* Stage order
* Clarify as the human Q&A gate (not silent specify tables)
* `skip` means self-answer specify/clarify, show a choice report, then one continue confirmation
* Analyze only when the plan says it is needed
* Implement and converge take turns until converged, or stop if blocked
* Three failures on the same stuck point, then stop for a human
* Compact reports (`STATUS`, `IMPLEMENT_STATUS`, `CONVERGE_OUTCOME`)

Do not reuse from that skill:

* Cursor `Task` / `generalPurpose`
* Cursor model slugs
* “Parent must not read skill files” as a Cursor-session rule
* Any assumption that the operator is sitting in a Cursor chat

Pi maps those rules onto Pi’s own agent, tools, and models.

---

# 4. Harness Execution Contract

The contract is framework-stage-agnostic. Hermes does **not** pass `plan` / `tasks` / `implement` as Hermes lifecycle steps.

### Start execution

The request should contain:

* Task identity
* Task description
* Workspace location (isolated worktree only)
* Repository/project context
* Playbook identity (first implementation: Spec Kit orchestrate)
* Model/provider configuration **reference** (not a Pi-specific client)
* Execution constraints: this folder only, no push, no protected/default branch, timeout
* Optional operator flags (for example `skip`)
* Optional resume context (prior questions answered, diagnostic notes)

Do not put a script of Spec Kit stages or an agent loop into the request.

### Report execution

The result should communicate:

* `completed` | `failed` | `needs_human` | `stuck`
* Exit/reason
* Native Spec Kit artifact paths written under the worktree (when present)
* Changes produced (worktree-relative)
* Logs/output reference
* Whether a whole-run retry is reasonable
* Questions / next action when `needs_human`
* Harness diagnostics without Pi SDK types leaking through

Hermes treats `completed` as “the harness finished its playbook,” not as “publish now.”

---

# 5. Adapter Boundary

```text
                    Hermes
                      │
              Generic execution
                      │
                      ▼
              Harness Adapter
                      │
            Pi-specific translation
                      │
                      ▼
                   Pi SDK
                      │
            Spec Kit orchestrate playbook
```

Hermes talks only to the generic contract.

A later harness is a new adapter plus that harness’s own playbook mapping. Do not change Hermes orchestration to add one.

---

# 6. Separation: Hermes vs framework vs harness

Do not confuse the three:

| Layer | Owns |
| --- | --- |
| Hermes | Task, folder, git safety, humans, checks, PR |
| Spec Kit | How to specify, plan, task-split, implement, converge |
| Pi | Agent loop, tools, models, running the Spec Kit playbook |

Hermes must not assume:

* Spec Kit stages are Hermes workflow columns
* Pi is the only possible harness
* A particular planner/builder agent exists in AiNative
* A particular model vendor is required

The first Pi implementation **does** use Spec Kit as its playbook. That is a Pi configuration choice, not a Hermes stage machine.

---

# 7. Target workflow

```text
                    Task
                     │
                     ▼
                  Hermes
                     │
              Select task
                     │
              Prepare workspace
                     │
              Start harness (one run)
                     │
                     ▼
          Harness Execution Contract
                     │
                     ▼
                  Pi Adapter
                     │
                     ▼
                  Pi SDK
                     │
           Spec Kit orchestrate
           (full pipeline in Pi)
                     │
          ┌──────────┴──────────┐
          ▼                     ▼
    needs_human / stuck      playbook finished
          │                     │
          ▼                     ▼
    Hermes parks / asks     Hermes validates
    operator                (existing checks)
                             │
                    ┌────────┴────────┐
                    ▼                 ▼
                 Failed            Passed
                     │                 │
                Recovery            Git/PR
                (new harness
                 run, not a
                 Hermes Spec Kit
                 stage)
```

Removed from Hermes:

```text
Hermes → scout → Spec Kit plan → tasks → PLANNING_COMPLETE → implement
```

That path must not remain as a fallback beside Pi.

---

# 8. State Model

Hermes is the source of truth for **orchestration state**.

```text
Hermes State
────────────
TASK_SELECTED
WORKSPACE_READY
EXECUTION_STARTED
EXECUTION_RUNNING
NEEDS_HUMAN
EXECUTION_FINISHED
VALIDATION
PUBLISHING
COMPLETED
FAILED
```

Do **not** add Hermes states for specify, plan, tasks, implement, or converge.

Do **not** keep `PLANNING_COMPLETE` as a Hermes-owned success/checkpoint that means “Spec Kit planning finished, Hermes will call implement later.”

Pi may keep internal Spec Kit step state. Hermes only sees normalized results/events:

```text
Harness:
    running
    progress
    needs_human
    completed
    failed
    stuck
```

Pi should still write native Spec Kit files (`spec.md`, `plan.md`, `tasks.md`, and related files) into the worktree as it goes, so a crash is inspectable. That is disk output, not Hermes workflow columns.

---

# 9. Failure, humans, and recovery

Recovery remains an orchestration responsibility **at run granularity**.

```text
Hermes
  │
  ▼
One harness execution (full Spec Kit playbook)
  │
  ▼
needs_human / stuck / failed / completed
  │
  ▼
Hermes
  ├── ask operator (clarify / continue / skip report)
  ├── resume harness with answers
  ├── retry or restart the whole run (bounded)
  ├── run existing validation-failure recovery
  └── escalate to human
```

Stuck policy (from the Cursor skill, mapped to Hermes):

* Retry the same harness run up to three attempts on a recoverable stuck point.
* After the third attempt, park and ask the operator.
* Do not fall back to the old Hermes Spec Kit short path.

Validation failure after a completed playbook still uses the existing Hermes check/recovery/publish rules. A worktree fix is another harness start with diagnostic context, not Hermes calling `implement` itself.

---

# 10. Safety

Pi will use tools (edit files, run commands). The contract must force:

* Writes only inside the current task worktree
* Feature branch only; no protected/default branch
* No push, merge, or pull request from the harness
* Stop on timeout
* No secrets in returned metadata

---

# 11. Model Independence

Do not couple the generic adapter to a specific model.

```text
Hermes
   │
   ▼
Harness
   │
   ├── Model Provider
   ├── Model
   ├── Tools
   ├── Spec Kit playbook
   └── Execution Loop
```

Hermes may pass a named model profile. The Pi adapter maps that onto Pi. Cursor model slugs from `speckit-orchestrate` are not Hermes config.

Later evaluation should be able to compare `Pi + Model A/B/C` without changing Hermes orchestration.

---

# 12. Future harnesses

```text
                    Hermes
                    Orchestration
                          │
              Harness Execution Contract
                          │
        ┌─────────────────┼─────────────────┐
        ▼                 ▼                 ▼
    Pi Adapter       Harness B          Harness C
```

Adding a harness means: implement a new adapter.

It does **not** mean teaching Hermes a second Spec Kit stage machine.

Do not optimize the contract for hypothetical harnesses beyond a clean start/result boundary.

---

# 13. Architectural Constraints

1. **Hermes is not the execution engine.**
2. **Hermes must not implement a duplicate agent loop.**
3. **Hermes must not sequence Spec Kit stages.**
4. **Hermes must not keep the short Spec Kit path as a fallback.**
5. **The Spec Kit orchestrate command lives in Pi.**
6. **Hermes must not depend directly on Pi SDK internals.**
7. **The generic execution contract must not contain Pi-specific or Cursor-specific concepts.**
8. **Pi must be replaceable.**
9. **Models must be replaceable independently of Hermes.**
10. **Hermes remains responsible for orchestration state.**
11. **The harness remains responsible for agent execution state and Spec Kit step state.**
12. **Existing worktree isolation and Git safety must remain intact.**
13. **Existing validation and publishing workflow must remain intact.**
14. **Do not introduce unnecessary abstractions beyond the harness boundary.**

---

# 14. Implementation Guidance

This document specifies architecture, not code.

Before coding:

1. Inspect the current Hermes path (`scout` / Spec Kit plan / tasks / implement).
2. Treat that path as **to be removed from Hermes**, not wrapped.
3. Define the thin start/result contract (one run, not per Spec Kit stage).
4. Put the Spec Kit orchestrate playbook behind the Pi adapter.
5. Keep workspace prepare, human parking, validation, and PR **outside** that boundary.

Do not rewrite unrelated components.

Do not add `/speckit-orchestrate` to Hermes.

Do not design a full live event stream in the first slice. Start with one run and one result (plus `needs_human`).

---

# 15. Definition of Done

The architectural goal is achieved when:

* Hermes starts a task without knowing Spec Kit’s internal steps.
* Pi runs the full Spec Kit orchestrate playbook through its SDK.
* Questions and continue/skip come back through Hermes, not a Pi chat.
* Hermes receives a normalized result and continues existing validation and PR.
* No Pi-specific or Cursor-specific types leak into Hermes orchestration.
* The old Hermes Spec Kit short path is gone, not left beside the new path.
* A second harness could theoretically be added without redesigning Hermes.

The immediate proof:

```text
Existing real task
       ↓
Hermes (select, workspace, start)
       ↓
Harness Contract
       ↓
Pi Adapter
       ↓
Pi + Spec Kit orchestrate (full pipeline)
       ↓
Hermes (human if needed → existing validation → existing PR)
```

The goal is **not** to build the final multi-harness system now.

The goal is to establish the correct boundary: **Hermes supervises; Pi executes Spec Kit.**
