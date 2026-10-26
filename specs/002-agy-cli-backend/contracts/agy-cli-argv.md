# Contract: `agy` child argv

The wrapper builds one argv. Parent never constructs this list.

## Invariants (every spawn that starts `agy`)

1. argv[0] is `agy` (PATH lookup).
2. `-p` (or `--print`) is present. Bare `agy` is forbidden.
3. `--disable-slash-commands` is present.
4. `--prompt-interactive` / `-i` is absent.
5. `--input-format` is absent (never combined with `-p`).
6. `--model <id>` is present (wrapper already exited 2 if missing).
7. Child stdin is not a TTY (`DEVNULL` / `stdio ignore`).
8. Working directory is wrapper `--cwd`.

## Mode matrix

| Wrapper flags | Extra CLI flags | Output |
|---------------|-----------------|--------|
| `--print` (short) | none for format (CLI default `text`) | stdout = assistant text |
| (default long) | `--output-format stream-json` | stdout = NDJSON events |
| (default, not `--scout`) | `--mode accept-edits --dangerously-skip-permissions` | edit / implement |
| `--scout` | `--mode plan` only (no skip-permissions) | read/plan |

## Optional mappings

| Wrapper | CLI | When omitted |
|---------|-----|----------------|
| `--effort X` | `--effort X` | not passed |
| `--timeout` | `--print-timeout {n}s` (ms ceiled to seconds, min 1s) | not passed |
| `--conversation-id ID` | `--conversation ID` | not passed; no `--continue` |
| `--vertex` | *(none)* | n/a |

Prompt is a single `-p` argument: contract text, then a blank line, then the job prompt.

## Fail-closed

If installed `agy` rejects `--dangerously-skip-permissions` (unknown flag / non-zero start) on an edit job: finalize `lifecycle=failed`. Do not strip the flag and retry. Do not import `google.antigravity`.

## Compact wrapper stdout (unchanged)

```
RUN_DIR=…
STATUS_FILE=…
LIFECYCLE=…
REPORT_FILE=…
```
