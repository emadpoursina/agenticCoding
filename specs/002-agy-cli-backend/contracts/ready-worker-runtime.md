# Contract: Ready `worker-runtime` for Antigravity

Applies when resolved worker is `antigravity` (aliases `agy`, `google-antigravity`) or default.

## Pass

1. `command -v agy` succeeds (operator PATH only).
2. `agy models` exits 0 (stdout/stderr not shown in FIXES; do not paste model lists if noisy — note may say CLI authenticated).

`from google.antigravity import Agent` must not be consulted. Missing Python SDK must not fail this check. `GEMINI_API_KEY`, `GOOGLE_API_KEY`, Vertex/Enterprise env must not pass the check by themselves.

## Fail notes and FIXES

| Condition | Note contains | Fix tells operator |
|-----------|---------------|--------------------|
| `agy` not on PATH | `agy` / PATH | install Antigravity CLI and put `agy` on PATH. Must **not** say `pip install google-antigravity` |
| `agy models` non-zero | unauthenticated or broken CLI | authenticate the CLI (`agy` interactive login once); API key env is not enough |

Do not probe `~/.local/bin/agy` unless that directory is already on PATH for the Ready process.

## Selftests (both ready copies)

| Case | Setup | Expect |
|------|--------|--------|
| 16 | `SPECKIT_WORKER=pi`, missing pi binary | `worker-runtime: fail`, `pi not on PATH` |
| 17 | `SPECKIT_WORKER=antigravity`, PATH without `agy`, isolated HOME, unset API/Vertex env | `worker-runtime: fail`; not an SDK-import message |
| 18 | unknown worker | unknown backend |
| 19 | unset `SPECKIT_WORKER` | `WORKER: antigravity` and a `worker-runtime:` line |

Keep the suite default `SPECKIT_WORKER=pi` so fixtures stay READY-ok without a live `agy`.

## Spawn vs Ready

Spawn does **not** re-run `agy models`. If credentials expire after Ready, stdin-ignored print mode plus timeout ends the job (CLI documents non-interactive unauthenticated → `authentication required` rather than a login TTY).
