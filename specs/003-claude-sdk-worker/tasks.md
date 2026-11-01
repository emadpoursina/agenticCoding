# Tasks: Claude SDK worker harness

**Input**: Design documents from `/specs/003-claude-sdk-worker/`

**Prerequisites**: plan.md (required), spec.md (required for user stories), research.md, data-model.md, contracts/, quickstart.md — all present from plan stage.

**Tests**: Spec Independent Tests, FR-015, plan W4 / TF-1–TF-6, and `quickstart.md` explicitly require `node …/claude-spawn.mjs --self-test` and both `ready-check.selftest.sh` copies. Include those test tasks (write assertions first, confirm they fail, then implement). Do **not** add extra test frameworks, fixtures, or live Anthropic job tasks. Optional live smoke in `quickstart.md` is not a gate.

**Organization**: Tasks grouped by user story (US1–US5). Single AiNative tree. Node stdlib only for the wrapper. Do not edit `AiNative/docs/agents/pi-harness/pi-spawn.mjs` or `AiNative/docs/agents/antigravity-harness/agy-spawn.py` behavior. Do not install packages or change operator auth. Do not rewrite host skill symlinks. Changelog only `AiNative/CHANGELOG.md`. Default worker remains `antigravity`.

**Constitution**: `.specify/memory/constitution.md` is an unfilled template — spec FRs are binding.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: User story label (US1–US5) on story-phase tasks only
- Every task includes exact file path(s)

## Path conventions

- Wrapper: `AiNative/docs/agents/claude-harness/claude-spawn.mjs`
- Contract text: `AiNative/docs/agents/claude-harness/worker-contract.md`
- Ready copies (keep in lockstep): `AiNative/docs/agents/ready/` and `AiNative/docs/agents/speckit-ready/`
- Feature contracts: `specs/003-claude-sdk-worker/contracts/`

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Lock scope and contracts before adding the third worker backend.

- [X] T001 Confirm implementation stays on the plan source list (`AiNative/docs/agents/claude-harness/` new folder, `AiNative/docs/agents/speckit-orchestrate/SKILL.md` plus `AGENTS.md`/`rule.md`, both ready `SKILL.md`/`AGENTS.md` + `scripts/ready-check.sh` + `ready-check.selftest.sh`, `AiNative/docs/agents/README.md`, `AiNative/docs/systems/feature-loop.md`, `AiNative/docs/knowledge/setup/cursor-setup.md`, `AiNative/docs/knowledge/setup/hermes-readiness.sh`, `AiNative/.cursor/commands/claude-harness.md`, `AiNative/CHANGELOG.md`); never edit behavior of `AiNative/docs/agents/pi-harness/pi-spawn.mjs` or `AiNative/docs/agents/antigravity-harness/agy-spawn.py` (FR-018); no package installs, npm/pip Agent SDK, or auth/key changes (FR-019); default worker stays `antigravity`
- [X] T002 [P] Desk-check `specs/003-claude-sdk-worker/contracts/claude-cli-argv.md`, `specs/003-claude-sdk-worker/contracts/run-dir.md`, and `specs/003-claude-sdk-worker/contracts/ready-worker-runtime.md` against spec clarifications: always `-p`; never default `--bare`; edit `--permission-mode auto`; scout `--permission-mode plan`; no skip-permissions / `bypassPermissions`; Ready PATH + env/`apiKeyHelper`/`.credentials.json` with no model call; no Ready version floor

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Add a Node launcher that execs operator `claude`, owns the parent argv/run-dir surface, and never imports language Agent SDKs.

**⚠️ CRITICAL**: No user story work until T003–T006 are done. Later stories add print argv, permission modes, Ready, STATUS, and docs on this skeleton.

