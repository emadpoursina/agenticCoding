# Feature Specification: Claude SDK worker harness

**Feature Branch**: `claude-sdk-worker`

**Spec Directory**: `003-claude-sdk-worker`

**Created**: 2026-10-31

**Status**: Draft

**Input**: User description: "right now we have pi and antigravity controle with sdk I want the samething for the claude make sure you search interent and official docs too." Intent: add a Claude worker control path parallel to Pi and Antigravity SDK worker harnesses (spawn/harness skill, `SPECKIT_WORKER` / git config `speckit.worker` integration, orchestrate docs).

## Clarifications

### Session 2026-10-31

- Q: For unattended implement/edit jobs, which Claude Code permission mode should the wrapper pass so tools actually run without a human? → A: `--permission-mode auto` (option B; classifier reviews tools; Anthropic’s `-p` recommendation). Not `--dangerously-skip-permissions` / `bypassPermissions`.
- Q: What should Ready treat as enough unattended Claude auth without spending a model turn? → A: Env tokens (`ANTHROPIC_API_KEY` / `CLAUDE_CODE_OAUTH_TOKEN` / `ANTHROPIC_AUTH_TOKEN` / `apiKeyHelper`) plus evidence of an existing local CLI login; no model call; fail if none of those exist (option C).
- Q: Should Worker `claude -p` jobs load the project/user Claude tree (`CLAUDE.md`, skills, MCP, hooks) or run `--bare`? → A: Never default `--bare`; load project/user config (option A).
- Q: Should Ready fail if the installed `claude` CLI is older than the flags this feature relies on? → A: No version floor in Ready; omit unsupported flags; fail closed only if a required flag is rejected (option B).
- Q: Should the wrapper pass official print-mode spend or turn caps (`--max-budget-usd`, `--max-turns`), or only the existing optional wrapper `--timeout` like Pi? → A: No default CLI caps; only optional wrapper `--timeout` (option A).

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Operator can run Spec Kit Worker stages on Claude (Priority: P1)

An operator who already can dispatch implement/converge/change/job to Pi or Antigravity can select Claude the same way: environment `SPECKIT_WORKER=claude` or local git config `speckit.worker claude`. Ready reports `WORKER: claude`. The parent still only launches a harness wrapper (same shape as `pi-spawn.mjs` / `agy-spawn.py`). That wrapper runs official Claude Code **print / non-interactive** mode (`claude -p` / `--print`). Short jobs return final text. Long jobs stream events to disk. The parent never starts the interactive Claude TUI, never calls `claude -p` itself, never uses Anthropic Managed Agents, and never drives the Messages/Client SDK tool loop.

**Why this priority**: Without a third worker backend, operators who want Claude for Worker-profile stages have no legal path inside speckit-orchestrate; Pi and Antigravity already work.

**Independent Test**: Set worker to Claude, run Ready, then spawn a short `--print` job and a long job through the wrapper only. Child argv always includes `-p`/`--print`. Parent logs show only the wrapper. Child stdin is not a TTY.

**Acceptance Scenarios**:

1. **Given** `SPECKIT_WORKER=claude` (or aliases below) or `git config speckit.worker claude`, **When** Ready runs, **Then** the compact report includes `WORKER: claude` and `worker-runtime` for that backend only (Pi and Antigravity are not required for this run).
2. **Given** Ready reported `WORKER: claude`, **When** implement/converge/change/job run, **Then** the parent spawns only the Claude harness wrapper with `--cwd` set to `WORKTREE` and the resolved `--model`; it does not exec `claude` itself and does not launch a host Task for those stages.
3. **Given** a short job, **When** the parent invokes the wrapper with `--print`, **Then** the wrapper executes `claude -p` with default text output and does not start the TUI.
4. **Given** a long job, **When** the parent invokes the wrapper without `--print`, **Then** the wrapper still executes `claude -p` and adds `--output-format stream-json`, writing those events under the run directory (`events.jsonl` plus `status.json` / `report.json`).
5. **Given** either spawn path, **When** the child starts, **Then** stdin is ignored (not a TTY); `--bg` / `--background` and a cloud-task `--cloud` description are absent (`-p` rejects those combinations). Prompt is passed as the print argument, not as interactive stdin.

