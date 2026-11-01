# Contract: Ready `worker-runtime` for Claude

Applies to both `AiNative/docs/agents/ready/scripts/ready-check.sh` and `AiNative/docs/agents/speckit-ready/scripts/ready-check.sh` (keep lockstep).

No model call. Language Agent SDK packages are neither required nor sufficient.

## Resolution (unchanged order)

1. `SPECKIT_WORKER`
2. `git config speckit.worker`
3. default `antigravity`

Canonicalize aliases: `claude-code` | `anthropic` → `claude`. Existing `agy` | `google-antigravity` → `antigravity`.

`SPECKIT_CLAUDE_BIN` overrides the PATH name (default `claude`), parallel to `SPECKIT_PI_BIN`.

## Claude pass/fail

| Condition | Result | Note / FIXES |
|-----------|--------|----------------|
| `claude` not on PATH | fail | Install Claude Code CLI and put `claude` on PATH. **Not** `pip install claude-agent-sdk` / `npm install @anthropic-ai/claude-agent-sdk`. |
| CLI on PATH, no auth evidence | fail | Point at official API-key / `claude setup-token` / `claude auth login` docs. Do not run `claude -p`. |
| CLI on PATH + any auth evidence below | pass | SDK packages may be absent. |
| CLI version old | pass | No version floor. |

Auth evidence (any one is enough):

- Non-empty `ANTHROPIC_API_KEY`
- Non-empty `CLAUDE_CODE_OAUTH_TOKEN`
- Non-empty `ANTHROPIC_AUTH_TOKEN`
- Settings JSON contains `apiKeyHelper` in `${CLAUDE_CONFIG_DIR:-$HOME/.claude}/settings.json` **or** `<repo>/.claude/settings.json` **or** `<repo>/.claude/settings.local.json` (key presence only; do not execute)
- Non-empty file `${CLAUDE_CONFIG_DIR:-$HOME/.claude}/.credentials.json` (do not print contents)

Not sufficient: `CLAUDE_CODE_USE_BEDROCK` / Vertex / Foundry env alone; presence of `node_modules/@anthropic-ai/claude-agent-sdk` or a Python `claude-agent-sdk` install.

**Assumption**: macOS Keychain-only `/login` without `.credentials.json` and without env/helper is treated as missing auth (Ready must not spend a model turn or scrape Keychain).

## Unknown worker

Fix text lists `pi`, `antigravity`, and `claude`.

## Selftests (both copies)

Keep:

| Case | Expect |
|------|--------|
| 16 | `SPECKIT_WORKER=pi` missing pi → `worker-runtime: fail` |
| 17 | antigravity, `agy` isolated off PATH → fail, not pip SDK |
| 18 | `SPECKIT_WORKER=not-a-backend` → unknown; FIXES mention `claude` |
| 19 | unset worker → `WORKER: antigravity` and a `worker-runtime:` line |

Add (suggested labels; implement may number after 21+):

| Case | Setup | Expect |
|------|--------|--------|
| Claude PATH miss | `SPECKIT_WORKER=claude`, isolated PATH, no real `claude` | fail, PATH install, not pip/npm SDK |
| Claude auth miss | stub `claude` on PATH, isolated HOME, unset auth env | fail, login/API-key fix; check script does not invoke a model |
| Claude auth env | stub `claude` + `ANTHROPIC_API_KEY=test` | `worker-runtime: pass`, `WORKER: claude` |
| Alias | `SPECKIT_WORKER=claude-code` or `anthropic` with stub+key | `WORKER: claude` |

Suite default may stay `SPECKIT_WORKER=pi` so fixtures remain READY-ok without live `agy`/`claude`.
