# Implementation Plan: Hermes Startup Context Files

**Branch**: `016-hermes-startup-context` | **Date**: 2026-09-14 |
**Spec**: [spec.md](./spec.md)

**Input**: Feature specification from
`/specs/016-hermes-startup-context/spec.md`

## Summary

Register Hermes `AGENTS.md`, persistent `SYSTEM.md`, and persistent `USER.md`
under one required `context` configuration with the exact container paths
`/opt/personal-agent/AGENTS.md`, `/opt/data/hermes-context/SYSTEM.md`, and
`/opt/data/hermes-context/USER.md`. A new stdlib-only startup-context seam
will validate and snapshot all three files before the live dispatcher accepts a
command, hash each source into revision-only metadata, enforce the documented
precedence order, and render a secret-safe `--doctor` diagnostic. Full text
stays in process memory for Hermes startup/planning/health use and is excluded
from coding-job payloads and operational records. The first delivery adds
short safe persistent-file templates while preserving the existing Hermes
`AGENTS.md` safety guidance.

## Technical Context

**Language/Version**: Python 3.12 (`>=3.12,<3.14`) through the existing `uv`
package in `personalAgent/`; Markdown and the existing subset YAML config.

**Primary Dependencies**: Existing stdlib-only Hermes package,
`pathlib`, `hashlib`, `os`, the existing `_parse_document` YAML subset, the
AiNative adapter, project registry, workspace manager, and current pytest 9.1.1
/ ruff 0.16.5 toolchain. No new dependency.

**Storage**: Three source Markdown files; actual `SYSTEM.md` and `USER.md`
remain in the existing `/opt/data` persistent mount. Revision/path metadata is
held in the process-local startup diagnostic and is not added to the native
Kanban board, workflow overlay, task records, worktrees, or a new database.

**Testing**: New focused `personalAgent/tests/test_startup_context.py`, live
dispatcher checks in `test_live_piv_bridge.py`, the existing harness and
orchestrator suites, `uv run pytest`, and `uv run ruff check src tests`.

**Target Platform**: Linux Hermes container for exact startup behavior, with
macOS/Linux temporary-path fixtures. Container-visible paths are used by
runtime code; host paths appear only in operator-facing Docker setup.

**Project Type**: In-process Python control plane and CLI health command with
filesystem configuration and a process-local context snapshot.

**Performance Goals**: Read and hash exactly three small files once per live
startup; do not add repeated discovery, polling, or a second persistence path.

**Constraints**: Fail closed on missing/unreadable/directory/empty/ambiguous
files; never auto-create persistent files; never translate host paths; do not
print contents or secrets; do not pass registered text into coding jobs; keep
runtime configuration above `SYSTEM.md`; leave project-bootstrapper wiring and
`ich-mag-dich` validation unchanged; no new dependency or database.

**Scale/Scope**: One live Hermes process, three fixed roles, one doctor
diagnostic, the existing single execution slot, and one focused fixture suite.

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

### Pre-research: PASS

| Principle / constraint | Verdict | Notes |
|---|---|---|
| I. Spec-first | PASS | The clarified feature spec, constitution, and current startup/persistence seams were read before design. |
| II. Least Code (Ponytail) | PASS | Reuses the existing parser, live dispatcher, adapter, registry, workspace manager, and overlay; adds one narrow context module. |
| III. Platform-native | PASS | Uses ordinary container files, existing `/opt/data` persistence, and the current CLI; adds no database, queue, or control plane. |
| IV. Trust-boundary tests | PASS | Path, file type, readability, UTF-8, duplicate registration, host-path, secret-safe output, precedence, and payload isolation receive focused checks. |
| V. Human authority | PASS | Missing persistent files remain an operator setup error; no deploy, push, merge, or protected-branch change is introduced. |
| Python 3.12 + uv | PASS | Existing package and lockfile remain authoritative. |
| No new dependencies | PASS | Python standard library and current pytest/ruff cover the feature. |
| Secrets and isolated Hermes home | PASS | Actual persistent files stay outside Git; diagnostics contain metadata only. |
| Surgical edits | PASS | Source changes are limited to startup loading/CLI integration, config, templates, tests, and guidance. |