---

### User Story 2 - Edit jobs write; scout jobs stay non-writing (Priority: P1)

Implement/fix jobs must use file and shell tools without waiting for a human. Official Claude Code print mode, when no permission mode is set (v2.1.302+), starts in Manual and **denies** calls that would prompt — a silent no-op that can still exit 0. Edit jobs therefore pass `--permission-mode auto` (classifier reviews tools; Anthropic’s unattended `-p` recommendation). They do not use `--dangerously-skip-permissions` / `--permission-mode bypassPermissions`. Scout jobs stay plan/read-only.

**Why this priority**: A worker that exits cleanly after denying tools looks like success while the job did nothing.

**Independent Test**: Default (edit) spawn includes `--permission-mode auto` and does not include skip-permissions / `bypassPermissions`. Scout spawn uses `--permission-mode plan` and does not use `auto`. Optional flags the installed CLI rejects are omitted. A required flag that the CLI rejects fails closed.

**Acceptance Scenarios**:

1. **Given** a default (edit) job, **When** the wrapper starts Claude, **Then** argv includes `--permission-mode auto` and does **not** include `--dangerously-skip-permissions` or `--permission-mode bypassPermissions`.
2. **Given** an installed CLI that rejects an optional flag (for example `--permission-prompts none`), **When** an edit job starts, **Then** that flag is omitted and the required `--permission-mode auto` is still passed. Ready does not fail solely because the CLI is older than a documented flag era.
3. **Given** a `--scout` job, **When** the wrapper starts Claude, **Then** argv includes `--permission-mode plan` and does **not** include `--permission-mode auto`, `--dangerously-skip-permissions`, or `bypassPermissions`.
4. **Given** an edit spawn whose installed CLI rejects the required `--permission-mode auto` flag, **When** the wrapper starts the job, **Then** it fails closed: no Manual-mode retry, no Client SDK fallback, no Managed Agents fallback.

---

### User Story 3 - Ready fails closed on missing Claude CLI, not on missing language SDK (Priority: P1)

Ready’s `worker-runtime` check for Claude must prove the official `claude` CLI is on PATH and that unattended auth is present, not that `pip install claude-agent-sdk` or `npm install @anthropic-ai/claude-agent-sdk` succeeded. Pi and Antigravity checks stay as they are. Unknown worker values still fail. Default worker remains `antigravity` when unset.

**Why this priority**: The Agent SDK libraries run the Claude Code binary; a package install without `claude` on PATH cannot run Worker stages.

**Independent Test**: Ready-check selftests gain Claude PATH/auth cases. Missing `claude`, or missing all of env tokens / `apiKeyHelper` / local CLI-login evidence, blocks Claude. Ready does not call the model and does not fail on CLI version alone. Importing the Python/TS Agent SDK is neither required nor sufficient.

**Acceptance Scenarios**:

1. **Given** `SPECKIT_WORKER=claude` (or alias), **When** `claude` is not on PATH, **Then** Ready is blocked with `worker-runtime: fail` and a fix that tells the operator to install Claude Code CLI and put `claude` on PATH — not to `pip install claude-agent-sdk` as the runtime.
2. **Given** `claude` on PATH, **When** none of `ANTHROPIC_API_KEY`, `CLAUDE_CODE_OAUTH_TOKEN`, `ANTHROPIC_AUTH_TOKEN`, `apiKeyHelper`, or evidence of an existing local CLI login is present, **Then** Ready is blocked with a fix pointing at official API-key or CLI login docs; Ready does **not** spend a model turn to probe.
3. **Given** `claude` on PATH and auth detectable, **When** the npm/Python Agent SDK packages are not installed, **Then** Ready still passes worker-runtime for Claude.
4. **Given** unset `SPECKIT_WORKER` and unset git config, **When** Ready runs, **Then** default remains `antigravity` (this feature does not change the default backend).
5. **Given** `SPECKIT_WORKER=not-a-backend`, **When** Ready runs, **Then** it still fails unknown worker, and the fix text lists `pi`, `antigravity`, and `claude`.

---

### User Story 4 - Wrapper contract matches Pi/Antigravity monitoring (Priority: P1)

