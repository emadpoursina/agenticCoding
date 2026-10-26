# Tasks: Antigravity CLI worker backend

**Input**: Design documents from `specs/002-agy-cli-backend/`

**Prerequisites**: plan.md (required), spec.md (required for user stories), research.md, data-model.md, contracts/, quickstart.md — all present from plan stage.

**Tests**: Spec Independent Tests, FR-015, plan W4 / TF-1–TF-6, and `quickstart.md` explicitly require `agy-spawn.py --self-test` and both `ready-check.selftest.sh` copies. Include those test tasks (write assertions first, confirm they fail, then implement). Do **not** add extra test frameworks, fixtures, or live `agy` job tasks. Optional live smoke in `quickstart.md` is not a gate.

**Organization**: Tasks grouped by user story (US1–US5). Single AiNative tree. Python stdlib only. Do not edit `AiNative/docs/agents/pi-harness/pi-spawn.mjs`. Do not install packages or change operator auth. Do not rewrite host skill symlinks. Changelog only `AiNative/CHANGELOG.md`.

**Constitution**: `.specify/memory/constitution.md` is an unfilled template — spec FRs are binding.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies on incomplete tasks)
- **[Story]**: User story label (US1–US5) on story-phase tasks only
- Every task includes exact file path(s)

## Path conventions

- Wrapper: `AiNative/docs/agents/antigravity-harness/agy-spawn.py`
- Contract text (contents unchanged): `AiNative/docs/agents/antigravity-harness/worker-contract.md`
- Ready copies (keep in lockstep): `AiNative/docs/agents/ready/` and `AiNative/docs/agents/speckit-ready/`
- Feature contracts: `specs/002-agy-cli-backend/contracts/`

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Lock scope and contracts before rewriting the wrapper or Ready gate.

- [x] T001 Confirm implementation stays on plan source list (`AiNative/docs/agents/antigravity-harness/agy-spawn.py`, harness `SKILL.md`/`rule.md`/`AGENTS.md`, wrapper comments, `AiNative/docs/agents/speckit-orchestrate/SKILL.md` plus `AGENTS.md`/`rule.md`, both ready `SKILL.md` + `scripts/ready-check.sh` + `ready-check.selftest.sh`, `AiNative/docs/agents/README.md`, `AiNative/docs/systems/feature-loop.md`, `AiNative/.cursor/commands/antigravity-harness.md`, `AiNative/CHANGELOG.md`); leave `AiNative/docs/agents/antigravity-harness/worker-contract.md` contents unchanged; never edit `AiNative/docs/agents/pi-harness/pi-spawn.mjs` (FR-018); no package installs, npm SDK, or auth/key changes (FR-019)
- [x] T002 [P] Desk-check `specs/002-agy-cli-backend/contracts/agy-cli-argv.md`, `specs/002-agy-cli-backend/contracts/run-dir.md`, and `specs/002-agy-cli-backend/contracts/ready-worker-runtime.md` against spec clarifications: always `-p`; text vs stream-json; skip-permissions fail-closed; dual timeout; lifecycle vs worker STATUS; Ready PATH + `agy models` only

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Replace the SDK Agent runtime with a Python launcher that execs `agy`, keeps the parent argv/run-dir surface, and never falls back to `google.antigravity`.

**⚠️ CRITICAL**: No user story work until T003–T005 are done. Later stories add flags, STATUS parse, Ready, and docs on this skeleton.

