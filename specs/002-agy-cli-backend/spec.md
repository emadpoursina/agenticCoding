# Feature Specification: Antigravity CLI worker backend

**Feature Branch**: `skip`

**Spec Directory**: `002-agy-cli-backend`

**Created**: 2026-10-26

**Status**: Draft

**Input**: User description: "skip" (operator skip flag). Full intent: switch the Antigravity worker backend from the Python SDK (`google.antigravity.Agent`) to the official `agy` CLI headless path, matching the Pi harness pattern, so `SPECKIT_WORKER=antigravity` actually runs `agy -p` (never the TUI).

## Clarifications

### Session 2026-10-26

- Q: For long jobs that write stream-json events, where does the wrapper get the assistant text used to parse `STATUS: ok|stuck|blocked`? → A: Text-mode jobs parse captured CLI stdout; stream-json jobs reconstruct assistant text from `events.jsonl`. The parent still polls `status.json` / `report.json` and does not ingest the event file.
- Q: When the operator sets wrapper `--timeout`, who actually stops a hung job? → A: Dual enforcement: forward `--print-timeout` to `agy` and keep the wrapper’s own SIGTERM then SIGKILL, matching Pi, so a CLI that ignores print-timeout cannot hang orchestrate.
- Q: If `agy -p` exits non-zero after a turn that still printed `STATUS: ok`, what is process lifecycle versus worker STATUS? → A: Lifecycle follows the process (non-zero exit → `failed`); worker STATUS is parsed independently. Exit 0 / `lifecycle=completed` is not job success; the parent still reads `reportValid` / `workerStatus`.
- Q: If the installed `agy` rejects `--dangerously-skip-permissions`, may the wrapper still run the edit job? → A: Fail closed. No Ask-policy retry, no Python SDK fallback. A replacement flag is allowed only if official headless docs name that equivalent.
- Q: How does spawn avoid hanging on an interactive login if CLI credentials expire after Ready passed? → A: Child stdin is ignored (not a TTY), argv always includes print/headless flags, and `--prompt-interactive` is never passed. Do not probe `agy models` on every spawn; if the CLI still blocks, the timeout path ends the job.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Operator gets a real unattended Antigravity worker (Priority: P1)

An operator sets `SPECKIT_WORKER=antigravity` (or uses the default) and runs Spec Kit. The parent still launches only the existing wrapper (`agy-spawn.py`). That wrapper runs official CLI print/headless mode. Short jobs return final text. Long jobs stream events to disk. The parent never starts the interactive TUI and never calls `agy -p` itself.

**Why this priority**: Today wrapper `--print` is a quiet SDK flag and does not exec `agy`. The default worker therefore does not match the documented “headless CLI like Pi” intent, and unattended runs can soft-deny tools while still exiting 0.

**Independent Test**: Spawn via the wrapper with `--print` and without it. Process inspection / argv of the child shows `agy` with `-p`/`--print` in both cases; never a bare `agy`. Short jobs use text output. Long jobs use stream-json with events written under the run directory. Parent logs show only the wrapper spawn. Child stdin is not a TTY.

**Acceptance Scenarios**:

1. **Given** the parent must run a short Antigravity job, **When** it invokes the wrapper with `--print`, **Then** the wrapper executes `agy -p` (alias of `--print`) with text output and does not start the TUI.
2. **Given** the parent must run a long Antigravity job, **When** it invokes the wrapper without `--print`, **Then** the wrapper still executes `agy -p` and adds `--output-format stream-json`, writing those events on disk under the run directory (`events.jsonl` plus existing `status.json` / `report.json`).
3. **Given** either spawn path, **When** the job starts, **Then** the child command always includes print/headless flags; a bare `agy` with no `-p`/`--print` is never launched.
4. **Given** Spec Kit orchestrate with `WORKER: antigravity`, **When** implement/converge/change/job stages run, **Then** the parent still only spawns `agy-spawn.py`; it does not exec `agy -p` itself.
5. **Given** either spawn path, **When** the child starts, **Then** its stdin is ignored (not a TTY) so an expired-credential login prompt cannot attach; `--prompt-interactive` is absent.

