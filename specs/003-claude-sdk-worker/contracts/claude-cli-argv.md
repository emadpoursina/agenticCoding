# Contract: `claude` child argv

The wrapper builds one argv. Parent never constructs this list. Official flag names: [CLI reference](https://code.claude.com/docs/en/cli-reference), [headless](https://code.claude.com/docs/en/headless).

## Invariants (every spawn that starts `claude`)

1. argv[0] is `claude` (or `SPECKIT_CLAUDE_BIN`).
2. `-p` or `--print` is present. Bare `claude` (TUI) is forbidden.
3. `--bg` / `--background` is absent.
4. `--cloud` with a new-task description is absent.
5. `--desktop` is absent.
6. `--bare` is absent by default (edit and scout).
7. `--input-format` is absent (never wait on parent-driven stream-json stdin).
8. `--prompt-interactive` is absent.
9. `--dangerously-skip-permissions` is absent.
10. `--permission-mode bypassPermissions` is absent.
11. `--continue` is absent.
12. `--resume` without an id is absent (no session picker).
13. `--model <id>` is present (wrapper already exited 2 if missing).
14. `--max-turns` and `--max-budget-usd` are absent unless a future spec adds them (do not default).
15. Child stdin is not a TTY (`stdio` ignore / DEVNULL).
16. Working directory is wrapper `--cwd`.
17. Job text is the print prompt argument, not stdin.

## Mode matrix

| Wrapper flags | Extra CLI flags | Output |
|---------------|-----------------|--------|
| `--print` (short) | none for format (CLI default text) | stdout = assistant text |
| (default long) | `--output-format stream-json --verbose` | stdout = NDJSON events |
| (default, not `--scout`) | `--permission-mode auto` | edit / implement |
| `--scout` | `--permission-mode plan` (no `auto`) | read/plan |
| no `--conversation-id` | `--no-session-persistence` if CLI help lists it | isolated run |
| `--conversation-id ID` | `--resume ID` (no `--no-session-persistence`) | resume print session |

## Contract attachment

| Preference | Flag | When |
|------------|------|------|
| 1 | `--append-system-prompt-file <worker-contract.md>` | CLI help lists the flag |
| 2 | `--append-system-prompt` + file contents | file flag rejected or absent |
| fail | — | both append forms rejected |

## Optional mappings

| Wrapper | CLI | When omitted / rejected |
|---------|-----|-------------------------|
| `--effort X` | `--effort X` | not passed |
| `--timeout` | *(none — no official print duration flag)* | wrapper kill timer only |
| `--conversation-id ID` | `--resume ID` | isolated run as above |
| (unattended nicety) | `--permission-prompts none` | omit if help/child rejects (v2.1.259+) |

## Fail-closed (required flags)

If installed `claude` rejects `-p`/`--print`, `--model`, `--permission-mode auto` (edit), or `--permission-mode plan` (scout): finalize `lifecycle=failed`. Do not retry Manual. Do not import Agent SDK. Do not spawn Managed Agents. Do not fall back to Pi/Antigravity/host Task.

Optional flags: omit and continue.

## Compact wrapper stdout (unchanged vs siblings)

```
RUN_DIR=…
STATUS_FILE=…
LIFECYCLE=…
REPORT_FILE=…
```