- [x] T003 In `AiNative/docs/agents/antigravity-harness/agy-spawn.py`, delete `google.antigravity` imports and the SDK `Agent` / `LocalAgentConfig` / policy path (`run_agent`); keep `python3` as launcher language and existing parent flags (`--name`, `--cwd`, `--model` required, `--effort`, `--timeout`, `--print`/`-p`, `--scout`, `--conversation-id`, `--vertex`, `--run-id`, prompt after `--`, `--self-test`); `--name` still sanitizer `[\w.-]+` with no path seps (data-model.md)
- [x] T004 In `AiNative/docs/agents/antigravity-harness/agy-spawn.py`, spawn `agy` via stdlib `subprocess` with child stdin ignored (`DEVNULL` / not a TTY), `cwd` = wrapper `--cwd`, argv[0] PATH lookup `agy`; if `agy` cannot be started, fail loudly with `lifecycle=failed` and **no** Python SDK fallback (FR-001, FR-017, FR-023); do not run `agy models` on spawn
- [x] T005 In `AiNative/docs/agents/antigravity-harness/agy-spawn.py`, keep run dir `.agent/antigravity/<job-name>/<run-id>/{status.json,report.json,events.jsonl,stderr.log}` plus `latest.json`; public JSON keys stay as today except `"backend": "agy-cli"` (not `antigravity-sdk`); `schemaVersion` remains `1`; compact wrapper stdout still `RUN_DIR=` / `STATUS_FILE=` / `LIFECYCLE=` / `REPORT_FILE=`; lifecycle follows child process (`starting` → `running` → `completed` exit 0 | `failed` non-zero | `terminated` signal not timeout | `timed_out` wrapper kill timer) per `specs/002-agy-cli-backend/contracts/run-dir.md` and data-model.md

**Checkpoint**: Wrapper can start `agy` without the SDK; parent still only calls `agy-spawn.py`; run-dir contract exists.

---

## Phase 3: User Story 1 — Operator gets a real unattended Antigravity worker (Priority: P1) 🎯 MVP

**Goal**: Every wrapper spawn execs official CLI print/headless `agy -p` (never a bare TUI). Short jobs use text stdout; long jobs use `--output-format stream-json` and persist events under the run dir. Parent never execs `agy` itself. Child stdin is not a TTY.

**Independent Test**: Spawn via wrapper with `--print` and without it. Child argv always includes `-p`/`--print`; never a bare `agy`; never `--prompt-interactive`; never `--input-format stream-json`. Short jobs omit `--output-format`. Long jobs include `--output-format stream-json` and write `events.jsonl`. `python3 AiNative/docs/agents/antigravity-harness/agy-spawn.py --self-test` covers TF-1/TF-2 argv (plan AC-1, AC-9; SC-001, SC-002, SC-009).

### Tests for User Story 1

> Write these assertions first; they MUST fail on the SDK-era `--print` chatter flag before T007–T008.

- [x] T006 [US1] Extend `self_test()` in `AiNative/docs/agents/antigravity-harness/agy-spawn.py` so TF-1/TF-2 fail until implemented: wrapper `--print` argv contains `-p` (or `--print`), `--disable-slash-commands` may wait for US4 but **must** assert no `--output-format` and no `--input-format`; long-job argv (no wrapper `--print`) contains `-p` **and** `--output-format stream-json`; neither path includes `--prompt-interactive` or `-i`; `--self-test` still does not start `agy`

### Implementation for User Story 1

- [x] T007 [US1] In `AiNative/docs/agents/antigravity-harness/agy-spawn.py`, always pass CLI `-p`/`--print`; wrapper `--print` → default text stdout (no `--output-format`); wrapper without `--print` → add `--output-format stream-json` and persist every raw CLI stdout line to `events.jsonl` (truncate/create at start); never combine `-p` with `--input-format stream-json` (FR-003–FR-006; contracts/agy-cli-argv.md)
- [x] T008 [US1] In `AiNative/docs/agents/antigravity-harness/agy-spawn.py`, keep stdin ignored; omit `--prompt-interactive`, `-i`, and `ask_user` from argv; do not probe `agy models` on spawn (FR-003, FR-023). Parent spawn instructions stay wrapper-only (code already; docs in US5)

**Checkpoint**: Unattended headless argv is real CLI print mode; TUI cannot attach via stdin.

---

## Phase 4: User Story 2 — Edit jobs write; scout jobs stay non-writing (Priority: P1)

**Goal**: Default (edit) jobs auto-approve shell and workspace writes. Scout stays plan-only. Rejected skip-permissions with no official replacement fails closed (no Ask retry, no SDK).