---

### User Story 2 - Edit jobs write; scout jobs stay non-writing (Priority: P1)

Implement/fix jobs must actually use shell and file tools without waiting for a human. Scout jobs must stay read-only / plan-only. Headless without auto-approve currently soft-denies shell and can still exit 0, which looks like success while the job did nothing.

**Why this priority**: A worker that exits 0 after soft-denying tools is worse than a loud failure.

**Independent Test**: An edit-job spawn includes `--dangerously-skip-permissions` (or an official-docs replacement) and `--mode accept-edits`. A scout spawn includes `--mode plan` and does not skip permissions for writes. Rejected skip-permissions with no replacement fails closed.

**Acceptance Scenarios**:

1. **Given** a default (edit) job, **When** the wrapper starts `agy`, **Then** the argv includes `--dangerously-skip-permissions` (or the documented equivalent auto-approve) and `--mode accept-edits`.
2. **Given** a `--scout` job, **When** the wrapper starts `agy`, **Then** the argv includes `--mode plan` and does not include skip-permissions.
3. **Given** an edit job that needs shell or file writes, **When** it finishes, **Then** those tools are not silently soft-denied as the default Ask policy; lifecycle/exit still reflect a real completed turn, and worker STATUS is parsed from assistant text (text-mode stdout, or reconstructed from `events.jsonl` for stream-json).
4. **Given** an edit spawn whose installed `agy` rejects `--dangerously-skip-permissions` (and official docs name no replacement), **When** the wrapper starts the job, **Then** it fails closed: no Ask-policy retry and no Python SDK fallback.

---

### User Story 3 - Ready fails closed on missing CLI, not missing Python SDK (Priority: P1)

Ready’s `worker-runtime` check for Antigravity must prove the CLI is on PATH and authenticated (`agy models`), not that `from google.antigravity import Agent` works. Existing ready-check selftests must match the new check.

**Why this priority**: Ready currently can pass on a PyPI SDK install while the CLI path this feature requires is missing, or fail on a CLI-only machine that is already authenticated.

**Independent Test**: Run ready-check selftests. Missing `agy` or failed `agy models` blocks Antigravity. Importing `google.antigravity` is neither required nor sufficient.

**Acceptance Scenarios**:

1. **Given** `SPECKIT_WORKER=antigravity` (or default), **When** `agy` is not on PATH, **Then** Ready is blocked with `worker-runtime: fail` and a fix that tells the operator to install/put `agy` on PATH — not `pip install google-antigravity`.
2. **Given** `agy` on PATH, **When** `agy models` fails (unauthenticated or broken CLI), **Then** Ready is blocked; Gemini API key or Vertex env alone does not pass worker-runtime.
3. **Given** `agy` on PATH and `agy models` succeeds, **When** the Python package `google.antigravity` is not importable, **Then** Ready still passes worker-runtime for Antigravity.
4. **Given** the ready-check selftests, **When** they run after this change, **Then** the Antigravity cases isolate PATH/`agy models` (not SDK import) and still cover missing-pi, unknown worker, and default-antigravity.

---

### User Story 4 - Wrapper contract stays the parent’s monitoring surface (Priority: P1)

The Cursor/Hermes-facing launcher remains `agy-spawn.py`. Run directories, `status.json`, `report.json`, worker-contract behavior, required `--model`, and optional `--effort` / `--timeout` stay. The CLI has no `--append-system-prompt`, so the wrapper prepends `worker-contract.md` into the prompt. Slash/skill expansion from the host must stay off.

**Why this priority**: Downstream stages already poll the wrapper contract. Changing the parent API would break orchestrate.