The parent-facing launcher is a new Claude harness wrapper. Run directories, `status.json`, `report.json`, worker-contract text, required `--model`, and optional `--effort` / `--timeout` / `--print` / `--scout` / `--conversation-id` match the existing harness contract. Official CLI supports `--append-system-prompt-file`, so the contract file is appended that way rather than inlined only as a prompt prefix.

**Why this priority**: Downstream stages already poll wrapper files. A different parent API would break orchestrate.

**Independent Test**: Same wrapper flags as siblings (`--name`, `--cwd`, `--model` required, optional `--effort`, `--timeout`, `--print`, `--scout`). Missing `--model` exits 2 without starting `claude`. Compact wrapper stdout still `RUN_DIR=` / `STATUS_FILE=` / `LIFECYCLE=` / `REPORT_FILE=`.

**Acceptance Scenarios**:

1. **Given** a spawn without `--model`, **When** the wrapper parses args, **Then** it exits 2 and does not start `claude`.
2. **Given** a valid spawn, **When** `claude` is invoked, **Then** `--model` is passed through; if `--effort` was set, it is passed as `claude --effort`; cwd of the child is the wrapper `--cwd` (feature worktree).
3. **Given** a valid spawn, **When** the prompt is assembled, **Then** `worker-contract.md` is supplied via `--append-system-prompt-file` (official CLI) and the job text is the print prompt. If the installed CLI rejects the file flag, the wrapper may fall back to `--append-system-prompt` with the same file contents; it must not drop the contract.
4. **Given** a valid spawn with no `--conversation-id`, **When** `claude` is invoked, **Then** the run is isolated (`--no-session-persistence` when the CLI accepts it). No `--continue`. Interactive `--resume` without an id is never used.
5. **Given** `--conversation-id <id>`, **When** `claude` is invoked, **Then** the wrapper maps it to official `--resume <id>` (print mode) and does not open a session picker.
6. **Given** a completed run, **When** the parent reads the run dir, **Then** `.agent/claude/<job-name>/<run-id>/{status.json,report.json,events.jsonl,stderr.log}` plus `latest.json` exist; lifecycle vs worker STATUS semantics match Pi/Antigravity.
7. **Given** a stream-json job, **When** `report.json` is written, **Then** `workerStatus` comes from assistant text reconstructed from `events.jsonl` (final `result` message text when present); the parent still does not ingest that file.
8. **Given** `claude -p` exits non-zero, **When** the wrapper finalizes, **Then** `lifecycle` is `failed` even if assistant text contained `STATUS: ok`.

---

### User Story 5 - Orchestrate and host docs list Claude as a third worker (Priority: P1)

Canonical speckit-orchestrate, ready (both copies), agents README, feature-loop, Cursor command, and host-skill linking treat Claude as a Worker backend beside Pi and Antigravity. The dispatcher still does not implement stages. Workers still do not commit, push, or open PRs unless a job prompt explicitly says so.

**Why this priority**: Operators and later agents follow those files; omitting Claude from resolution tables would leave a working wrapper unused.

**Independent Test**: Search those files for worker resolution. Claude is named. Claims that only Pi and Antigravity exist are gone. Pi and Antigravity spawn instructions remain accurate.

**Acceptance Scenarios**:

1. **Given** `speckit-orchestrate` Worker SDK resolution, **When** an operator reads it, **Then** order is still env → git config → default `antigravity`, and accepted values include `claude` with aliases `claude-code`, `anthropic`.
2. **Given** `WORKER: claude`, **When** Worker-profile stages run, **Then** the parent is told to follow `claude-harness` (canonical `AiNative/docs/agents/claude-harness/`) the same way it follows `pi-harness` / `antigravity-harness`.
3. **Given** host skill linking, **When** a new agent folder is added, **Then** `link-host-skills.sh` / Cursor command wrapping is documented the same way as the other harnesses.
4. **Given** a delivered change set, **When** versioning is updated, **Then** `AiNative/CHANGELOG.md` records the new backend under the repo’s existing Keep a Changelog scheme.

---

### Edge Cases