**Independent Test**: Edit argv includes `--dangerously-skip-permissions` and `--mode accept-edits`. Scout argv includes `--mode plan` and omits skip-permissions. Fail-closed helper: unknown skip-permissions → `lifecycle=failed`, no retry without the flag, no `google.antigravity` import (spec US2; plan TF-3, TF-5.6; AC-4, AC-5, AC-10).

### Tests for User Story 2

- [x] T009 [US2] Extend `self_test()` in `AiNative/docs/agents/antigravity-harness/agy-spawn.py` for TF-3: default argv has `--mode accept-edits` and `--dangerously-skip-permissions`; `--scout` argv has `--mode plan` and does **not** include skip-permissions; assert a fail-closed helper that finalizes `failed` without stripping the flag or importing the SDK (do not use `--mode auto`)

### Implementation for User Story 2

- [x] T010 [US2] In `AiNative/docs/agents/antigravity-harness/agy-spawn.py`, default (not `--scout`) child argv includes `--mode accept-edits` and `--dangerously-skip-permissions` (FR-007; research: not `--mode auto`)
- [x] T011 [US2] In `AiNative/docs/agents/antigravity-harness/agy-spawn.py`, `--scout` passes `--mode plan` and MUST NOT pass `--dangerously-skip-permissions`; if installed `agy` rejects skip-permissions (unknown flag / non-zero start) on an edit job, finalize `lifecycle=failed` with no Ask-policy retry and no SDK fallback; official docs name no replacement flag as of 2026-10-26 (FR-007, FR-008)

**Checkpoint**: Edit jobs cannot soft-deny tools and look successful; scout is not an auto-approve shell agent.

---

## Phase 5: User Story 3 — Ready fails closed on missing CLI, not missing Python SDK (Priority: P1)

**Goal**: Antigravity `worker-runtime` is `command -v agy` then `agy models`. SDK import is neither required nor sufficient. Both ready copies stay in lockstep.

**Independent Test**: Both `ready-check.selftest.sh` exit 0. Case 16 still missing-pi fail; case 17 fails on missing `agy` (isolated PATH + fake HOME, unset API/Vertex env) with a PATH install fix — **not** `pip install google-antigravity` and not an SDK-import message; case 18 unknown worker; case 19 `WORKER: antigravity` plus a `worker-runtime:` line. Suite default stays `SPECKIT_WORKER=pi` (FR-014, FR-015; plan TF-4; AC-3, AC-8).

### Tests for User Story 3

> Rewrite selftests first so case 17 fails for the right reason after T014–T015.

- [x] T012 [P] [US3] Rewrite Antigravity cases in `AiNative/docs/agents/ready/scripts/ready-check.selftest.sh` per `specs/002-agy-cli-backend/contracts/ready-worker-runtime.md`: keep cases 16/18/19; case 17 isolates `agy` off PATH (stub PATH + fake HOME, no `agy` binary) and expects `worker-runtime: fail` plus CLI PATH fix text, not `pip install google-antigravity`; keep suite default `SPECKIT_WORKER=pi`
- [x] T013 [P] [US3] Apply the identical case 16–19 rewrite to `AiNative/docs/agents/speckit-ready/scripts/ready-check.selftest.sh` (FR-015 lockstep)

### Implementation for User Story 3

- [x] T014 [US3] In `AiNative/docs/agents/ready/scripts/ready-check.sh`, for `antigravity|agy|google-antigravity` (and default): pass only if `command -v agy` succeeds **and** `agy models` exits 0 (stdout discarded; do not paste model lists into FIXES); do not require `python3` or `from google.antigravity import Agent`; `GEMINI_API_KEY` / `GOOGLE_API_KEY` / Vertex env MUST NOT pass the check; do not special-case `~/.local/bin/agy` unless already on PATH; missing `agy` FIXES tell operator to install/put `agy` on PATH — never `pip install google-antigravity`; failed `agy models` FIXES say authenticate the CLI, API key env is not enough (FR-014)
- [x] T015 [US3] Copy the same `worker-runtime` logic into `AiNative/docs/agents/speckit-ready/scripts/ready-check.sh` so both copies stay in lockstep (FR-014, FR-015)