**Independent Test**: Same wrapper flags as today (`--name`, `--cwd`, `--model` required, optional `--effort`, `--timeout`, `--print`, `--scout`). Contract text appears at the start of the prompt sent to `agy`. `--disable-slash-commands` is always present. Missing `--model` still exits 2 without starting `agy`.

**Acceptance Scenarios**:

1. **Given** a spawn without `--model`, **When** the wrapper parses args, **Then** it exits 2 and does not start `agy`.
2. **Given** a valid spawn, **When** `agy` is invoked, **Then** `--model` is passed through; if `--effort` was set, it is passed through; if `--timeout` was set, it is mapped to `agy --print-timeout`.
3. **Given** a valid spawn, **When** the prompt is assembled, **Then** the contents of `worker-contract.md` are prepended to the job prompt (CLI has no append-system-prompt flag).
4. **Given** a valid spawn, **When** `agy` is invoked, **Then** `--disable-slash-commands` is present so the worker does not expand host skills.
5. **Given** a completed run, **When** the parent reads the run dir, **Then** `status.json`, `report.json`, lifecycle vs worker STATUS, and compact wrapper stdout (`RUN_DIR=`, `STATUS_FILE=`, `LIFECYCLE=` / `REPORT_FILE=`) still exist as today.
6. **Given** a stream-json job, **When** `report.json` is written, **Then** `workerStatus` comes from assistant text reconstructed from `events.jsonl`; the parent still does not ingest that file.
7. **Given** `agy -p` exits non-zero, **When** the wrapper finalizes the run, **Then** `lifecycle` is `failed` even if assistant text contained `STATUS: ok`; the parent still uses `reportValid` / `workerStatus` for job success.

---

### User Story 5 - Docs stop saying the SDK is the worker runtime (Priority: P2)

Canonical harness, orchestrate, and ready docs/skills/rules no longer claim “there is no `agy -p`” or that the Python SDK is the worker runtime. They describe CLI headless via the wrapper, matching Pi’s “wrapper execs `pi -p`” shape.

**Why this priority**: Operators and later agents follow those files; stale “SDK is the runtime” text would undo the switch.

**Independent Test**: Search canonical AiNative agent docs for the old claims; they are gone. New text says Ready checks `agy` + `agy models`, parent only calls `agy-spawn.py`, and `--print` means `agy -p`.

**Acceptance Scenarios**:

1. **Given** `AiNative/docs/agents/antigravity-harness/` (`SKILL.md`, `rule.md`, `AGENTS.md`, wrapper comments) plus orchestrate and both ready skill copies, **When** an operator searches for “there is no `agy -p`” or “SDK is the worker runtime”, **Then** those claims are absent.
2. **Given** the same files, **When** an operator reads how to spawn, **Then** they are told never to launch bare `agy`, never to mix wrapper `--print` with `--input-format stream-json`, and never to have the parent call `agy -p` itself.
3. **Given** a delivered change set, **When** versioning is updated, **Then** `AiNative/CHANGELOG.md` records the switch under the repo’s existing Keep a Changelog scheme.

---

### Edge Cases

