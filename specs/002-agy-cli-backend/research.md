# Research: Antigravity CLI worker backend

Operator skip is active. Decisions below resolve Technical Context and map official CLI docs onto the existing wrapper/Ready surfaces. No NEEDS CLARIFICATION remains.

## CLI is the worker; wrapper stays Python

- **Decision**: Rewrite `agy-spawn.py` to `subprocess` `agy` with stdin ignored. Delete `google.antigravity` imports. Keep Python as the launcher language and the parent API (`python3 …/agy-spawn.py`).
- **Rationale**: Spec FR-001/FR-002/FR-017; Pi already does “wrapper execs CLI” in `pi-spawn.mjs` (`stdio: ["ignore","pipe","pipe"]`). Parent must not exec `agy` itself.
- **Alternatives considered**: Rewrite wrapper in Node to share Pi code — rejected (spec: Python remains the wrapper). Hybrid SDK fallback — rejected (FR-017). Parent calling `agy -p` — rejected (FR-002).

## Print vs stream-json (both always `-p`)

- **Decision**: Wrapper `--print` → `agy -p` with default text stdout. Wrapper without `--print` → `agy -p --output-format stream-json`, persist every stdout line to `events.jsonl`. Never pass `--input-format stream-json` with `-p` (CLI drops `-p` prompts and requires stdin).
- **Rationale**: Official [headless](https://antigravity.google/docs/cli/headless/) + [reference](https://antigravity.google/docs/cli/reference/); spec FR-003–FR-006. Today `--print` is a no-op chatter flag on the SDK path.
- **Alternatives considered**: `--output-format json` for long jobs — rejected (no live events). stdin stream-json session — rejected (would hang with stdin ignored; CLI forbids combining with `-p`).

## STATUS text source

- **Decision**: Text mode: parse captured CLI stdout (diagnostics are on stderr). Stream-json: reconstruct assistant text from disk `events.jsonl` — prefer last `event=="result"` → `result.response`; if missing, concatenate `step_update.text_delta` for `step_type=="agent_response"`. Parent still polls only `status.json` / `report.json`.
- **Rationale**: Clarification session 2026-10-26; FR-021. Official stream shape is `init` / `step_update` / `result`, not Pi’s `type` events.
- **Alternatives considered**: Parse CLI `status` SUCCESS/ERROR as worker STATUS — rejected (different vocabulary from `ok|stuck|blocked`). Parent ingesting `events.jsonl` — rejected (FR-021).

## Edit vs scout argv

- **Decision**: Default (edit): `--mode accept-edits --dangerously-skip-permissions`. Scout: `--mode plan` and omit skip-permissions. Always `--disable-slash-commands`. No `--prompt-interactive`. No `ask_user`.
- **Rationale**: Official `--mode` values (`accept-edits` | `auto` | `plan`). `auto` is preview, sandbox-gated, not on business/enterprise. Headless default Ask **soft-denies shell and still exits 0** — that is why skip-permissions is required for implement jobs. `accept-edits` auto-approves workspace file writes; skip-permissions auto-approves tools including shell.
- **Alternatives considered**: `--mode auto` — rejected in spec assumptions. Scout with skip-permissions — rejected (would widen plan into an auto-approve shell agent). Scoped `permissions.allow` in `settings.json` — out of scope (must not alter operator auth/settings).

## Skip-permissions fail-closed

- **Decision**: Always pass `--dangerously-skip-permissions` on edit jobs. Official docs name no replacement flag. If the child exits because the flag is unknown, lifecycle is `failed`; do not retry without the flag; do not import the SDK.
- **Rationale**: Spec clarification; FR-007. Replacement allowed only if official headless/reference names an equivalent (they do not as of 2026-10-26).
- **Alternatives considered**: Probe `agy --help` before spawn — extra surface, not required. Degrade to Ask — rejected.

## Timeout dual enforcement

- **Decision**: If wrapper `--timeout` is set, pass `agy --print-timeout` using Go duration (`{n}s` from wrapper seconds; millisecond values ceil up to whole seconds, minimum 1s when a timeout was requested) **and** keep the wrapper SIGTERM then SIGKILL timer (Pi `GRACEFUL_KILL_MS` ≈ 2s). If `--timeout` is omitted, pass neither `--print-timeout` nor a wrapper kill timer.
- **Rationale**: FR-012. Headless page documents default wait **5 minutes**; CLI reference lists `--print-timeout` default `0s` (wait until the turn completes). Spec: do not invent a wrapper timeout; CLI default applies. Dual kill covers a CLI that ignores print-timeout.
- **Alternatives considered**: Always pass `--print-timeout 5m` — rejected (invents a timeout when operator omitted `--timeout`). Seconds-only without unit — rejected if CLI wants duration syntax; `{n}s` matches official examples (`15m`, `10m`).

## Ready worker-runtime

- **Decision**: For `antigravity|agy|google-antigravity`: `command -v agy` then `agy models` (stdout discarded; non-zero fails). Do not require `python3` or `google.antigravity`. Do not treat `GEMINI_API_KEY` / Vertex env as sufficient. Do not special-case `~/.local/bin/agy` unless it is on PATH. Keep requiring `python3` only implicitly because the parent still launches the `.py` wrapper — that is **not** the Ready identity check (FR-014).
- **Rationale**: Ready currently can pass on PyPI SDK + API key with no CLI. Spec invert: CLI auth is the signal.
- **Alternatives considered**: Keep API-key fallback — rejected (SDK-era). Probe `agy models` on every spawn — rejected (FR-023).

## Ready selftests

- **Decision**: Keep cases 16 (missing pi), 18 (unknown worker), 19 (default antigravity). Rewrite case 17 to isolate `agy` off PATH (stub PATH + fake HOME, no `agy` binary) and expect `worker-runtime: fail` plus a PATH install fix, not `pip install google-antigravity`. Case 19 must still report `WORKER: antigravity` and a `worker-runtime:` line; pass/fail follows whether the isolated environment has `agy`. Apply identically to `docs/agents/ready/` and `docs/agents/speckit-ready/` copies.
- **Rationale**: FR-015. Existing case 17 comments already isolate PATH/HOME because host SDK/`agy` made the test flaky — that isolation now becomes the product check.
- **Alternatives considered**: Live `agy models` success case in CI — not deterministic without operator credentials; optional local-only, not a required selftest.

## Contract prepend vs system_instructions

- **Decision**: Read `worker-contract.md` and prepend it to the job prompt passed as `agy -p <prompt>`. CLI has no `--append-system-prompt`.
- **Rationale**: FR-010; Pi uses `--append-system-prompt` which agy lacks.
- **Alternatives considered**: `--json-schema` for STATUS — rejected (compact report is free text).

## Optional flags

- **Decision**: `--model` required (exit 2, no child). `--effort` forwarded as `agy --effort` when set (`low`–`max` per CLI). `--conversation-id` → `agy --conversation <id>` when set; default isolated (no `--continue`). `--vertex` remains parsed for compatibility and is **not** mapped to `--project`; Vertex users authenticate via CLI (`agy models`).
- **Rationale**: Spec assumptions; official `--project` is a different flag and must not be invented from `--vertex`.
- **Alternatives considered**: Drop `--vertex` — would break existing parent argv for no gain.

## `backend` field in status/report

- **Decision**: Change `"backend": "antigravity-sdk"` to `"backend": "agy-cli"`. Keep `schemaVersion: 1` and the rest of the public status/report keys.
- **Rationale**: Only `agy-spawn.py` writes that string today; parent docs tell operators to read `lifecycle` / `reportValid` / `workerStatus`. Leaving `antigravity-sdk` would contradict the runtime.
- **Alternatives considered**: Leave the string — misleading. Bump schemaVersion — unnecessary; no field removed.

## Docs blast radius

- **Decision**: Required by FR-016: `antigravity-harness` `{SKILL,rule,AGENTS}.md` + wrapper comments, `speckit-orchestrate/SKILL.md`, both ready `SKILL.md`. Also edit sibling files that still teach “SDK is the worker runtime” so SC-007 / US5 search cannot fail: orchestrate `AGENTS.md`/`rule.md`, `docs/agents/README.md`, `docs/systems/feature-loop.md`, Cursor command `AiNative/.cursor/commands/antigravity-harness.md`. Keep both ready-check.sh + selftest copies in lockstep. Do not rewrite host symlinks. Changelog `AiNative/CHANGELOG.md` next SemVer (`0.4.0` recommended: worker-runtime identity change).
- **Rationale**: Independent test searches canonical AiNative agent docs, not only FR-016 paths.
- **Alternatives considered**: FR-016-only — would leave README/feature-loop/orchestrate AGENTS still saying SDK.

## Pi unchanged

- **Decision**: Do not edit `pi-spawn.mjs` or pi-harness docs except if a shared sentence currently claims Antigravity is SDK-only (orchestrate/feature-loop only).
- **Rationale**: FR-018.

## Official references (2026-10-26)

- https://antigravity.google/docs/cli/headless/
- https://antigravity.google/docs/cli/reference/
- https://antigravity.google/docs/cli/modes/
