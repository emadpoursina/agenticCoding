# Rules — Handoff to speckit-orchestrate

## Must

- Emit a self-contained launch block a new empty agent can paste as the whole
  message. Never say “continue the previous chat.”
- Include `skip` unless the user explicitly wants clarify questions in the
  new agent.
- Include `keep-local` only when the user said not to ship, commit, push, or
  open a PR.
- List unsettled questions under **Open decisions**; do not answer them here.
- If known files or a named skill matter, put them under Context /
  Constraints, not as `path:` / `skill:` on the first line.

## Must not

- Run `/speckit-orchestrate`, implement, or spawn workers.
- Infer or emit `path: feature`, `path: change`, or `path: job`.
- Invent a feature when the thread has no actionable goal.
- Write files unless the user asked to save the handoff.
- Capture session state to `.agent/handoff/` (that is the `handoff` agent).

## Stop conditions

- No actionable goal — one sentence, stop.
- After the fenced block — stop. No commentary after the fence.

## Boundary

This agent only formats a launch message. Path selection and the pipeline
belong to `speckit-orchestrate` in the receiving session.
