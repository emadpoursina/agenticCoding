# ADR: Fresh Hermes install; feature loop is target, not live

**Date:** 2026-09-30
**Status:** Accepted
**Supersedes:** [2026-09-feature-loop.md](./2026-09-feature-loop.md) (Pi-specific form)

## Context

The previous Hermes was a custom control plane that ran the feature loop
through Pi workers, `python -m hermes_kanban`, and operator-specific profiles
(`task-generator`, `executor`). It was erased completely and replaced with a
fresh, raw install of the official Hermes agent (`nousresearch/hermes-agent`)
in Docker (`hermes-personal-coding`).

The new install differs in ways that invalidate the old runtime docs:

- No Pi runtime and no `hermes_kanban` module.
- Native `hermes kanban` and `hermes project` commands exist, but no project is
  enrolled and only the `default` profile exists — the loop is not wired.
- AiNative is mounted read-only at `/opt/data/mnt/AiNative`; work happens in
  `/opt/data/mnt/workspace`. The old `/ainative`, `/opt/personal-agent`, and
  `hermes-context` paths are gone.
- Per-role `HERMES_*_MODEL` env vars are gone; model routing lives in
  `config.yaml`, with per-task overrides via `hermes kanban set-model`.

AiNative still described the old loop as **live**, which would mislead the new
Hermes (it reads AiNative as read-only guidance).

## Decision

- AiNative owns the methodology, not the runtime. Runtime facts live in
  `personalAgent/` and the operator's private Hermes home.
- The [feature loop](../../systems/feature-loop.md) and its agents are kept as
  **target methodology** and relabeled from "live" to "target — not wired".
- Dead runtime references are removed or generalized: Pi is replaced by a
  runtime-agnostic "worker"; `python -m hermes_kanban`, `pi_worker_contract.md`,
  `HERMES_*_MODEL`, and the `/ainative` path are gone; `task-generator` /
  `executor` profile names are no longer asserted.
- The old [feature-loop ADR](./2026-09-feature-loop.md) is superseded by this
  one; the old text stays as history.

## Consequences

**Enables:** the new Hermes can read AiNative without being told it runs a loop
it does not have; the loop design survives as a starting point for the
architecture work.

**Trade-offs:** the feature loop is now explicitly unfinished; some agent
contracts (card paths, compact reports) remain proposals until mapped onto the
native `hermes kanban` dispatch model.

## Rejected alternatives

- Delete the feature loop and its agents entirely — discards design capital and
  the runtime-agnostic agent definitions (critic, tester, pr-reviewer).
- Leave the docs as "live" — the exact failure this cleanup exists to prevent.
- Rewrite the loop onto native Hermes dispatch now — that is the architecture
  work to be done with Hermes, not a documentation cleanup.