## Project Structure

### Documentation (this feature)

```text
specs/016-hermes-startup-context/
├── spec.md
├── plan.md
├── research.md
├── data-model.md
├── quickstart.md
├── contracts/
│   └── startup-context.md
├── checklists/
│   └── requirements.md
└── tasks.md                 # Phase 2 (/speckit-tasks), not created here
```

### Source and tests

```text
personalAgent/
├── src/hermes_kanban/
│   ├── startup_context.py    # exact-path loading, revisions, precedence, diagnostic model
│   ├── runtime.py            # live startup validation and --doctor mode
│   └── orchestrator.py       # process-local snapshot attachment only
├── tests/
│   ├── test_startup_context.py
│   ├── test_live_piv_bridge.py
│   ├── test_harness_adapter.py
│   └── test_piv_orchestrator.py
├── config/default.yaml       # exact container registrations
├── docs/context/
│   ├── SYSTEM.example.md
│   └── USER.example.md
├── AGENTS.md                 # existing versioned guidance plus short completion note
└── README.md                 # operator copy/doctor instructions
```

`docker-compose.yml` already mounts the host Hermes home at `/opt/data` and
the repository at `/opt/personal-agent`; no new mount or persistent store is
needed. `executor.py`, `persist.py`, and the provider-neutral harness records
remain unchanged except for tests proving the registered text never enters
those seams.

**Structure Decision**: Keep the flat `hermes_kanban` package and existing
fixture style. Put the fixed-role filesystem contract in one new module,
invoke it at the current live dispatcher boundary, and keep metadata separate
from the in-memory text snapshot. Use the existing operator data mount for
persistent files and the existing repository mount for `AGENTS.md`.

## Implementation Design

### 1. Add the exact-path startup context seam

- Create `personalAgent/src/hermes_kanban/startup_context.py`.
- Define typed records for the three roles, loaded text, metadata-only
  registrations, precedence layers, and safe startup diagnostics.
- Parse the `context` mapping with `projects._parse_document`; require exactly
  `hermes_instructions`, `system`, and `user`.
- Validate absolute container paths, reject host-only `/Users/...` paths,
  require one readable non-empty regular UTF-8 file per role, and reject
  duplicate resolved files.
- Hash source bytes with SHA-256 and retain the text only in the current
  process. Never write a source file or search another location.
- Keep the precedence resolver pure and ordered as
  platform/safety → Hermes → live runtime → SYSTEM → project → USER → task.

### 2. Gate live startup and expose the safe doctor report

- In `runtime.build_live_orchestrator()`, load the startup snapshot before
  board selection or command handling, then continue through the existing
  native board/harness setup.
- Add an optional process-local snapshot/diagnostic reference to
  `PivOrchestrator`; do not add it to `WorkflowRecord` or any persistence
  serializer. Existing fixture construction remains valid when the optional
  value is absent.
- Build the diagnostic from existing `AiNativeAdapter`, `ProjectRegistry`,
  `WorkspaceManager`, harness configuration, and overlay directory objects.
  Include only the required paths, identities, agent names, and revisions.
- Add `--doctor` to the existing parser. It performs the same startup
  validation, prints the safe diagnostic, and exits without selecting a task.
  Normal live startup uses the same validation/reporting path before dispatch.
- Ensure errors include role, exact configured path, and safe reason, never
  file text or secret values.

### 3. Preserve coding-job and operational-record boundaries

- Do not add the snapshot to `ExecutePayload`, `AssembledContext`,
  `HarnessStartRequest`, `HarnessResult`, `WorkflowRecord`, Kanban records,
  worktrees, project repositories, or overlay JSON.
- Keep `_read_workspace_files()` as the only coding-job file projection; it
  continues to read project-local files in the prepared worktree.
- Record/report only role/path/SHA-256 revision metadata. Add tests that place
  unique sentinel text in all three registered files and assert the sentinels
  are absent from job requests, model contexts, and persisted records.

### 4. Add safe first-delivery files and configuration

- Add the `context` block with the three exact container paths to
  `personalAgent/config/default.yaml`.
- Add short, non-secret placeholders at
  `personalAgent/docs/context/SYSTEM.example.md` and
  `personalAgent/docs/context/USER.example.md`; both explicitly tell the
  operator to complete them later.