- [X] T003 Create `AiNative/docs/agents/claude-harness/worker-contract.md` with the same meaning as Pi/Antigravity: one job, compact `STATUS: ok|stuck|blocked`, no unsolicited commit/push/SSH (data-model.md Worker contract; FR-011)
- [X] T004 Create `AiNative/docs/agents/claude-harness/claude-spawn.mjs` (Node stdlib only; shebang ok; do not import `@anthropic-ai/claude-agent-sdk` / `claude-agent-sdk`): parent flags `--name` (required; sanitizer `[\w.-]+`, no path seps — names the run dir, **not** `claude -n`), `--cwd`, `--model` required (missing → exit 2, no `claude`), optional `--effort` / `--timeout` (seconds or `Nms`) / `--print`/`-p` / `--scout` / `--conversation-id` / `--run-id`, prompt after `--`, `--self-test` (no child); invalid `--name` / `--timeout` fail before spawn (data-model.md Wrapper spawn)
- [X] T005 In `AiNative/docs/agents/claude-harness/claude-spawn.mjs`, create run dir `.agent/claude/<job-name>/<run-id>/{status.json,report.json,events.jsonl,stderr.log}` plus `latest.json` beside the job folder; JSON `"backend": "claude-cli"` and `"schemaVersion": 2`; compact wrapper stdout `RUN_DIR=` / `STATUS_FILE=` / `LIFECYCLE=` / `REPORT_FILE=`; lifecycle `starting` → `running` → `completed` (exit 0) | `failed` (non-zero) | `terminated` (signal, not timeout) | `timed_out` (wrapper kill timer) per `specs/003-claude-sdk-worker/contracts/run-dir.md`
- [X] T006 In `AiNative/docs/agents/claude-harness/claude-spawn.mjs`, spawn `claude` via `child_process` with stdin ignored (DEVNULL / not a TTY), `cwd` = wrapper `--cwd`, argv[0] `${SPECKIT_CLAUDE_BIN:-claude}`; probe `claude --help` once for optional flags; if `claude` cannot start, fail `lifecycle=failed` with **no** Pi / Antigravity / host Task / Client SDK / Managed Agents fallback (FR-017); never default `--bare`; never pass `--bg`/`--background`, `--desktop`, `--prompt-interactive`, `--input-format`, or `--cloud` with a new-task description

**Checkpoint**: Parent-facing wrapper exists; run-dir contract exists; child stdin cannot attach a TUI.

---

## Phase 3: User Story 1 — Operator can run Spec Kit Worker stages on Claude (Priority: P1) 🎯 MVP

**Goal**: Every wrapper spawn execs official Claude Code print/headless (`claude -p`). Short jobs use default text stdout; long jobs use `--output-format stream-json --verbose` and persist events. Parent never execs `claude` itself.

**Independent Test**: Spawn via wrapper with `--print` and without it. Child argv always includes `-p`/`--print`; never a bare TUI `claude`; never `--bg`/`--cloud` description/`--input-format stream-json`; stdin not a TTY. Short jobs omit `--output-format`. Long jobs include `--output-format stream-json` and `--verbose` and write `events.jsonl`. `node AiNative/docs/agents/claude-harness/claude-spawn.mjs --self-test` covers TF-1/TF-2 argv (plan AC-1, AC-2, AC-9; SC-001, SC-002, SC-009).

### Tests for User Story 1

> Write these assertions first; they MUST fail until T008–T009.

- [X] T007 [US1] Add `--self-test` assertions in `AiNative/docs/agents/claude-harness/claude-spawn.mjs` for TF-1/TF-2: wrapper `--print` argv contains `-p` or `--print`, `--model`, no `--output-format stream-json`, no `--bare`; long-job argv (no wrapper `--print`) contains `-p` **and** `--output-format stream-json` **and** `--verbose`; neither path includes `--input-format`, `--bg`/`--background`, `--desktop`, `--prompt-interactive`, or `--cloud`; `--self-test` still does not start `claude`

### Implementation for User Story 1

- [X] T008 [US1] In `AiNative/docs/agents/claude-harness/claude-spawn.mjs`, always pass CLI `-p`/`--print`; wrapper `--print` → default text stdout (omit `--output-format`); wrapper without `--print` → add `--output-format stream-json --verbose` and persist every raw CLI stdout line to `events.jsonl` (truncate/create at start); job text is the print prompt argument, not stdin (FR-004–FR-007; contracts/claude-cli-argv.md)
- [X] T009 [US1] In `AiNative/docs/agents/claude-harness/claude-spawn.mjs`, keep stdin ignored; omit `--bg`/`--background`, `--prompt-interactive`, `--input-format`, `--desktop`, and `--cloud` task-description; do not default `--bare` so project/user config (`CLAUDE.md`, skills, MCP, hooks) loads (FR-004, FR-007, FR-025)

