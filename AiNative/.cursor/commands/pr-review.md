---
description: Staged PR review for any project — defaults to the current workspace
---

# PR review command

```yaml
name: pr-review
description: Staged PR review for any project — defaults to the current workspace
```

## Invocation

When this command is invoked, apply the **pr-reviewer** skill from `~/.cursor/skills/pr-reviewer/` (machine symlink into the AiNative checkout).

Do not use a project-local `~/.cursor` skill copy — that path resolves through the symlink.

## Arguments

`$ARGUMENTS` — parse per the skill. **Project root defaults to the current workspace.** An absolute path is optional, for reviewing a different clone.

```text
/pr-review
/pr-review --pr 42
/pr-review --uncommitted
/pr-review --focus security
/pr-review --extra @docs/design.md
/pr-review --base main
/pr-review /absolute/path/to/other-clone --pr 42
```

## Steps

1. Resolve `project-root`: first absolute path in `$ARGUMENTS` if present, else the current workspace.
2. Load project context from `<project-root>/.cursor/agents.yaml` (or `.cursor/pr-review.yaml`).
3. Fetch diff (`gh pr diff` or `git diff`).
4. Run phases 1 → 1.5 (if applicable) → 2 → 3 → 4 → 5 in order.
5. Emit the consolidated report from the skill.

## Examples

```text
/pr-review --pr 128
```

```text
/pr-review --focus reliability
```
