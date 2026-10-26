---
description: Emit a copy-paste /speckit-orchestrate launch block from this chat
---

# Handoff to speckit-orchestrate

When this command is invoked, **do not** run `/speckit-orchestrate`, implement, or spawn workers. Turn **this chat** into a self-contained launch block for a **new empty agent**.

**Never choose the path.** Do not infer or emit `path: feature`, `path: change`, or `path: job`. Only hand off — the new agent / orchestrate picks the path.

`$ARGUMENTS` is extra scope or constraints. Fold it into the block. If empty, use only this conversation.

## Infer

From the thread (and `$ARGUMENTS` if any):

- **Goal** — one sentence: who, what, why
- **skip** — include `skip` unless the user explicitly wants clarify questions in the new agent
- **keep-local** — include `keep-local` only if the user said not to ship, commit, push, or open a PR. Orchestrate ships automatically otherwise.
- **Done when** — observable checks
- **In / out of scope** — decisions already made here; do not drop them
- **Constraints** — stack, files, what not to touch
- **Context** — branch, key paths, ruled-out bugs, APIs. Never “continue the previous chat.”
- **Open decisions** — questions raised here but not settled, each as a question. Omit the section if none. Do not resolve them yourself; clarify answers them in its choice report.

If the thread has no actionable goal, say so in one sentence and stop. Do not invent a feature.

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

Context:
- ...

Open decisions:
- <unsettled question?>
```

If known files or a named skill matter, list them under Context / Constraints — do not encode them as a path choice.

Keep it short enough to paste. Prefer bullets over prose. Do not write files unless the user asked to save the handoff.