**Checkpoint**: Unattended headless argv is real CLI print mode; TUI cannot attach via stdin.

---

## Phase 4: User Story 2 — Edit jobs write; scout jobs stay non-writing (Priority: P1)

**Goal**: Default (edit) jobs pass `--permission-mode auto` so tools run unattended. Scout stays `--permission-mode plan`. Skip-permissions / `bypassPermissions` never appear. Required-flag rejection fails closed.

**Independent Test**: Default spawn includes `--permission-mode auto` and does not include skip-permissions / `bypassPermissions`. Scout spawn uses `--permission-mode plan` and does not use `auto`. Optional `--permission-prompts none` omitted when help/child rejects it. Required `--permission-mode auto` (edit) or `plan` (scout) rejected → `lifecycle=failed`, no Manual retry, no SDK (spec US2; plan TF-3, TF-5.6; AC-4, AC-5, AC-10).

### Tests for User Story 2

- [X] T010 [US2] Extend `--self-test` in `AiNative/docs/agents/claude-harness/claude-spawn.mjs` for TF-3: default argv has `--permission-mode auto` and does **not** include `--dangerously-skip-permissions` or `--permission-mode bypassPermissions`; `--scout` argv has `--permission-mode plan` and does **not** include `auto`, skip-permissions, or `bypassPermissions`; assert a fail-closed helper that finalizes `failed` when required `--permission-mode auto` is rejected (no Manual retry)

### Implementation for User Story 2

- [X] T011 [US2] In `AiNative/docs/agents/claude-harness/claude-spawn.mjs`, default (not `--scout`) child argv includes `--permission-mode auto` and MUST NOT include `--dangerously-skip-permissions` or `--permission-mode bypassPermissions`; if `claude --help` lists `--permission-prompts`, optionally add `--permission-prompts none`; omit that optional flag when help/child rejects it (FR-008, FR-026)
- [X] T012 [US2] In `AiNative/docs/agents/claude-harness/claude-spawn.mjs`, `--scout` passes `--permission-mode plan` and MUST NOT pass `--permission-mode auto`, `--dangerously-skip-permissions`, or `bypassPermissions`; if installed CLI rejects required `-p`/`--print`, `--model`, `--permission-mode auto` (edit), or `--permission-mode plan` (scout), fail closed before/at spawn — no Manual-mode retry, no Client SDK, no Managed Agents (FR-009, FR-026)

**Checkpoint**: Edit jobs cannot Manual-deny tools and still look successful; scout is not the edit `auto` path.

---

## Phase 5: User Story 3 — Ready fails closed on missing Claude CLI, not on missing language SDK (Priority: P1)

**Goal**: Claude `worker-runtime` is `claude` on PATH plus unattended auth evidence (no model call). SDK packages are neither required nor sufficient. Aliases `claude-code`/`anthropic` canonicalize to `claude`. Unknown-worker FIXES list `claude`. Default unset worker remains `antigravity`.

**Independent Test**: Both `ready-check.selftest.sh` exit 0. Cases 16/17 still fail as today; case 18 unknown-worker FIXES list `pi`, `antigravity`, and `claude`; case 19 `WORKER: antigravity` plus a `worker-runtime:` line. New Claude PATH-miss fails with CLI PATH fix, not `pip install claude-agent-sdk` / `npm install @anthropic-ai/claude-agent-sdk`. Auth-miss fails without invoking a model. Env-token pass even without SDK packages. Alias → `WORKER: claude`. Suite default may stay `SPECKIT_WORKER=pi` (FR-014, FR-015; plan TF-4; AC-3, AC-8, AC-14).

### Tests for User Story 3

> Add Claude selftest cases first so T015–T016 fail for the right reason until Ready gains a `claude` arm.