- `claude` missing at spawn time (Ready should have blocked; wrapper still fails loudly with no language-SDK fallback).
- Auth expired after Ready: child stdin ignored; print flags always present so a login TUI cannot attach; wrapper timeout ends a hung process (SIGINT then SIGTERM then SIGKILL, matching official “SIGINT ends the turn / SIGTERM exits 143”).
- Installed CLI rejects required `--permission-mode auto` (edit) or `--permission-mode plan` (scout): that job fails closed. Optional flags the CLI rejects are omitted instead.
- Print mode with no permission mode (Manual deny): must not be the edit-job path; edit jobs always pass `--permission-mode auto`.
- `--bg` / `--cloud` with a new-task description combined with `-p`: never passed (official conflict).
- Wrapper `--print` (text) vs long job (`--output-format stream-json`): both still pass `-p`; they differ only in output format. Stream-json jobs pass `--verbose` so events are complete enough to reconstruct the final result.
- `--timeout` omitted: wrapper does not invent a timeout (same as Pi). Claude’s own background-wait ceiling is not treated as a Spec Kit job timeout. The wrapper MUST NOT default `--max-turns` or `--max-budget-usd`.
- `--timeout` set: wrapper kill timer fires; optional forwarding of a CLI duration flag only if official CLI names one for print mode. Spend/turn caps are still not defaulted.
- `--effort` omitted: not passed; CLI default applies.
- Worker process exits 0 after a turn that omitted `STATUS: ok|stuck|blocked`: `reportValid` false; not job success.
- Parallel jobs require distinct `--name`; run dirs under `.agent/claude/`.
- `--bare` is **never** the default for Worker stages (edit or scout). Jobs load project and user config (`CLAUDE.md`, skills, MCP, hooks). Isolation is `--no-session-persistence` plus ignored stdin, not `--bare`.
- Root/sudo: wrapper still MUST NOT pass `bypassPermissions`. If the CLI refuses `--permission-mode auto` as root, the wrapper surfaces that failure and does not retry as Manual.
- Python/TS Agent SDK `query()` / `ClaudeSDKClient` are **not** the parent spawn API. A future internal implementation may use those libraries only if they still exec the same Claude Code binary; Ready still checks `claude` on PATH.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: Spec Kit MUST offer a third Worker backend identity `claude` (aliases: `claude-code`, `anthropic`). Resolution order MUST remain: `SPECKIT_WORKER`, else `git config speckit.worker`, else default `antigravity`.
- **FR-002**: The Claude worker runtime MUST be official Claude Code non-interactive print mode (`claude -p` / `--print`) as documented in Anthropic’s Agent SDK CLI / headless docs. Worker runs MUST NOT use the Anthropic Messages/Client SDK as the agent loop, MUST NOT use Managed Agents hosted sessions as the Spec Kit worker, and MUST NOT launch the Claude TUI.
- **FR-003**: Cursor and Hermes MUST spawn Claude Worker jobs only through a new harness wrapper under `AiNative/docs/agents/claude-harness/` (skill + contract + spawn script, same file contract as Pi/Antigravity). The parent MUST NOT exec `claude` itself.
- **FR-004**: The wrapper MUST never launch bare `claude` (no `-p`/`--print`). It MUST NOT pass `--bg`/`--background`, `--prompt-interactive`, or a `--cloud` task-description spawn with `-p`.
- **FR-005**: Wrapper `--print` MUST run `claude -p` with default text output (final response on stdout).
- **FR-006**: Wrapper jobs without `--print` MUST run `claude -p --output-format stream-json` (with `--verbose` so the stream includes the final result) and persist raw stdout lines to `events.jsonl`.
- **FR-007**: The wrapper MUST start `claude` with stdin ignored (not a TTY) and MUST pass the job as the print prompt. It MUST NOT wait on `--input-format stream-json` for parent-driven bidirectional input.
- **FR-008**: Edit jobs (default, no `--scout`) MUST pass `--permission-mode auto` and MUST NOT pass `--dangerously-skip-permissions` or `--permission-mode bypassPermissions`. Optional flags (including `--permission-prompts none`) MUST be omitted when the installed CLI rejects them. If the installed CLI rejects the required `--permission-mode auto` flag, the wrapper MUST fail closed (no Manual retry, no Client SDK / Managed Agents fallback).
- **FR-009**: Scout jobs (`--scout`) MUST pass `--permission-mode plan` and MUST NOT pass `--permission-mode auto`, `--dangerously-skip-permissions`, or `bypassPermissions`.
- **FR-010**: `--model` remains required. Missing `--model` MUST exit 2 without starting `claude`. Optional `--effort` MUST be forwarded as `claude --effort` when present. Optional `--conversation-id` MUST map to `claude --resume <id>` in print mode; default MUST be a fresh isolated run (`--no-session-persistence` when supported; never interactive resume picker; never `--continue` unless that id mapping requires it).
- **FR-011**: The wrapper MUST attach `worker-contract.md` via `--append-system-prompt-file` (fallback `--append-system-prompt` with the same text). Contract meaning MUST match Pi/Antigravity (one job, compact STATUS report, no unsolicited commit/push/SSH).
- **FR-012**: Wrapper `--timeout` (seconds or `Nms`) MUST start the wrapper’s own kill timer. On expiry the wrapper MUST send SIGINT, then SIGTERM, then SIGKILL if the process remains (Claude Code documents SIGINT to end a turn and SIGTERM as exit 143). Omitting `--timeout` MUST NOT add a wrapper-invented timeout. The wrapper MUST NOT pass default CLI spend/turn caps (`--max-budget-usd`, `--max-turns`).
- **FR-013**: Run directory layout MUST be `.agent/claude/<job-name>/<run-id>/{status.json,report.json,events.jsonl,stderr.log}` plus `latest.json`. Lifecycle vs worker STATUS MUST match existing harnesses: process outcome vs parsed `STATUS: ok|stuck|blocked`. Compact wrapper stdout MUST stay `RUN_DIR=` / `STATUS_FILE=` / `LIFECYCLE=` / `REPORT_FILE=`.
- **FR-014**: Ready `worker-runtime` for Claude MUST require `claude` on PATH and detectable unattended auth without a model call. Detectable auth is any of: `ANTHROPIC_API_KEY`, `CLAUDE_CODE_OAUTH_TOKEN`, `ANTHROPIC_AUTH_TOKEN`, `apiKeyHelper`, or evidence of an existing local CLI login. If none of those exist, Ready MUST fail. It MUST NOT require installing `claude-agent-sdk` / `@anthropic-ai/claude-agent-sdk`. It MUST NOT call the model. Cloud-provider env (`CLAUDE_CODE_USE_BEDROCK` / Vertex / Foundry) is not required for Ready.
- **FR-015**: Ready-check scripts and selftests in both `AiNative/docs/agents/ready/` and `AiNative/docs/agents/speckit-ready/` MUST cover Claude PATH/auth success and failure, and MUST keep existing Pi, Antigravity, unknown, and default-antigravity cases.
- **FR-016**: Canonical docs MUST name the Claude backend: `claude-harness` (`SKILL.md`, `rule.md`, `AGENTS.md`, wrapper comments), `speckit-orchestrate` (`SKILL.md`, `AGENTS.md`, `rule.md`), both ready `SKILL.md` files, `docs/agents/README.md`, `docs/systems/feature-loop.md`, Cursor command under `AiNative/.cursor/commands/`, and install/link docs that already list `pi-harness` / `antigravity-harness` (including `hermes-readiness.sh` skill presence list and `cursor-setup.md` slash-command list).
- **FR-017**: If `claude` cannot be started, the wrapper MUST fail without falling back to Pi, Antigravity, a host Task, Client SDK, or Managed Agents.
- **FR-018**: Pi and Antigravity harness behavior MUST remain unchanged except for shared worker-resolution lists that gain `claude`.
- **FR-019**: This change MUST NOT install Anthropic packages as a required operator step, MUST NOT change operator keys, and MUST NOT switch the default worker off `antigravity`.
- **FR-020**: Delivered behavior change MUST be recorded in `AiNative/CHANGELOG.md` using the existing Keep a Changelog / SemVer scheme (implement stage; specify does not bump).
- **FR-021**: Worker STATUS MUST be parsed from assistant text. Text-mode MUST use captured CLI stdout. Stream-json jobs MUST reconstruct that text from `events.jsonl` (prefer the final `result` payload’s text field). The parent MUST keep polling `status.json` / `report.json` and MUST NOT ingest `events.jsonl` for STATUS.
- **FR-022**: Process lifecycle MUST follow the child: exit 0 → `completed`; non-zero → `failed`; signal without timeout → `terminated`; wrapper timeout → `timed_out`. Wrapper exit 0 / `lifecycle=completed` MUST NOT be treated as job success.
- **FR-023**: `claude-harness` MUST be spawn-only (same inversion rule as Pi/Antigravity): Cursor/Hermes writes the job; Claude only executes it. The speckit-orchestrate parent MUST remain a dispatcher.
- **FR-024**: Worker-profile model resolution for Claude MUST use the same order as today (invocation `worker:` → `SPECKIT_WORKER_MODEL` → runtime default) and MUST pass the resolved value as wrapper `--model`. The harness MUST NOT pin a model slug.
- **FR-025**: Worker `claude -p` jobs MUST load project and user Claude config (`CLAUDE.md`, skills, MCP, hooks). The wrapper MUST NOT default `--bare` for edit or scout jobs.
- **FR-026**: Ready MUST NOT fail solely because the installed `claude` version is below a documented flag era (no version floor). The wrapper MUST omit flags the installed CLI rejects, and MUST fail closed only if a required flag is rejected (`-p`/`--print`, `--model`, `--permission-mode auto` on edit, `--permission-mode plan` on scout).

