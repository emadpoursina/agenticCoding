# ADR: Feature loop replaces homemade PIV as the live workflow

**Date:** 2026-09-21
**Status:** Accepted

## Context

AiNative originally defined PIV (Plan → Implementation → Validation) with
in-house agents (scout, plan-reviewer, critic, tester, pr-reviewer).
Hermes was later wired to run GitHub Spec Kit as a **single Pi playbook**,
while Cursor ran `/speckit-orchestrate` as a parent dispatcher with one
worker per stage. Docs, Cursor, and live Hermes described three different
loops.

The operator chose an outer wrap: Ready and AiNative validation/review
gates, Spec Kit as the middle states, a thin parent as the graph, Pi as
a one-step executor. Cursor already parents that pattern in the IDE.
**The next code change is Hermes only.**

## Decision

- **AiNative** owns the loop definition:
  `docs/systems/feature-loop.md`.
- **Two orchestrators, one graph:** Cursor parent is
  `/speckit-orchestrate` (workers: Cursor Task or Pi via `/pi-harness`).
  Hermes parent is `personalAgent` (workers: Pi only). Neither copies
  the graph; they link `feature-loop.md`.
- Each **agent state** is one new worker. Pi / Task does not know the
  graph. `/pi-harness` is a worker backend, not an orchestrator.
- Spec Kit skills stay in the **enrolled project**. They are not copied
  into AiNative.
- Homemade PIV in `agentic-coding.md` is historical / optional Cursor
  guidance, not the live stage list.
- Specs `013` / `014` “one Spec Kit playbook, no Hermes-owned stages”
  are superseded for the live path by `specs/018-unified-feature-loop`.
- **Implementation order:** personalAgent first. Do not change Cursor
  `/speckit-orchestrate` in that pass.

## Consequences

**Enables:** insert an AiNative agent between Spec Kit states; keep Pi
context small; one loop for Cursor and Hermes.

**Trade-offs:** more Pi boots and report parsing; Hermes must stay a thin
dispatcher or it will re-implement Spec Kit in Python.

## Rejected alternatives

- Keep one Pi `speckit-orchestrate` playbook (cannot insert mid-loop
  agents; context grows).
- Keep homemade PIV as the live machine (Spec Kit already replaced plan +
  implement).
- Duplicate the loop into `personalAgent` as a second methodology.
- Make `/pi-harness` the orchestrator (it is spawn-only).
