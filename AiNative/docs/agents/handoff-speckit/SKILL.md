---
name: handoff-speckit
description: >-
  Emit a copy-paste /speckit-orchestrate launch block from this chat. Use when
  the user invokes /handoff-speckit, asks to hand off to speckit-orchestrate,
  or wants a paste-ready launch message for a new empty agent. Does not run
  orchestrate.
disable-model-invocation: true
---

# Handoff to speckit-orchestrate

When this skill is invoked, **do not** run `/speckit-orchestrate`, implement, or
spawn workers. Turn **this chat** into a self-contained launch block for a
**new empty agent**.

**Never choose the path.** Do not infer or emit `path: feature`, `path: change`,
or `path: job`. Only hand off — the new agent / orchestrate picks the path.

This is not the `handoff` session-capture skill (`.agent/handoff/` files).

Extra user text after the invoke is extra scope or constraints. Fold it into
the block. If empty, use only this conversation.

## Infer

From the thread (and extra args if any):

- **Goal** — one sentence: who, what, why
- **skip** — include `skip` unless the user explicitly wants clarify questions in the new agent
- **keep-local** — include `keep-local` only if the user said not to ship, commit, push, or open a PR. Orchestrate ships automatically otherwise.
- **Done when** — observable checks
- **In / out of scope** — decisions already made here; do not drop them
- **Constraints** — stack, files, what not to touch
- **Host profiles** — the Reasoning, Validation and Worker profiles from the HOST configuration (see [Host profiles](#host-profiles)). Always include them; read the values, never type them from memory.
- **Context** — branch, key paths, ruled-out bugs, APIs. Never “continue the previous chat.”
- **Open decisions** — questions raised here but not settled, each as a question. Omit the section if none. Do not resolve them yourself; clarify answers them in its choice report.

If the thread has no actionable goal, say so in one sentence and stop. Do not invent a feature.

## Host profiles

Read the HOST configuration on every run so the new agent gets the same model
profiles this host uses. Read-only: never write or change the config.

1. **File** — `$SPECKIT_HARNESS_MODELS` if set, else `~/.config/ainative/harness-models.yaml`.
2. **Section** — the active harness: `$SPECKIT_HARNESS` if set, else the harness you are running in (`cursor`, `opencode`, or `claude`).
3. **Each profile** (Reasoning, Validation, Worker) — take that section's profile. If the section or profile is missing, take the `default` section's value for that profile only. Never mix profiles.
4. **Report** — `executionMode`, `provider`, `modelId`, and `effort` only when set. Include `fallback` only when the profile has one.
5. **Unresolved** — if the file is missing or a profile has no usable value, write `unresolved — set in harness-models.yaml` for that profile. Do not guess a model.
6. **Hermes** — the file does not apply. Write `managed by Hermes profile config` for each profile; do not guess values.

Only config values go in. One-off keyword or env overrides are not read here;
include one only if the user typed it in the request.

## Output

Reply with **only** a single fenced `text` block the user can paste into a new agent as the whole message. No preamble, no commentary after the fence.

First line is the command. Put `skip` and `keep-local` on that line when they apply. **Do not** put `path:` or `skill:` on that line — leave path selection to the receiving agent.

```text
/speckit-orchestrate skip

Goal: <one sentence>

Done when:
- <check>

In scope:
- ...

Out of scope:
- ...

Constraints:
- ...

Host profiles (<harness> — harness-models.yaml):
- Reasoning: <executionMode>, <provider>, <modelId>[, effort: <level>]
  - fallback: <executionMode>, <provider>, <modelId>
- Validation: <executionMode>, <provider>, <modelId>[, effort: <level>]
- Worker: <executionMode>, <provider>, <modelId>[, effort: <level>]

Context:
- ...

Open decisions:
- <unsettled question?>
```

If known files or a named skill matter, list them under Context / Constraints — do not encode them as a path choice.

Keep it short enough to paste. Prefer bullets over prose. Do not write files unless the user asked to save the handoff.
