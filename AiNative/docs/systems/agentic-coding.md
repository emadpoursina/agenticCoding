# Agentic coding system

**Live feature workflow is not this file.** Use
[feature-loop.md](./feature-loop.md) (Hermes + Cursor). This document is
the older homemade PIV write-up (scout, plan-reviewer, critic, tester).
Keep it for optional small Cursor-only work; do not treat it as what
Hermes runs.

Canonical five-part model (Harness, Model, Context, Tools, Agents): [agentic-system.md](./agentic-system.md).

This doc covers **Context** (AI layer below) and historical **PIV** agents. Harness, model tiers, and tools are defined in agentic-system.md.

## AI layer

1. Markdown files about the project that explain different parts of the codebase to an AI — plus your rules, policies, and conventions.
2. **Progressive disclosure** — two parts: an index main file and detail files.
   1. The AI uses the index to find and load only what it needs instead of filling context with irrelevant information.
   2. Keep file size in check: each file should point to a specific part of the code so an agent working on that part loads only that file.
   3. Keep the AI from loading unnecessary material so the context window stays free for actual coding.
3. Rules for how you code and what policies or agreements you have about style.
   1. Rules matter: a bad rule means bad code across all features.
   2. Start small and grow step by step as agents make mistakes — fix not only the problem but also the specs/standards files.
4. When using MCPs, avoid filling context with poorly scoped MCP server handling.
5. Developers use the terminal as their environment for better control and lower context consumption.

## PIV: Plan — Implementation — Validation

### Plan

1. Brainstorm with AI and explain the idea.
2. Define the blast radius.
   1. How much autonomy the task needs.
   2. A good measure is number of files touched.
      1. Based on complexity, configure how autonomous the AI should be.
      2. Based on complexity, configure how much the AI should plan and ask.
3. **Interrogate before writing the plan.** Run the [scout](../agents/scout/) agent first to produce a System Understanding Brief of the current system in the blast-radius area; the planner takes the brief as input so its reasoning budget goes on the questions, not on indexing. During interrogation, route any further repo questions to scout's **Repo Q&A** mode (cheap Tier 3) instead of reading files on the planner model. Then, based on task complexity, ask multiple-choice questions — **exactly 4 options each** — and **recommend one answer** per question with a brief rationale. Wait for confirmation or corrections before drafting the written plan.

   | Complexity | Questions | Typical signal |
   |------------|-----------|----------------|
   | Low | 5 | 1–2 files, narrow scope |
   | Medium | 10 | 3–6 files, some unknowns |
   | High | 20 | 7+ files, multi-area, or ambiguous requirements |

4. **Reuse before building.** Before proposing new code, work through this order:

   1. **Library** — Is there a maintained library that solves this? Is adoption worth it (dependency cost, fit, maintenance, team familiarity)?
   2. **In-repo** — Is there an existing implementation, module, or pattern in this codebase to extend or reuse?
   3. **Build** — Only if neither applies, plan to implement from scratch.

   Document the choice and rationale in the execution plan.

5. Plan each agent so they do not touch the same areas and create conflicts. Use small atomic commits.
6. Produce a **written plan artifact** before Implementation starts. Draft it, then **automatically run the [plan-reviewer](../agents/plan-reviewer/) gate** (planner spawns it as a same-model subagent) — fix and rewrite on REJECT until ACCEPT, then present it and wait for confirmation. Required sections:

   | Section | Purpose |
   |---------|---------|
   | **Execution plan** | Work items, blast radius, agent boundaries |
   | **Acceptance criteria** | Measurable done conditions — testable statements the critic checks against the implementation |
   | **Validation layer** | What critic and tester will verify later: test types (unit, integration, E2E, user flow), heuristic risks, PASS/FAIL signals — see [validation-layer.md](./validation-layer.md) |
   | **Test flows** | Step-by-step user/customer flows the tester executes — happy path, edge cases, error paths |
   | **Commit plan** | Atomic commits per work item |

   Without acceptance criteria, test flows, and a validation layer section, critic and tester lack inputs for the Validation phase.

### Implementation

1. **Context reset:** start a new empty chat with only implementation-needed docs.
2. The developer only answers specific questions the AI has.
3. Delegate the *how*; keep thinking about the *why* of the feature or architecture.

### Validation

Validation is owned by two in-house agents: [critic](../agents/critic/) (adversarial review of plan and implementation — design holes, edge cases, spec/code mismatch) and [tester](../agents/tester/) (prove the code works — run the test flows defined in Plan; browser automation for E2E). Run critic first, then tester. Use a **different LLM model** (and a new chat) than Plan or Implementation — see [validation-layer.md](./validation-layer.md#model-selection). Full architecture: [validation-layer.md](./validation-layer.md).

1. Multi-layer pyramid for catching bugs and problems before they reach PR.
2. Prove the code actually works.
3. Use test flows defined in the planning phase.
4. Browser automation tools for E2E.
5. Three important loops when a problem is found:
   1. **Loop back to Implement:** give the agent the specific validation failure as feedback and let it fix the issue. Be explicit: “The function returns undefined when the input array is empty — fix this so it returns an empty array instead.”
   2. **Loop back to Plan:** if the failure reveals a misunderstanding about the task itself, do not patch it in Implement. Revise the spec and run a new cycle.
   3. When the AI misses something, fix the problem and update the project AI layer. Also update the universal overall AI layer (AiNative repo) when the lesson applies globally.
   4. Ask the agent to write unit/integration/E2E tests after implementation.
   5. [pr-reviewer](../agents/pr-reviewer/) is the final gate, run **after** Validation passes. If the validation layer works correctly there should be little surprise in PR review — a problem reaching PR review means something slipped through Validation, so feed the gap back into the critic/tester agents.