- [X] T013 [P] [US3] Extend `AiNative/docs/agents/ready/scripts/ready-check.selftest.sh` per `specs/003-claude-sdk-worker/contracts/ready-worker-runtime.md`: keep cases 16/17/19; update case 18 FIXES to mention `claude`; add Claude PATH-miss (`SPECKIT_WORKER=claude`, isolated PATH, no real `claude`) expecting `worker-runtime: fail` plus CLI PATH fix, not pip/npm Agent SDK; add auth-miss (stub `claude`, isolated HOME, unset `ANTHROPIC_API_KEY` / `CLAUDE_CODE_OAUTH_TOKEN` / `ANTHROPIC_AUTH_TOKEN`) expecting fail and login/API-key fix with no model invocation; add stub+`ANTHROPIC_API_KEY=test` expecting `worker-runtime: pass` and `WORKER: claude`; add alias `claude-code` and/or `anthropic` expecting `WORKER: claude`; keep suite default `SPECKIT_WORKER=pi`
- [X] T014 [P] [US3] Apply the identical case 16–19 + Claude-case rewrite to `AiNative/docs/agents/speckit-ready/scripts/ready-check.selftest.sh` (FR-015 lockstep)

### Implementation for User Story 3

- [X] T015 [US3] In `AiNative/docs/agents/ready/scripts/ready-check.sh`, add `claude|claude-code|anthropic` (case-insensitive aliases → report `WORKER: claude`); binary `${SPECKIT_CLAUDE_BIN:-claude}` via `command -v`; auth pass if **any** of: non-empty `ANTHROPIC_API_KEY`, `CLAUDE_CODE_OAUTH_TOKEN`, `ANTHROPIC_AUTH_TOKEN`; `apiKeyHelper` key present in `${CLAUDE_CONFIG_DIR:-$HOME/.claude}/settings.json` **or** `<repo>/.claude/settings.json` **or** `<repo>/.claude/settings.local.json` (presence only; **do not execute**); non-empty file `${CLAUDE_CONFIG_DIR:-$HOME/.claude}/.credentials.json` (do not print contents). Fail if CLI missing (FIXES: install Claude Code CLI / PATH — never `pip install claude-agent-sdk` / `npm install @anthropic-ai/claude-agent-sdk`) or none of the auth evidence exists (FIXES: official API-key / `claude auth login` / `claude setup-token`; mention Keychain-only login is undetectable without env/helper/credentials file). Do not call the model. Do not parse `claude --version`. Cloud env (`CLAUDE_CODE_USE_BEDROCK` / Vertex / Foundry) is not sufficient. Unknown-worker FIXES list `pi`, `antigravity`, and `claude`. Unset worker still defaults to `antigravity` (FR-001, FR-014, FR-026)
- [X] T016 [US3] Copy the same `worker-runtime` logic into `AiNative/docs/agents/speckit-ready/scripts/ready-check.sh` so both copies stay in lockstep (FR-014, FR-015)

**Checkpoint**: Ready on a CLI+auth machine can pass without Agent SDK packages; missing CLI or undetectable auth cannot.

---

## Phase 6: User Story 4 — Wrapper contract matches Pi/Antigravity monitoring (Priority: P1)

**Goal**: Parent flags, contract append, isolation/resume, timeout SIGINT→SIGTERM→SIGKILL, STATUS parse, and `status.json`/`report.json` match existing harnesses. Stream-json `workerStatus` comes from reconstructed assistant text; parent still does not ingest `events.jsonl`. Non-zero `claude` exit is `lifecycle=failed` even if text had `STATUS: ok`.

**Independent Test**: Missing `--model` exits 2 without starting `claude`. `--effort` forwarded when CLI accepts it. `--timeout 2` sets wrapper timer fields; argv has no `--max-turns` / `--max-budget-usd`; omitted timeout → no wrapper-invented timer. `--conversation-id` → `--resume`; default isolated (`--no-session-persistence` when help lists it). Contract via `--append-system-prompt-file` (fallback `--append-system-prompt`). Stream-json reconstruct prefers last `type=="result"` text. `node …/claude-spawn.mjs --self-test` prints `SELFTEST: ok` (FR-010–FR-013, FR-021–FR-022; plan TF-5; AC-6, AC-13).

### Tests for User Story 4