### Key Entities

- **Worker backend identity (`claude`)**: One of three Spec Kit Worker providers, selected per run.
- **Claude harness wrapper**: Only parent-facing launcher. Owns run dir, child argv, STATUS parse, `status.json` / `report.json`.
- **Claude Code print process (`claude -p`)**: Official headless worker (Agent SDK via CLI). Always print mode. Text vs stream-json selected by wrapper `--print`.
- **Worker contract**: Text of `worker-contract.md`, attached with official append-system-prompt file/flag.
- **Run directory**: On-disk job record under `.agent/claude/…` used by the parent to poll and summarize.
- **Ready worker-runtime**: Gate that proves `claude` on PATH and unattended auth without a billed probe.
- **Edit vs scout mode**: Edit = `--permission-mode auto` (no skip-permissions / `bypassPermissions`). Scout = `--permission-mode plan`.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: 100% of Claude worker processes started by the wrapper include print/headless flags; 0% are a bare TUI `claude`.
- **SC-002**: 100% of parent Claude Worker spawns go through the Claude harness wrapper; 0 parent Worker stages exec `claude -p` directly or launch a host Task instead.
- **SC-003**: After Ready on a machine with `claude` on PATH and detectable auth, Claude `worker-runtime` passes even if Python/npm Agent SDK packages are absent; the inverse (packages present, CLI missing or auth undetectable) fails Ready.
- **SC-004**: An edit-job that needs workspace writes and shell completes those tools under `--permission-mode auto` instead of Manual-denying them and exiting 0 with no work.
- **SC-005**: A scout job does not take the edit-job `auto` path (`--permission-mode plan`, no `auto`, no skip-permissions).
- **SC-006**: Existing wrapper monitoring files (`status.json`, `report.json`, worker STATUS parse) are present on every successful spawn layout. Stream-json runs still yield a parsed `workerStatus` without the parent reading `events.jsonl`.
- **SC-007**: An operator can switch backends with only `SPECKIT_WORKER` / `speckit.worker`; default when unset remains Antigravity.
- **SC-008**: Ready-check selftests for Claude worker-runtime pass under the new PATH/auth check and still fail when `claude` is isolated off PATH; Pi/Antigravity selftests still pass.
- **SC-009**: 100% of wrapper-spawned `claude` processes have stdin ignored and include print flags; 0 spawn hangs waiting on a login TUI when credentials are missing (timeout or immediate fail instead).
- **SC-010**: Searching in-scope orchestrate/ready/harness docs for “only pi or antigravity” as the Worker set returns zero remaining exclusive claims; Claude is listed beside them.
- **SC-011**: A first-time operator who already has Claude Code CLI authenticated can complete Ready + one short `--print` spawn using only the documented wrapper flags, without installing a second coding-agent product for that run.

