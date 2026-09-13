# Implementation Plan: AiNative Structure Alignment

**Branch**: `015-align-ainative-structure` | **Date**: 2026-09-13 |
**Spec**: [spec.md](./spec.md)

**Input**: Feature specification from
`/specs/015-align-ainative-structure/spec.md`

**Reference**: The nested `AiNative/` checkout is the read-only source of
truth. It is already on the four-layer tree and is not an implementation
target.

## Summary

Align the Hermes consumer and its disposable methodology fixtures with
AiNative's current `docs/agents/` contract, while keeping the complete
written vocabulary of `systems`, `agents`, `knowledge`, and `records`.
The adapter will have one strict agent root and will remove its existing
simple-roster/manifest fallback branches; setup will be rerun against the
live `personalAgent/` app so its agent and systems links and ignore block are
migrated in place. Existing AiNative setup and verification scripts are the
canonical migration tooling; this feature consumes and exercises them rather
than adding a second implementation.

No runtime reader will be added for `knowledge` or `records`, no compatibility
aliases will remain, and no files in the nested AiNative checkout will be
modified or copied.

## Technical Context

**Language/Version**: Python 3.12 (`>=3.12,<3.14`) through the existing `uv`
package in `personalAgent/`; POSIX shell and Node.js built-ins for the existing
AiNative checks

**Primary Dependencies**: Existing stdlib-only Hermes package, `pathlib`,
`subprocess`, `git`, Node.js `fs`/`path`, and the current `pytest` 9.1.1 /
`ruff` 0.16.5 toolchain. No new dependency.

**Storage**: Files, read-only symlinks, fixture trees, and `.gitignore`
entries only. Existing Hermes SQLite databases, overlays, and task state are
untouched.

**Testing**: Focused `personalAgent/tests/test_ainative_adapter.py` and the
existing executor/integration checks, `uv run pytest`, `uv run ruff check`,
AiNative `check-ainative-link.sh`, `check-agent-commands.sh`, and
`check-doc-links.mjs`.

**Target Platform**: macOS/Linux development and the existing Linux Hermes
container. The `/ainative` Docker bind remains read-only.

**Project Type**: Cross-repository contract alignment: one in-process Python
adapter, shell/Node setup verification, fixture-based tests, live Hermes
guidance, and tracked Spec Kit design artifacts.

**Performance Goals**: Preserve current small-roster behavior. Agent discovery
remains a deterministic immediate-directory scan; link validation remains a
single local walk of Markdown and rule files. No throughput target is needed.

**Constraints**: No new dependencies, no hardcoded host paths, no AiNative
write or duplicate, no fallback to `docs/8-agents` or a simple `agents/` tree,
no compatibility symlinks, no second runtime reader, and surgical edits only.
The setup script must preserve a real local `docs/systems/` directory unless
its documented force option is used.

**Scale/Scope**: One adapter and its contract test, one committed fixture
tree, the live `personalAgent/` consumer, the current setup/check scripts,
and stale references in the active adapter-related specifications.

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

### Pre-research: PASS

| Principle / constraint | Verdict | Notes |
|---|---|---|
| I. Spec-first | PASS | Clarified feature spec, constitution, and current source trees were read before design. |
| II. Least Code (Ponytail) | PASS | Remove obsolete fallback branches and reuse existing setup/check scripts; add no new abstraction. |
| III. Platform-native | PASS | Reuse the existing filesystem, symlink, Git, Docker read-only mount, and script capabilities. AiNative remains read-only. |
| IV. Trust-boundary tests | PASS | Adapter root validation, old-path rejection, read-only refusal, setup migration, parity, and link checks are explicit. |
| V. Human authority | PASS | No push, merge, deploy, production repository, or autonomous methodology change is introduced. |
| Python 3.12 + uv | PASS | Existing Hermes package and lockfile remain authoritative. |
| No new dependencies | PASS | Python stdlib, Git, Bash, and Node.js already cover the work. |
| Surgical edits | PASS | Changes are limited to the adapter, fixtures/tests, live guidance, setup projection, and stale contract references. |

## Project Structure

### Documentation (this feature)

```text
specs/015-align-ainative-structure/
├── spec.md
├── plan.md
├── research.md
├── data-model.md
├── quickstart.md
├── contracts/
│   └── structure-alignment.md
├── checklists/
│   └── requirements.md
└── tasks.md             # Phase 2 (/speckit-tasks), not created here
```

### Source and reference repositories

```text
AiNative/                                  # read-only reference; no edits
├── docs/{systems,agents,knowledge,records}/
├── scripts/ainative-link.mjs              # setup-project implementation
├── scripts/check-ainative-link.sh
├── scripts/check-agent-commands.sh
└── scripts/check-doc-links.mjs

personalAgent/                             # live Hermes consumer
├── src/hermes_kanban/ainative.py
├── tests/test_ainative_adapter.py
├── tests/fixtures/ainative-full/docs/agents/
├── AGENTS.md
├── docs/v0-implementation-plan.md
├── .gitignore                              # managed setup block
└── generated docs/agents + docs/systems links

specs/
├── 001-ainative-adapter/                   # active adapter contract docs
├── 004-agent-execution/
├── 005-piv-orchestrator/
├── 006-piv-recovery/
└── 015-align-ainative-structure/
```

**Structure Decision**: Keep the existing flat `hermes_kanban` package and
the current fixture strategy. Change only the adapter's accepted root and
fixture paths. The four AiNative layers stay a documentation vocabulary;
only `docs/agents/` is read by Hermes, while setup also exposes
`docs/systems/` to the app. `knowledge/` and `records/` remain reference
material and are validated through links, not loaded by a new runtime API.

## Complexity Tracking