**Checkpoint**: Ready on a CLI-only machine can pass; SDK-only / missing CLI cannot.

---

## Phase 6: User Story 4 — Wrapper contract stays the parent’s monitoring surface (Priority: P1)

**Goal**: Parent flags, contract prepend, `--disable-slash-commands`, timeout dual enforcement, STATUS parse, and `status.json`/`report.json` semantics stay. Stream-json `workerStatus` comes from reconstructed assistant text; parent still does not ingest `events.jsonl`. Non-zero `agy` exit is `lifecycle=failed` even if text had `STATUS: ok`.

**Independent Test**: Missing `--model` exits 2 without starting `agy`. `--effort` forwarded when set. `--timeout 2` → `--print-timeout 2s` plus wrapper SIGTERM then SIGKILL fields; omitted timeout → no `--print-timeout` and no wrapper kill timer. `--conversation-id` → `--conversation`; `--vertex` not forwarded. Prompt starts with `worker-contract.md` + blank line + job prompt. Stream-json reconstruct prefers last `result.response`, else `agent_response` `text_delta`. `python3 …/agy-spawn.py --self-test` prints `SELFTEST: ok` (FR-009–FR-013, FR-021–FR-022; plan TF-5; AC-6).

### Tests for User Story 4

- [x] T016 [US4] Extend `self_test()` in `AiNative/docs/agents/antigravity-harness/agy-spawn.py` for TF-1 remainder and TF-5: missing `--model` → exit 2, no spawn; `--timeout 2` maps to `--print-timeout 2s` and wrapper timer fields set; omitted timeout → no `--print-timeout`; millisecond timeout ceiled to whole seconds, minimum 1s when a timeout was requested; `--conversation-id` maps to `--conversation`; `--vertex` absent from child argv; prompt value is contract text, blank line, job prompt; `--disable-slash-commands` always present; non-zero child exit → `lifecycle=failed` even if stdout has `STATUS: ok`; stream-json fixture with `result.response` wins; fixture with only `text_delta` still parses `STATUS: ok`; malformed JSONL lines ignored (count/log, no crash)

### Implementation for User Story 4

- [x] T017 [US4] In `AiNative/docs/agents/antigravity-harness/agy-spawn.py`, require `--model` (exit 2, do not start `agy`); pass `--model <id>` through; always pass `--disable-slash-commands`; prepend `worker-contract.md` contents plus a blank line to the job prompt as the single `-p` argument (CLI has no `--append-system-prompt`) (FR-009–FR-011)
- [x] T018 [US4] In `AiNative/docs/agents/antigravity-harness/agy-spawn.py`, map wrapper `--timeout` seconds to `agy --print-timeout {n}s` (ms ceiled to seconds, min 1s when requested) **and** start wrapper SIGTERM then SIGKILL (~2s grace, Pi-matching); omit both `--print-timeout` and the wrapper kill timer when `--timeout` is omitted (do not invent 5m); forward `--effort` as `agy --effort` only when set; map `--conversation-id` to `agy --conversation <id>` when set (no `--continue` by default); parse `--vertex` but do not forward `--project` or any Vertex CLI flag (FR-011, FR-012; contracts/agy-cli-argv.md)
- [x] T019 [US4] In `AiNative/docs/agents/antigravity-harness/agy-spawn.py`, parse worker STATUS with existing regex `\bSTATUS\s*[:=]?\s*(ok|stuck|blocked)\b`: text mode from captured CLI stdout; stream-json from `events.jsonl` — last `event=="result"` `result.response` (trimmed), else concatenated `step_update.text_delta` where `step_type=="agent_response"`; put that text in `report.json` `summary`/`summaryExtracted`; `reportValid` true iff STATUS token found; heartbeat `status.json` `current`/`lastEventType` from stream events (`init`/`step_update`/`result`) without putting assistant body in `status.json`; wrapper process exit 0 only when `lifecycle=completed`; parent job success remains `reportValid`/`workerStatus` (FR-013, FR-021, FR-022; contracts/run-dir.md)