- Add a concise startup-context/operator-completion note to the existing
  `personalAgent/AGENTS.md` without deleting its current safety instructions.
- Update `personalAgent/README.md` with manual template-copy instructions,
  persistent-file boundaries, exact container paths, and the `--doctor`
  example. Do not change project-bootstrapper wiring or `ich-mag-dich`
  validation.

### 5. Verify and record delivery

- Add focused fixtures for success, load order, exact-path/no-fallback,
  missing, unreadable, directory, empty, invalid UTF-8, duplicate,
  host-only, revision-change, precedence, no-auto-create, secret-safe
  diagnostics, and coding-job isolation.
- Update the live-entry check for startup validation and `--doctor` without
  requiring real persistent files in ordinary offline tests.
- Run focused tests, the complete pytest suite, and Ruff. Run the documented
  container doctor check when the local Hermes image/home are available.
- Update the root `CHANGELOG.md` with the delivered plan/design artifacts and,
  during implementation, update `personalAgent/CHANGELOG.md` for the actual
  source/templates/tests delivery. Do not commit persistent `SYSTEM.md` or
  `USER.md`.

## Dependency and Execution Order

| ID | Atomic work package | Depends on | Safe parallelism | Executor / model / effort |
|---|---|---|---|---|
| A | Implement startup-context models, exact-path loader, hashing, and precedence resolver | None | Foundation; blocks B/C | `implementation-worker` / `po-normal-grok46` (Grok 4.6, Medium) |
| B | Integrate live startup gating, diagnostic construction, and `--doctor` | A | Serial with runtime/orchestrator changes | `implementation-worker` / `po-normal-grok46` (Grok 4.6, Medium) |
| C | Add config, templates, AGENTS/README guidance | A's contract only | Parallel with B | `documentation-worker` / `po-normal-grok46` (Grok 4.6, Medium) |
| D | Add focused isolation, failure, precedence, revision, and CLI tests | A and B | Parallel by test file after interfaces settle | `test-worker` / `po-normal-grok46` (Grok 4.6, Medium) |
| E | Run full validation, container doctor proof, and changelog delivery | B, C, D | Final serialized gate | `validation-worker` / `po-normal-grok46` (Grok 4.6, Medium) |

The independent work is limited to documentation/templates and test
preparation after the loader contract is fixed. Runtime integration and
orchestrator lifecycle changes remain serialized because they share the live
startup boundary. The container proof is last because it depends on the
checked-in config, templates, source mount, and all focused checks.

## Phase 1 Acceptance and Verification

- The default config registers exactly the three specified container paths.
- A valid fixture loads all three files in order before a live command can run.
- Missing, unreadable, directory, empty, invalid-UTF-8, duplicate, and
  host-only cases fail with role/path/reason diagnostics and create nothing.
- A changed source file produces a new revision for the same configured path.
- `--doctor` reports AiNative root, available agents, configured projects,
  workspace root, active harness, persistent state path, and three
  role/path/revision records without any file body or secret.
- Precedence fixtures resolve platform/safety, Hermes, runtime, SYSTEM,
  project, USER, and task conflicts in the documented order.
- Unique registered-file sentinel text is absent from coding-job payloads,
  model contexts, harness requests, Kanban/task records, worktrees, projects,
  and overlay JSON.
- Actual persistent `SYSTEM.md` and `USER.md` remain outside Git and are
  never auto-created; repository templates are safe and operator-completable.
- Existing harness, orchestrator, project-bootstrapper boundary, and
  `ich-mag-dich` validation behavior remain unchanged.
- Focused tests, full pytest, Ruff, and the available Docker doctor proof pass.

## Post-design Constitution Check: PASS

The design reuses the existing parser and live dispatcher, adds no dependency
or state store, and keeps source files canonical. Validation occurs before
command handling at the trust boundary, all failure modes are explicit, and
the only persisted/reportable context is role/path/revision metadata. Hermes
retains safety and human authority, while coding jobs continue to receive only
project-local context. No unresolved clarification or constitution violation
remains.

## Complexity Tracking

No constitution violations require justification.
