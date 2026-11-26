# Handoff to speckit-orchestrate

Turn the current chat into a paste-ready `/speckit-orchestrate` launch block
for a **new empty agent**. Does not run orchestrate, implement, or spawn workers.

Canonical source: AiNative `docs/agents/handoff-speckit/`. Linked into Cursor
(`~/.cursor/skills/handoff-speckit/`), OpenCode
(`~/.config/opencode/skill/handoff-speckit/`), and Claude Code
(`~/.claude/skills/handoff-speckit/`). Cursor `/handoff-speckit` only wraps
this skill.

Not the `handoff` agent (session files under `.agent/handoff/`).

## When to use

- User invokes `/handoff-speckit` (Cursor / Claude Code) or skill
  `handoff-speckit` (OpenCode)
- User asks to hand off this chat to speckit-orchestrate or wants a
  paste-ready launch message for a new agent

## Inputs

- This conversation
- Optional extra args (scope or constraints)

## Outputs

- One fenced `text` block starting with `/speckit-orchestrate` (plus `skip`
  and/or `keep-local` when they apply), including a **Host profiles** section
  read from the HOST configuration, or one sentence if there is no actionable
  goal

## Supporting files

| File | Purpose |
|------|---------|
| [SKILL.md](./SKILL.md) | Infer + output contract for the launch block |
| [rule.md](./rule.md) | Constraints and stop conditions |