**Checkpoint**: Parent can keep polling `status.json`/`report.json` unchanged; stream-json STATUS works without parent reading events.

---

## Phase 7: User Story 5 — Docs stop saying the SDK is the worker runtime (Priority: P2)

**Goal**: Canonical harness, orchestrate, ready, and sibling operator docs describe CLI headless via the wrapper (Pi shape). Zero remaining “there is no `agy -p`” or “SDK is the worker runtime” claims. Changelog records the switch.

**Independent Test**: `rg` in `quickstart.md` §4 returns zero matches for those phrases; positive search still finds `agy-spawn.py`, `agy -p`, and Ready `agy models`. Spawn docs: never launch bare `agy`, never mix wrapper `--print` with `--input-format stream-json`, parent never calls `agy -p` itself (spec US5; AC-7, AC-2, AC-11).

### Implementation for User Story 5

- [x] T020 [P] [US5] Rewrite `AiNative/docs/agents/antigravity-harness/SKILL.md`, `AiNative/docs/agents/antigravity-harness/rule.md`, `AiNative/docs/agents/antigravity-harness/AGENTS.md`, and module/doc comments in `AiNative/docs/agents/antigravity-harness/agy-spawn.py`: worker runtime is `agy -p` via the wrapper; Ready checks `agy` + `agy models`; parent only calls `agy-spawn.py`; wrapper `--print` means CLI text mode; never bare `agy`; never mix `-p` with `--input-format stream-json`; never `pip install google-antigravity` as the worker runtime (FR-016)
- [x] T021 [P] [US5] Update `AiNative/docs/agents/speckit-orchestrate/SKILL.md`, `AiNative/docs/agents/speckit-orchestrate/AGENTS.md`, and `AiNative/docs/agents/speckit-orchestrate/rule.md` so Worker stages still spawn only `agy-spawn.py` and do not exec `agy -p` themselves; delete SDK-as-runtime claims (FR-002, FR-016; research docs blast radius)
- [x] T022 [P] [US5] Update `AiNative/docs/agents/ready/SKILL.md` and `AiNative/docs/agents/speckit-ready/SKILL.md`: Antigravity worker-runtime is PATH `agy` + successful `agy models`; SDK import neither required nor sufficient; FIXES never `pip install google-antigravity` (FR-014, FR-016)
- [x] T023 [P] [US5] Update sibling operator docs that still teach SDK runtime so SC-007 cannot fail: `AiNative/docs/agents/README.md`, `AiNative/docs/systems/feature-loop.md`, `AiNative/.cursor/commands/antigravity-harness.md` (research.md Docs blast radius; do not rewrite host symlinks)
- [x] T024 [US5] Add a Keep a Changelog / SemVer entry to `AiNative/CHANGELOG.md` for the CLI switch (recommend `0.4.0` — worker-runtime identity change); do not bump Specify/spec artifacts (FR-020)

**Checkpoint**: Operator-facing docs match the CLI wrapper; changelog records the behavior change.

---

## Phase 8: Polish & Cross-Cutting Concerns

**Purpose**: Prove the gate from `quickstart.md` and freeze Pi.