## Assumptions

- **Official surface (researched 2026-10-31)**: Anthropic documents the Agent SDK as Python (`claude-agent-sdk`, `query()` / `ClaudeSDKClient`) and TypeScript (`@anthropic-ai/claude-agent-sdk`), and documents the **same agent loop** via CLI `claude -p` with `--output-format text|json|stream-json`. Sources: [Agent SDK overview](https://code.claude.com/docs/en/agent-sdk/overview), [headless / programmatic](https://code.claude.com/docs/en/headless), [CLI reference](https://code.claude.com/docs/en/cli-reference), [permission modes](https://code.claude.com/docs/en/permission-modes), [Python SDK reference](https://code.claude.com/docs/en/agent-sdk/python) (also mirrored under docs.anthropic.com).
- **CLI wrapper, not parent-imported SDK**: Pi is `pi -p` via `pi-spawn.mjs`. Antigravity is `agy -p` via `agy-spawn.py` (Python SDK is explicitly **not** the worker runtime after `002-agy-cli-backend`). Claude follows that pattern: wrapper execs `claude -p`. Language of the wrapper is an implement-stage choice (Node like Pi or Python like Antigravity); the spec does not require npm/pip Agent SDK packages at Ready time.
- **Not in v1**: Managed Agents (`ant` CLI / hosted sessions), Messages API Client SDK tool loops, Claude Desktop (`--desktop`), `claude --bg`, cloud task create with `--cloud`, interactive `/login` TUI, changing default worker to Claude.
- **Auth**: Ready treats unattended auth as present if any of `ANTHROPIC_API_KEY`, `CLAUDE_CODE_OAUTH_TOKEN`, `ANTHROPIC_AUTH_TOKEN`, `apiKeyHelper`, or evidence of an existing local CLI login is found. It does not call the model and fails if none exist. Bedrock/Vertex/Foundry env is not a Ready requirement. Ready does not pass `--bare` (bare mode ignores OAuth/keychain and requires an API key). Anthropic forbids third-party products from offering claude.ai login; this harness is an operator-local spawn, not a hosted product login.
- **Permissions**: Official print mode without a permission mode can start Manual and deny prompting tools. Edit jobs pass `--permission-mode auto`. Scout uses `plan`. Skip-permissions / `bypassPermissions` are out of this worker’s argv.
- **`--bare` never default**: Worker stages load the project/user tree (including Spec Kit prompts the job names). Bare mode skips `CLAUDE.md`, skills, MCP, and hooks; isolation is `--no-session-persistence` plus ignored stdin, not `--bare`.
- **Isolation**: Default `--no-session-persistence` so parallel jobs do not share transcripts. Resume only when `--conversation-id` is explicit.
- **Stdin**: Official `-p` can read piped stdin (10MB cap). Spec Kit parent is unattended, so stdin is DEVNULL; prompt is the `-p` argument. Official note: unreadable stdin prints a warning and continues with the CLI prompt.
- **Lifecycle vs STATUS**: Child process outcome sets `lifecycle`; assistant-text parse sets `workerStatus`. Non-zero `claude` exit is `failed` even if the text included `STATUS: ok`.
- **STATUS text source**: `--print` → CLI stdout. Long jobs → assistant/result text reconstructed from persisted stream-json lines.
- **Timeout / caps**: No official print-mode `--print-timeout` in the CLI reference snapshot used for this spec; wrapper kill timer is the Spec Kit bound. No default `--max-turns` or `--max-budget-usd`. Signal order follows Claude Code docs (SIGINT then SIGTERM) plus Pi-style SIGKILL escalation.
- **CLI version**: Ready does not enforce a minimum `claude` version. Unsupported optional flags are omitted. A rejected required flag fails closed at spawn.
- **Docs scope**: Canonical AiNative copies listed in FR-016. Host symlinks are produced by existing `link-host-skills.sh`, not by hand-copying skill bodies.
- **Changelog**: Implement bumps `AiNative/CHANGELOG.md`. Specify does not bump versions.
- **Out of scope stays out**: Changing Pi/Antigravity child argv; package installs; operator key changes; making the parent implement stages; Cursor Task as the Claude worker; rewriting speckit-orchestrate into plan-orchestrator.