- `agy` missing at spawn time (Ready should have blocked; wrapper still fails loudly without falling back to the Python SDK).
- `agy models` fails (cached credentials missing); Ready blocks. Spawn does not re-run `agy models`. Child stdin is ignored and argv stays print/headless so a login TUI cannot attach; if the CLI still blocks, the dual timeout path ends the job.
- Installed `agy` rejects `--dangerously-skip-permissions` with no official replacement flag: edit job fails closed (no Ask-policy retry, no SDK fallback).
- Headless default Ask policy without skip-permissions: edit jobs must not take this path; scout/plan may, because writes are out of scope.
- CLI rejects combining `--print` with `--input-format stream-json`; the wrapper never uses that combo.
- Wrapper `--print` (text) vs long job (`--output-format stream-json`): both still pass `-p`; they differ only in output format. STATUS parse uses stdout for text mode and `events.jsonl` assistant text for stream-json.
- `--timeout` omitted: wrapper does not invent a timeout; CLI `--print-timeout` default applies (official docs: 5 minutes); wrapper kill timer is also unset.
- `--timeout` set as seconds or `Nms`: mapped to a value `agy --print-timeout` accepts, and the wrapper still SIGTERMs then SIGKILLs on expiry (Pi-matching dual enforcement).
- `agy -p` non-zero exit: `lifecycle=failed`; worker STATUS remains a separate parse of assistant text.
- `--effort` omitted: not passed; CLI default effort applies.
- `--conversation-id` / `--vertex`: see Assumptions (CLI mapping / no SDK fallback).
- Worker process exits 0 after a completed turn that omitted `STATUS: ok|stuck|blocked`: same as today (`reportValid` false); not treated as job success.
- Parallel jobs still require distinct `--name` values; run dirs stay under `.agent/antigravity/<job-name>/<run-id>/`.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The Antigravity worker runtime MUST be the official `agy` CLI in print/headless mode. Worker runs MUST NOT use `google.antigravity.Agent` / the Python SDK.
- **FR-002**: Cursor and Hermes MUST spawn Antigravity jobs only through `agy-spawn.py`. The parent MUST NOT exec `agy` or `agy -p` itself.
- **FR-003**: The wrapper MUST never launch bare `agy` (no `-p` / `--print`). Interactive TUI, `--prompt-interactive`, and `ask_user` MUST stay out of spawn argv.
- **FR-004**: Wrapper `--print` MUST run `agy -p` with default text output (final response on stdout).
- **FR-005**: Wrapper jobs without `--print` MUST run `agy -p --output-format stream-json` and persist those events on disk in the run directory.
- **FR-006**: The wrapper MUST NOT pass `--input-format stream-json` together with print/headless prompt flags (CLI rejects that combo).
- **FR-007**: Edit jobs (default, no `--scout`) MUST pass `--dangerously-skip-permissions` and `--mode accept-edits`. If the installed CLI rejects that skip-permissions flag, the wrapper MUST fail closed unless official headless docs name a replacement flag. It MUST NOT retry without auto-approve and MUST NOT fall back to the Python SDK.
- **FR-008**: Scout jobs (`--scout`) MUST pass `--mode plan` and MUST NOT pass `--dangerously-skip-permissions`.
- **FR-009**: Every spawn MUST pass `--disable-slash-commands`.
- **FR-010**: The wrapper MUST prepend `worker-contract.md` to the job prompt. It MUST NOT assume a CLI `--append-system-prompt` flag exists.
- **FR-011**: `--model` remains required. Missing `--model` MUST exit 2 without starting `agy`. Optional `--effort` MUST be forwarded as `agy --effort` when present.
- **FR-012**: Wrapper `--timeout` (seconds or `Nms`) MUST be forwarded as `agy --print-timeout` and MUST also start the wrapper’s own kill timer (SIGTERM, then SIGKILL). Omitting `--timeout` MUST NOT add a wrapper-invented timeout or `--print-timeout`.
- **FR-013**: Run directory layout and files MUST remain: `.agent/antigravity/<job-name>/<run-id>/{status.json,report.json,events.jsonl,stderr.log}` plus `latest.json`. Lifecycle vs worker STATUS semantics MUST stay as documented today.
- **FR-014**: Ready `worker-runtime` for Antigravity MUST require `agy` on PATH and a successful `agy models`. It MUST NOT require `from google.antigravity import Agent`. API key / Vertex env MUST NOT be sufficient without CLI auth.
- **FR-015**: Ready-check selftests (both `AiNative/docs/agents/ready/` and `AiNative/docs/agents/speckit-ready/` copies) MUST be updated so Antigravity failure/success cases isolate CLI PATH and `agy models`, not SDK import.
- **FR-016**: Canonical docs MUST be updated: `antigravity-harness` (`SKILL.md`, `rule.md`, `AGENTS.md`, wrapper module/doc comments), `speckit-orchestrate/SKILL.md`, and both ready `SKILL.md` files. They MUST NOT state that there is no `agy -p` or that the Python SDK is the worker runtime.
- **FR-017**: If `agy` cannot be started, the wrapper MUST fail without a Python SDK fallback (no hybrid backend).
- **FR-018**: Pi harness behavior MUST remain unchanged.
- **FR-019**: This change MUST NOT install packages or alter operator auth/keys. It MUST NOT adopt npm `antigravity-sdk` or VS Code extensions.
- **FR-020**: Delivered behavior change MUST be recorded in `AiNative/CHANGELOG.md` using the existing Keep a Changelog / SemVer scheme.
- **FR-021**: Worker STATUS MUST be parsed from assistant text as today. Text-mode (`--print`) MUST use captured CLI stdout. Stream-json jobs MUST reconstruct that text from `events.jsonl`. The parent MUST keep polling `status.json` / `report.json` and MUST NOT ingest `events.jsonl` for STATUS.
- **FR-022**: Process lifecycle MUST follow the child process, matching Pi: exit 0 → `completed`; non-zero exit → `failed`; signal without timeout → `terminated`; wrapper timeout → `timed_out`. Worker STATUS / `reportValid` stay independent. Wrapper exit 0 / `lifecycle=completed` MUST NOT be treated as job success.
- **FR-023**: The wrapper MUST start `agy` with stdin ignored (not a TTY). It MUST NOT pass `--prompt-interactive` or `ask_user`. It MUST NOT run `agy models` on every spawn.