No constitution violations require justification.

## Implementation Design

### 1. Make the adapter strict at the trust boundary

- Change `AiNativeAdapter.__init__` to require
  `{settings.path}/docs/agents/` as a directory.
- Remove `_simple_roster`, `manifest.yaml` acceptance, and the fallback to
  `{settings.path}/agents`; these branches are incompatible with the clean
  break.
- Keep sorted immediate-directory discovery and the existing reserved
  `template` / `_skills` exclusions.
- Keep agent loading, shared-skill resolution, revision capture, and refused
  writes unchanged except for paths rooted under `docs/agents/`.
- Add a focused regression proving a checkout with only the retired
  `docs/8-agents/` root is rejected and never scanned.

### 2. Move fixtures and preserve adapter coverage

- Use `git mv` inside `personalAgent/` to move
  `tests/fixtures/ainative-full/docs/8-agents/` to `docs/agents/`.
- Remove obsolete simple-roster fixture files (`agents/scout.md` and the
  unused `manifest.yaml`) so tests cannot accidentally validate a fallback.
- Update every adapter assertion and live-mount guard to use `docs/agents/`.
- Retain coverage for complete/partial/incomplete agents, reserved folders,
  missing shared skills, revision/dirty state, invalid paths, and refused
  writes. Keep executor and integration checks hermetic through the same
  fixture.

### 3. Realign the live Hermes app through setup

- Run `AiNative/scripts/setup-project.sh` against `personalAgent/` using the
  current AiNative checkout.
- Verify `.cursor/rules/personal`, `docs/agents`, and `docs/systems` point to
  AiNative; remove any stale numbered symlinks if present.
- Verify the managed `.gitignore` block contains only the current
  machine-local paths and that a real local `docs/systems/` directory would
  remain protected without `--force-workflows`.
- Update `personalAgent/AGENTS.md` critic/tester links and the active
  AiNative layout section in `personalAgent/docs/v0-implementation-plan.md`.
- Leave Docker's `/ainative:ro` mount and all other Hermes runtime behavior
  unchanged.

### 4. Align tracked specifications and design references

- Update the active adapter contract artifacts under
  `specs/001-ainative-adapter/` to name `docs/agents/`.
- Update stale adapter-path prescriptions in the 004, 005, and 006 design/task
  documents that still direct implementers to `docs/8-agents/`.
- Do not rewrite the migration ADR or deliberate old-path assertions in the
  setup self-check; those are historical/verification references, not runtime
  fallbacks. Any historical text must clearly say the old layout is retired.

### 5. Verify the complete migration

- Run the adapter-focused tests, then the complete Hermes test and lint suite.
- Run `scripts/check-ainative-link.sh` to cover new/existing projects, stale
  symlink removal, real `docs/systems/` preservation, and ignore migration.
- Run `scripts/check-agent-commands.sh` against AiNative's current
  `docs/agents/` roster and `.cursor/commands/`.
- Run `node scripts/check-doc-links.mjs` against AiNative and the consumer
  documentation; verify nested `records/*` links resolve relative to their
  containing file.
- Run a final stale-path audit and distinguish intentional historical/check
  fixture mentions from operational, test, or active-guidance dependencies.

### 6. Record the delivered change

- Update the root `CHANGELOG.md` for the delivered Spec Kit alignment
  artifacts, and the live `personalAgent/CHANGELOG.md` for the adapter,
  fixture, setup, and guidance changes, using the repositories' existing
  semantic-versioning conventions.
- Do not add a second changelog or modify the read-only AiNative checkout.

## Dependency and Execution Order

1. **Reference and baseline verification**: confirm the current AiNative tree
   and run its existing checks. This establishes that the source-of-truth
   migration is already complete.
2. **Adapter/fixture cutover**: move the fixture, remove fallback code and
   legacy fixture artifacts, update adapter tests, and run focused tests.
3. **Consumer setup and guidance**: rerun setup for `personalAgent`, update
   live links and app guidance, and verify the read-only mount remains intact.
4. **Specification alignment**: update active contract/design references and
   preserve only intentional historical or verification mentions.
5. **Full verification and version history**: run all checks, audits, and
   changelog updates.

Steps 1 and 4 are independent of the adapter code and can be prepared in
parallel. The setup projection depends on the current AiNative checkout but
not on Python changes. Focused tests must pass before the full suite; final
link/parity/setup checks are the release gate.

## Phase 1 Acceptance and Verification

- `AiNativeAdapter` accepts only a read-only checkout containing
  `docs/agents/`; it never accepts `docs/8-agents`, a top-level `agents/`
  roster, or a manifest-only/simple fixture.
- All returned agent, instruction, rule, and shared-skill paths are rooted in
  `docs/agents/`, and existing adapter behavior remains covered.
- Hermetic fixtures and focused tests pass without the live mount, credentials,
  network, or writes to AiNative.
- Rerunning setup against `personalAgent/` creates current `agents` and
  `systems` links, removes stale numbered symlinks, migrates ignore entries,
  and preserves a real systems directory unless forced.
- Consumer guidance and active specs use the four-layer vocabulary and current
  agent URLs; no operational or test dependency uses the retired agent root.
- The read-only `/ainative` mount remains unchanged.
- The adapter, full pytest/lint suite, setup self-check, parity check, and
  documentation-link check all pass, with failures visible.

## Post-design Constitution Check: PASS

The design removes obsolete compatibility behavior instead of adding a new
layer, reuses the current scripts and filesystem contracts, and keeps all
AiNative content read-only. Trust-boundary failures and migration behavior
have deterministic fixture checks. No new dependency, database, runtime
reader, alias, fallback, unresolved clarification, or constitution exception
remains.