- [X] T017 [US4] Extend `--self-test` in `AiNative/docs/agents/claude-harness/claude-spawn.mjs` for TF-5: missing `--model` → exit 2, no spawn; `--timeout 2` sets wrapper kill-timer fields and does **not** add `--max-turns` or `--max-budget-usd`; omitted timeout → no wrapper-invented timer; `--conversation-id` maps to `--resume`; default isolated includes `--no-session-persistence` when probed present and never `--continue` / `--resume` without an id; contract append uses `--append-system-prompt-file` or `--append-system-prompt` fallback; dual-append failure is fail-closed; non-zero child exit → `lifecycle=failed` even if stdout has `STATUS: ok`; stream-json fixture with `type=="result"` wins; fixture with only `text_delta` still parses `STATUS: ok`; malformed JSONL lines increment `parseErrors` and do not crash; SIGINT-then-SIGTERM-then-SIGKILL order encoded in timeout helper fields

### Implementation for User Story 4

- [X] T018 [US4] In `AiNative/docs/agents/claude-harness/claude-spawn.mjs`, require `--model` (exit 2, do not start `claude`) and pass `--model <id>`; attach `AiNative/docs/agents/claude-harness/worker-contract.md` via `--append-system-prompt-file` when help lists it, else `--append-system-prompt` with the same file text; if both append forms are rejected, fail closed (do not drop the contract); job text remains the `-p` prompt (FR-010, FR-011)
- [X] T019 [US4] In `AiNative/docs/agents/claude-harness/claude-spawn.mjs`, forward `--effort` as `claude --effort` only when set **and** CLI accepts it; no `--conversation-id` → `--no-session-persistence` when help lists it, never `--continue`, never `--resume` without an id; `--conversation-id <id>` → `--resume <id>` and omit `--no-session-persistence`; wrapper `--timeout` starts wrapper kill timer only (no official print duration flag): on expiry SIGINT, wait ~2s (`GRACEFUL_KILL_MS`), SIGTERM, wait again, SIGKILL; omit the timer when `--timeout` omitted; never default `--max-turns` or `--max-budget-usd` (FR-010, FR-012)
- [X] T020 [US4] In `AiNative/docs/agents/claude-harness/claude-spawn.mjs`, parse worker STATUS with regex `\bSTATUS\s*[:=]?\s*(ok|stuck|blocked)\b`: text mode from captured CLI stdout; stream-json from `events.jsonl` — last object `type == "result"` string at `result` (or nested `result.result`), else join `type == "assistant"` `content[].text` (skip subagent lines with non-null `parent_tool_use_id` unless no main-thread text), else join `stream_event` `text_delta`; put that text in `report.json` `summary`/`summaryExtracted`; `reportValid` true iff STATUS token found; heartbeat `status.json` ~2s with `current`/`lastEventType` (`result`, `assistant`, `system`, or synthetic `agent_start`) without assistant body in `status.json`; wrapper process exit 0 only when `lifecycle=completed`; parent job success remains `reportValid`/`workerStatus` (FR-013, FR-021, FR-022; contracts/run-dir.md)

**Checkpoint**: Parent can keep polling `status.json`/`report.json` unchanged; stream-json STATUS works without parent reading events.

---

## Phase 7: User Story 5 — Orchestrate and host docs list Claude as a third worker (Priority: P1)

**Goal**: Canonical speckit-orchestrate, ready (both copies), agents README, feature-loop, Cursor command, and host-skill linking treat Claude as a Worker backend beside Pi and Antigravity. Dispatcher still does not implement stages. Changelog records the backend.

**Independent Test**: Search in-scope files for worker resolution. Claude is named (`claude-harness`, `SPECKIT_WORKER=claude`). Claims that only Pi and Antigravity exist are gone. Pi and Antigravity spawn instructions remain accurate. `rg` commands in `quickstart.md` §§2, 4, 6–7 pass (spec US5; AC-2, AC-7, AC-11; SC-010).

### Implementation for User Story 5