- [x] T025 Run `python3 AiNative/docs/agents/antigravity-harness/agy-spawn.py --self-test` and expect `SELFTEST: ok`; `rg -n "from google.antigravity|google.antigravity.Agent"` on that wrapper must have no matches (quickstart §§1–2)
- [x] T026 [P] Run `bash AiNative/docs/agents/ready/scripts/ready-check.selftest.sh` and `bash AiNative/docs/agents/speckit-ready/scripts/ready-check.selftest.sh`; both exit 0 (quickstart §3)
- [x] T027 [P] Run the forbidden-phrase and wrapper-only `rg` commands from `specs/002-agy-cli-backend/quickstart.md` §§4–5; zero leftover “there is no \`agy -p\`” / “SDK is the worker runtime”; spawn docs still name `agy-spawn.py`
- [x] T028 Confirm `git diff --name-only -- AiNative/docs/agents/pi-harness/pi-spawn.mjs` is empty (or no behavior hunks) and `AiNative/CHANGELOG.md` newest version mentions `agy -p` / CLI headless / `agy models` (quickstart §§6–7; FR-018, FR-020)

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies
- **Foundational (Phase 2)**: Depends on Setup — BLOCKS all user stories
- **US1 (Phase 3)**: Depends on Foundational — MVP CLI print spawn
- **US2 (Phase 4)**: Depends on US1 argv builder in the same wrapper file (sequential, not parallel with US1)
- **US3 (Phase 5)**: Depends on Foundational only (Ready scripts; can run in parallel with remaining wrapper work once US1/US2 started by another implementer)
- **US4 (Phase 6)**: Depends on US1–US2 (same `agy-spawn.py`; STATUS/timeout/contract on the CLI argv)
- **US5 (Phase 7)**: Can start after Foundational for wording, but should land after US3–US4 so docs match shipped flags
- **Polish (Phase 8)**: After desired stories

### User Story Dependencies

- **User Story 1 (P1)**: After Phase 2 — MVP
- **User Story 2 (P1)**: After US1 (same file: `agy-spawn.py`)
- **User Story 3 (P1)**: After Phase 2 — independent files (ready copies)
- **User Story 4 (P1)**: After US2 (same wrapper)
- **User Story 5 (P2)**: After behavior exists; docs files are parallel among themselves except changelog last

### Within Each User Story

- Self-test / ready-selftest assertions first where listed; confirm fail; then implementation
- Argv builder before STATUS reconstruct
- Ready-check.sh after selftest rewrite
- Docs after (or in lockstep with) behavior
- Story complete before next wrapper story

### Parallel Opportunities

- T002 with T001
- T012 and T013 (two selftest files)
- US3 (ready) vs US1/US2/US4 (wrapper) after Phase 2 if two implementers
- T020–T023 different doc files
- T026 and T027 in Polish

Do **not** mark sequential `agy-spawn.py` tasks `[P]`.

---

## Parallel Example: User Story 3

```bash
# After Phase 2, two ready selftest files together:
Task: "Rewrite case 17 in AiNative/docs/agents/ready/scripts/ready-check.selftest.sh"
Task: "Rewrite case 17 in AiNative/docs/agents/speckit-ready/scripts/ready-check.selftest.sh"
```

## Parallel Example: User Story 5

```bash
Task: "Rewrite antigravity-harness SKILL.md / rule.md / AGENTS.md"
Task: "Update speckit-orchestrate SKILL.md / AGENTS.md / rule.md"
Task: "Update both ready SKILL.md files"
Task: "Update README.md, feature-loop.md, Cursor command"
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Phase 1 Setup
2. Phase 2 Foundational (CRITICAL)
3. Phase 3 US1 (`agy -p` always; text vs stream-json)
4. **STOP and VALIDATE**: `agy-spawn.py --self-test` TF-1/TF-2 assertions
5. Then US2 (edit/scout) before treating implement jobs as unattended-complete

### Incremental Delivery

1. Setup + Foundational → launcher execs CLI, no SDK
2. US1 → unattended print/headless (MVP)
3. US2 → tools actually run on edit jobs
4. US3 → Ready identity is the CLI
5. US4 → parent monitoring/STATUS/timeout parity with Pi
6. US5 → docs + changelog
7. Polish → `quickstart.md`

### Parallel Team Strategy

1. Together: Setup + Foundational
2. Then: Developer A continues `agy-spawn.py` (US1 → US2 → US4); Developer B Ready copies (US3); Developer C docs (US5) after flags stabilize
3. Polish is sequential on the combined tree

---

## Notes

- [P] tasks = different files, no incomplete-task dependencies
- Do not keep sample template tasks
- `worker-contract.md` is prepended, not edited
- Official CLI: https://antigravity.google/docs/cli/headless/
- Commit plan (if parent Ship commits): wrapper → ready → docs/changelog; never commit `.agent/` run dirs
- Avoid: hybrid SDK fallback, `--mode auto`, inventing `--print-timeout` when operator omitted `--timeout`, parent exec of `agy -p`
