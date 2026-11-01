# Host editor access to AiNative agents

AiNative `docs/agents/` is the source of truth. Cursor, OpenCode, and Claude Code
must not keep a forked copy of an agent. They symlink the same folders.

| Host | Skills path | Invoke |
|------|-------------|--------|
| Cursor | `~/.cursor/skills/<name>` | Skill name, or `/<name>` command |
| OpenCode | `~/.config/opencode/skill/<name>` | Skill name |
| Claude Code | `~/.claude/skills/<name>` | Skill name, or `/<name>` ([official skills docs](https://code.claude.com/docs/en/skills)) |

Claude Code merges custom commands into skills — a skill folder at
`~/.claude/skills/<name>/SKILL.md` already creates `/<name>`. Do **not** also
symlink AiNative agents into `~/.claude/agents/`; that path is Claude's separate
[subagent](https://code.claude.com/docs/en/sub-agents) format.

## Link skills

From this repo:

```bash
./docs/knowledge/setup/link-host-skills.sh            # Cursor
./docs/knowledge/setup/link-host-skills.sh --claude   # Claude Code
./docs/knowledge/setup/link-host-skills.sh --all      # Cursor + OpenCode + Claude
```

Skip `template/` (copy starter, not an agent). Library skills under
`docs/agents/_skills/` are linked too so every host sees the same names.

Cursor-only extra (not an AiNative agent): `~/.cursor/skills/pr-generate/`.
`/speckit-orchestrate` ship uses that skill’s `template.md`.

## Cursor commands

Cursor slash commands are a separate surface from Agent Skills. OpenCode and
Claude Code do not need them; they invoke the skill (or `/skill-name`) directly.

Each Cursor command in [`.cursor/commands/`](../../../.cursor/commands/) only
tells the agent to follow `~/.cursor/skills/<name>/SKILL.md` (plus `AGENTS.md`
and `rule.md` in that folder). Do not put a second workflow in the command.

`link-host-skills.sh` writes a missing command file per agent and symlinks it
to `~/.cursor/commands/<name>.md`.

Platform aliases (Cursor name ≠ skill folder):

| Command | Skill it runs |
|---------|----------------|
| `/pr-review` | `pr-reviewer` |
| `/pr-generate` | Cursor-only `pr-generate` (no OpenCode/Claude skill) |
| `/handoff-speckit` | Cursor-only launch-block helper (does not run `/speckit-orchestrate`). No skill behind it; the command file is the workflow, the one exception to the rule above. |

Skills with `disable-model-invocation: true` will not auto-load; use the slash
command (or attach the skill) — `/speckit-orchestrate`, `/change`, `/critic`,
`/tester`, `/pr-reviewer`, `/route-work`, `/pi-harness`, `/antigravity-harness`, `/claude-harness`,
`/speckit-ready`.

## After adding an agent

1. Add the folder under `docs/agents/<name>/` and register it in
   [agents/README.md](../../agents/README.md).
2. Re-run `link-host-skills.sh --all` so Cursor, OpenCode, and Claude see it.