### Key Entities

- **Wrapper spawn (`agy-spawn.py`)**: Only Cursor/Hermes-facing launcher. Owns run dir, child argv, STATUS parse, `status.json` / `report.json`.
- **CLI print process (`agy -p`)**: Official headless worker. Always print mode. Text vs stream-json selected by wrapper `--print`.
- **Worker contract**: Text of `worker-contract.md`, prepended to the user prompt because the CLI has no append-system-prompt flag.
- **Run directory**: On-disk job record under `.agent/antigravity/…` used by the parent to poll and summarize.
- **Ready worker-runtime**: Gate that proves Antigravity CLI presence and cached CLI auth via `agy models`.
- **Edit vs scout mode**: Edit = `accept-edits` + skip-permissions. Scout = `plan` without skip-permissions.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: 100% of Antigravity worker processes started by the wrapper include print/headless flags; 0% are a bare TUI `agy`.
- **SC-002**: 100% of parent Antigravity spawns go through `agy-spawn.py`; 0 parent stages exec `agy -p` directly.
- **SC-003**: After Ready on a CLI-authenticated machine with `agy` on PATH, Antigravity `worker-runtime` passes even if the Python SDK is absent; the inverse (SDK present, CLI missing or `agy models` failing) fails Ready.
- **SC-004**: An edit-job that needs shell or workspace writes completes those tools instead of soft-denying them and exiting 0 with no work.
- **SC-005**: A scout job does not take the edit-job auto-approve/write path (`--mode plan`, no skip-permissions).
- **SC-006**: Existing wrapper monitoring files (`status.json`, `report.json`, worker STATUS parse) remain present on every successful spawn layout. Stream-json runs still yield a parsed `workerStatus` without the parent reading `events.jsonl`.
- **SC-007**: A search of the in-scope docs/skills/rules for “there is no `agy -p`” and “SDK is the worker runtime” returns zero remaining claims.
- **SC-008**: Ready-check selftests for Antigravity worker-runtime pass under the new CLI check (and still fail when `agy` is isolated off PATH).
- **SC-009**: 100% of wrapper-spawned `agy` processes have stdin ignored and include print/headless flags; 0 spawn hangs waiting on a login TUI when credentials are missing (timeout or immediate fail instead).
- **SC-010**: An edit spawn whose CLI rejects skip-permissions with no official replacement ends as a failed run, never as a successful empty Ask-policy turn.