- [X] T021 [P] [US5] Write `AiNative/docs/agents/claude-harness/SKILL.md`, `AiNative/docs/agents/claude-harness/rule.md`, `AiNative/docs/agents/claude-harness/AGENTS.md`, and module/doc comments in `AiNative/docs/agents/claude-harness/claude-spawn.mjs`: spawn-only inversion (parent writes the job; Claude executes); parent only launches `claude-spawn.mjs` with `--cwd` = WORKTREE and required `--model` (no harness-pinned model; resolution still invocation `worker:` → `SPECKIT_WORKER_MODEL` → runtime default); never exec `claude` itself; never default `--bare`; edit `--permission-mode auto`; scout `--permission-mode plan` (FR-003, FR-016, FR-023, FR-024)
- [X] T022 [P] [US5] Update `AiNative/docs/agents/speckit-orchestrate/SKILL.md`, `AiNative/docs/agents/speckit-orchestrate/AGENTS.md`, and `AiNative/docs/agents/speckit-orchestrate/rule.md` so Worker SDK resolution order stays env → git config → default `antigravity`, accepted values include `claude` with aliases `claude-code`/`anthropic`, and `WORKER: claude` stages follow `claude-harness` the same way as `pi-harness` / `antigravity-harness`; parent remains a dispatcher and does not exec `claude -p` (FR-001, FR-016, FR-023)
- [X] T023 [P] [US5] Update `AiNative/docs/agents/ready/SKILL.md`, `AiNative/docs/agents/ready/AGENTS.md`, `AiNative/docs/agents/speckit-ready/SKILL.md`, and `AiNative/docs/agents/speckit-ready/AGENTS.md`: Worker backends are `pi`, `antigravity`, and `claude`; Ready `WORKER:` compact field includes `claude`; Claude worker-runtime is PATH `claude` + unattended auth evidence without a model call; SDK packages neither required nor sufficient (FR-014, FR-016)
- [X] T024 [P] [US5] Update sibling operator docs so exclusive two-backend Worker claims are gone: `AiNative/docs/agents/README.md`, `AiNative/docs/systems/feature-loop.md`, `AiNative/docs/knowledge/setup/cursor-setup.md` (slash-command list includes `claude-harness`), `AiNative/docs/knowledge/setup/hermes-readiness.sh` (skill presence list includes `claude-harness` SKILL/worker-contract/spawn), and add Cursor command `AiNative/.cursor/commands/claude-harness.md` (same stub shape as `pi-harness.md` / `antigravity-harness.md`; do not rewrite host skill symlinks — `link-host-skills.sh` already links every agent folder) (FR-016)
- [X] T025 [US5] Add a Keep a Changelog / SemVer entry to `AiNative/CHANGELOG.md` for the third worker backend (recommend `0.6.0`); do not bump Specify/spec artifacts (FR-020)

**Checkpoint**: Operator-facing docs name Claude beside Pi and Antigravity; changelog records the behavior change.

---

## Phase 8: Polish & Cross-Cutting Concerns

**Purpose**: Prove the gate from `quickstart.md` and freeze sibling spawn files.

- [X] T026 Run `node AiNative/docs/agents/claude-harness/claude-spawn.mjs --self-test` and expect `SELFTEST: ok`; `rg` on that wrapper must not import `@anthropic-ai/claude-agent-sdk` or `claude-agent-sdk` (quickstart §1)
- [X] T027 [P] Run `bash AiNative/docs/agents/ready/scripts/ready-check.selftest.sh` and `bash AiNative/docs/agents/speckit-ready/scripts/ready-check.selftest.sh`; both exit 0 (quickstart §3)
- [X] T028 [P] Run the wrapper-only and docs `rg` commands from `specs/003-claude-sdk-worker/quickstart.md` §§2, 4, 7; spawn instructions name `claude-spawn.mjs`; zero leftover exclusive “only pi or antigravity” Worker claims in in-scope files; `claude-harness` appears in hermes-readiness and cursor-setup lists
- [X] T029 Confirm `git diff --name-only -- AiNative/docs/agents/pi-harness/pi-spawn.mjs AiNative/docs/agents/antigravity-harness/agy-spawn.py` is empty (or no behavior hunks) and `AiNative/CHANGELOG.md` newest version mentions `claude-harness` / `claude -p` / `WORKER: claude` (quickstart §§5–6; FR-018, FR-020)

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies
- **Foundational (Phase 2)**: Depends on Setup — BLOCKS all user stories
- **US1 (Phase 3)**: Depends on Foundational — MVP CLI print spawn
- **US2 (Phase 4)**: Depends on US1 argv builder in the same wrapper file (sequential, not parallel with US1)
- **US3 (Phase 5)**: Depends on Foundational only (Ready scripts; can run in parallel with remaining wrapper work)
- **US4 (Phase 6)**: Depends on US1–US2 (same `claude-spawn.mjs`; STATUS/timeout/contract on the CLI argv)
- **US5 (Phase 7)**: Can start after Foundational for wording, but should land after US3–US4 so docs match shipped flags
- **Polish (Phase 8)**: After desired stories

### User Story Dependencies

- **User Story 1 (P1)**: After Phase 2 — MVP
- **User Story 2 (P1)**: After US1 (same file: `claude-spawn.mjs`)
- **User Story 3 (P1)**: After Phase 2 — independent files (ready copies)
- **User Story 4 (P1)**: After US2 (same wrapper)
- **User Story 5 (P1)**: After behavior exists; docs files are parallel among themselves except changelog last

### Within Each User Story

- Self-test / ready-selftest assertions first where listed; confirm fail; then implementation
- Argv builder before STATUS reconstruct
- Ready-check.sh after selftest rewrite
- Docs after (or in lockstep with) behavior
- Story complete before next wrapper story

### Parallel Opportunities

- T002 with T001
- T013 and T014 (two selftest files)
- US3 (ready) vs US1/US2/US4 (wrapper) after Phase 2 if two implementers
- T021–T024 different doc files
- T027 and T028 in Polish

Do **not** mark sequential `claude-spawn.mjs` tasks `[P]`.

---

## Parallel Example: User Story 3

```bash
# After Phase 2, two ready selftest files together:
Task: "Add Claude PATH/auth/alias cases in AiNative/docs/agents/ready/scripts/ready-check.selftest.sh"
Task: "Add the same cases in AiNative/docs/agents/speckit-ready/scripts/ready-check.selftest.sh"
```

## Parallel Example: User Story 5

```bash
Task: "Write claude-harness SKILL.md / rule.md / AGENTS.md"
Task: "Update speckit-orchestrate SKILL.md / AGENTS.md / rule.md"
Task: "Update both ready SKILL.md + AGENTS.md"
Task: "Update README.md, feature-loop.md, cursor-setup.md, hermes-readiness.sh, Cursor command"
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Phase 1 Setup
2. Phase 2 Foundational (CRITICAL)
3. Phase 3 US1 (`claude -p` always; text vs stream-json)
4. **STOP and VALIDATE**: `claude-spawn.mjs --self-test` TF-1/TF-2 assertions
5. Then US2 (edit/scout) before treating implement jobs as unattended-complete

### Incremental Delivery

1. Setup + Foundational → launcher execs CLI, no language SDK
2. US1 → unattended print/headless (MVP)
3. US2 → tools actually run on edit jobs
4. US3 → Ready identity is the CLI + auth evidence
5. US4 → parent monitoring/STATUS/timeout parity with Pi
6. US5 → docs + changelog 0.6.0
7. Polish → `quickstart.md`

### Parallel Team Strategy

1. Together: Setup + Foundational
2. Then: Developer A continues `claude-spawn.mjs` (US1 → US2 → US4); Developer B Ready copies (US3); Developer C docs (US5) after flags stabilize
3. Polish is sequential on the combined tree

---

## Notes

- [P] tasks = different files, no incomplete-task dependencies
- Do not keep sample template tasks
- `worker-contract.md` is appended via official CLI flags, not inlined as the only identity
- Official CLI: https://code.claude.com/docs/en/cli-reference
- Commit plan (if parent Ship commits): wrapper → ready → docs/changelog; never commit `.agent/` run dirs or secrets
- Avoid: hybrid SDK/Managed Agents fallback, default `--bare`, `--dangerously-skip-permissions` / `bypassPermissions`, inventing `--max-turns`/`--max-budget-usd`, parent exec of `claude -p`, Ready version floor, changing default worker off `antigravity`

---

## Phase 9: Convergence

- [X] T030 Update compact report template in `AiNative/docs/agents/ready/SKILL.md` to include `claude` in `WORKER: pi | antigravity | claude` per FR-016 (partial)
- [X] T031 Update compact report template in `AiNative/docs/agents/speckit-ready/SKILL.md` in lockstep to include `claude` in `WORKER: pi | antigravity | claude` per FR-016 (partial)
- [X] T032 Update worker runtime text in `AiNative/docs/agents/speckit-orchestrate/SKILL.md` to remove exclusive "Pi or Antigravity SDK" phrasing and explicitly name Claude / `claude-harness` per US5 (partial)