## Assumptions

- **Edit-job `--mode`**: Use `accept-edits`, not `auto`. Official `auto` is a preview, sandbox-gated, and not available on business/enterprise; unattended implement jobs need real writes, which `accept-edits` plus `--dangerously-skip-permissions` provides.
- **Scout permissions**: `--mode plan` is sufficient to keep scout non-writing; skip-permissions is edit-only so plan mode is not widened into an auto-approve shell agent.
- **Auth**: Cached `agy` credentials are the runtime auth. Ready treats successful `agy models` as the auth signal. `GEMINI_API_KEY` / Vertex env are no longer enough to pass Antigravity worker-runtime (they were SDK-era signals).
- **`agy` on PATH**: Ready uses `command -v agy` (operator PATH). A private path such as `~/.local/bin/agy` counts only if it is on PATH for the Ready process; Ready does not special-case a hardcoded home path once CLI is the runtime (today’s extra `~/.local/bin` probe was an SDK-era auth fallback).
- **No hybrid**: Missing CLI is a hard failure. The wrapper never imports `google.antigravity` on the worker path.
- **Python remains the wrapper language**: `agy-spawn.py` stays the launcher, so `python3` is still needed to *start the wrapper*, but it is not the worker-runtime identity check and the PyPI `google-antigravity` package is not required.
- **Timeout mapping**: Wrapper `--timeout` seconds become a CLI `--print-timeout` duration the installed `agy` accepts (seconds, or the CLI’s duration syntax if seconds-only is rejected). Millisecond wrapper values are converted up to the CLI’s unit. The wrapper also keeps its own SIGTERM/SIGKILL timer (Pi-matching dual enforcement). Unset wrapper timeout means no wrapper kill timer and the CLI default (documented 5 minutes) applies; this is a change from “SDK wrapper had no default timeout.”
- **Lifecycle vs STATUS**: Child process outcome sets `lifecycle`; assistant-text parse sets `workerStatus`. Non-zero `agy` exit is `failed` even if the text included `STATUS: ok`.
- **STATUS text source**: `--print` → CLI stdout. Long jobs → assistant text reconstructed from persisted stream-json lines in `events.jsonl` (raw CLI lines, same disk file the parent is told not to ingest).
- **Skip-permissions fail-closed**: Only `--dangerously-skip-permissions` or a flag the official headless docs name as its replacement. No degrade-to-Ask, no SDK.
- **No TTY at spawn**: stdin ignored; no extra `agy models` probe at spawn (Ready already gated auth).
- **`--vertex`**: Keep the flag for compatibility if already parsed, but do not start the SDK and do not invent a new CLI project flag. Vertex/Enterprise users must already be authenticated to the CLI (`agy models` succeeds).
- **`--conversation-id`**: If still parsed, map to `agy --conversation <id>` when set; default remains a fresh isolated run (no `--continue`).
- **Slash commands**: Always disable in print mode so host skills are not expanded inside the worker.
- **Docs scope**: Canonical AiNative copies listed in the request; in-repo speckit-ready duplicates of ready-check + selftest + SKILL.md. Host symlinks that point at AiNative are not separately rewritten.
- **Changelog**: Implement stage bumps `AiNative/CHANGELOG.md` (next SemVer under the existing scheme). Specify does not bump versions.
- **Out of scope stays out**: Pi harness, package installs, operator key changes, npm SDK, VS Code extensions, interactive TUI / `--prompt-interactive` / `ask_user`, mixing `--print` with `--input-format stream-json`.
- **Official CLI reference**: https://antigravity.google/docs/cli/headless/ (`-p` aliases `--print` / `--prompt`; `--disable-slash-commands`; `--print-timeout`; `--dangerously-skip-permissions`; `--mode accept-edits|auto|plan`; do not combine `-p` with `--input-format stream-json`).
