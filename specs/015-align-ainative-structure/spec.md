# Feature Specification: AiNative Structure Alignment

**Feature Branch**: `015-align-ainative-structure`

**Created**: 2026-09-13

**Status**: Draft

**Input**: User description: "Compare the current agenticCoding consumer with the
new AiNative four-layer documentation structure and align all references,
mounts, setup, tests, specs, and tooling. Make a clean break with no
back-compat aliases."

## Scope and baseline

AiNative is the authoritative read-only methodology checkout at
`/Users/emad/Projects/playground/agenticCoding/AiNative`. Its accepted
structure is:

- `docs/systems/`: the former systems and AI-workflow material
- `docs/agents/`: the former agent material
- `docs/knowledge/`: the former reference material, with snippets under
  `docs/knowledge/snippets/`
- `docs/records/`: debugging, decisions, postmortems, and evaluations under
  their respective subfolders

This feature aligns **two consumers** of that layout:

- this Spec Kit repository (`agenticCoding`): adapter, fixtures, tests,
  guidance, and tracked specifications
- the live Hermes app (`personalAgent/`): the enrolled project that mounts
  AiNative and must match the new paths after setup

AiNative itself is a reference and read-only mount for this feature; it is not
modified or copied into either consumer.

## Clarifications

### Session 2026-09-13

- Q: Which project should we align to AiNative's new four-layer docs layout? → A: Both this repo (agenticCoding: adapter, tests, fixtures, specs) and the live Hermes app (personalAgent)
- Q: For the live Hermes app, what should we actually change? → A: Both: re-run setup and fix leftover old-path references
- Q: Besides agents, which AiNative folders should the running app actually use? → A: Agents plus systems (setup links those two into the app). Architecture: Hermes loads agents only from `docs/agents/`; setup also links `docs/systems` into the app. `knowledge` and `records` stay methodology docs, not a new runtime reader.
- Q: Older feature specs still say docs/8-agents as if that is the live contract. What should we do with those writings? → A: Also update old specs that still prescribe the live adapter path (recommended). The live app is still a test project and may be realigned cleanly; do not rewrite every completed historical task note unless it still tells implementers to use the retired path.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Read agents from the current AiNative layer (Priority: P1)

An operator runs Hermes with the current AiNative checkout mounted read-only.
The adapter discovers and loads agents from `docs/agents/`, resolves each
agent's instruction documents and shared skills, and records paths under that
layer. The current `/ainative` mount location remains usable, while the
outdated numbered agent path is not treated as an alternate location.

**Why this priority**: Agent discovery is the consumer's runtime contract with
AiNative. It must match the authoritative tree before tests or operational
documentation can be trusted.

**Independent Test**: Point the adapter at a temporary git copy shaped like the
current AiNative tree. List and load a known agent, resolve its rule and shared
skill, inspect every returned path, and confirm the old numbered agent location
is neither required nor accepted.

**Acceptance Scenarios**:

1. **Given** a read-only AiNative checkout containing `docs/agents/` and valid
   agent folders, **When** Hermes lists agents, **Then** it returns the
   expected agent names and excludes reserved template and shared-skill
   folders.
2. **Given** a known agent under `docs/agents/`, **When** Hermes loads and
   resolves it, **Then** purpose, how-to, constraint, and shared-skill data
   point to files under the current layer and preserve their existing raw
   content.
3. **Given** a methodology checkout without `docs/agents/` but with an old
   numbered agent folder, **When** Hermes validates the checkout, **Then** it
   fails clearly and does not fall back to the old folder or another path.
4. **Given** the container exposes the configured `/ainative` mount
   read-only, **When** the live-mount roster check runs, **Then** it inspects
   `/ainative/docs/agents/` and does not write to the mount.

---

### User Story 2 - Keep the consumer's tests, fixtures, and guidance aligned (Priority: P1)

Maintainers update the consumer without having to remember which parts still
use the old layout. The adapter implementation, fixture methodology, tests,
live-mount checks, and project guidance all use the same `docs/agents/`
contract. Existing read-only, revision, dependency, and unsafe-write behavior
continues to be tested rather than being weakened during the path migration.

**Why this priority**: Stale fixtures or documentation can make a green test
run validate a structure that no longer exists in the mounted source of truth.

**Independent Test**: Run the adapter, executor, import, and focused live-mount
tests against fixtures whose agent files live under `docs/agents/`; inspect
the consumer guidance and source for stale numbered-agent references.

**Acceptance Scenarios**:

1. **Given** the committed methodology fixtures, **When** the focused tests
   copy and initialize a fixture repository, **Then** all agent, skill,
   revision, and write-refusal assertions use `docs/agents/`.
2. **Given** an executor attempts to write to an agent instruction file,
   **When** the write-refusal check runs, **Then** the test targets the
   current agent layer and still proves the read-only mount is unchanged.
3. **Given** a maintainer follows the consumer's workflow guidance, **When**
   they open the critic or tester reference, **Then** the links resolve to
   `docs/agents/critic` and `docs/agents/tester`.
4. **Given** an audit scans current consumer source, tests, and guidance,
   **When** it searches for retired layout references, **Then** it finds no
   operational or test dependency on the retired numbered paths.

---

### User Story 3 - Verify the complete four-layer migration (Priority: P2)

Maintainers can verify that the consumer and the AiNative setup contract
agree on all four semantic layers. Documentation cross-references, setup
behavior, command/agent parity, and link checks describe the current paths.
Existing projects are migrated by rerunning setup; no compatibility symlinks
are retained.

**Why this priority**: A path migration is incomplete if runtime code is
updated but setup tooling, links, or specifications continue to recreate the
old structure.

**Independent Test**: Run the current AiNative setup self-check, agent-command
parity check, and documentation-link check; inspect the consumer's tracked
Markdown specifications and the resulting temporary project layout.

**Acceptance Scenarios**:

1. **Given** a new or existing temporary app repository, **When** the current
   setup workflow runs, **Then** it provides `docs/agents` and `docs/systems`,
   removes stale `docs/8-agents` and `docs/2-ai-workflows` symlinks, and
   updates the managed ignore entries to the new paths.
2. **Given** all current Markdown and rule documents, **When** the
   documentation-link check runs, **Then** relative links resolve against the
   four-layer tree, including links whose depth changed under
   `docs/records/{debugging,decisions,postmortems,evaluations}/`.
3. **Given** the agent folders and command files in the current AiNative
   checkout, **When** command/agent parity is checked, **Then** the check
   uses `docs/agents` and reports no missing, orphaned, or malformed agent
   contract.
4. **Given** a consumer project with old path references in its tracked
   specs, **When** the alignment audit completes, **Then** its active
   references describe `systems`, `agents`, `knowledge`, and `records`, with
   no back-compat alias requirement.
5. **Given** the live Hermes app still has old numbered links or ignore
   entries, **When** alignment runs, **Then** setup is rerun and leftover
   old-path references in that app's own files are corrected.

---

### Edge Cases

- A methodology path is empty, missing, not a directory, or marked writable:
  validation fails without binding to the current working directory.
- `docs/agents/` exists but is empty or contains only reserved folders:
  discovery returns no usable agents and reports incomplete agent data when a
  named agent is requested.
- An agent has a missing or unreadable `AGENTS.md`, `SKILL.md`, `rule.md`, or
  referenced shared skill: existing incomplete-agent or unresolved-dependency
  behavior remains visible; no partial dependency result is returned.
- A fixture or temporary app contains both old and new symlinks: setup removes
  only the stale old symlinks and preserves a real local `docs/systems/`
  directory unless the existing force behavior explicitly permits replacement.
- A relative link moves from a root layer into a nested `records/` layer:
  validation resolves it from the containing document and catches broken
  depth changes.
- The current consumer is tested without a live AiNative mount: fixture tests
  remain hermetic and do not require credentials, network access, or writes to
  the real checkout.
- A historical record needs to explain the migration: it may name the old
  layout as history, but active setup, runtime, test, and link behavior must
  not depend on it.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The consumer MUST treat the current AiNative full methodology
  layout as `docs/agents/`, `docs/systems/`, `docs/knowledge/`, and
  `docs/records/`, with `docs/knowledge/snippets/` nested under knowledge and
  `docs/records/{debugging,decisions,postmortems,evaluations}/` nested under
  records. Runtime use is limited to `docs/agents/` (Hermes adapter discovery)
  plus `docs/systems` where setup links it into the app. `knowledge` and
  `records` MUST be aligned in written references and link checks; they MUST
  NOT gain a new runtime reader.
- **FR-002**: The AiNative adapter MUST discover full-layout agents only under
  `docs/agents/` and MUST reject a missing current agent layer at the trust
  boundary. It MUST NOT fall back to `docs/8-agents`, create an alias, or scan
  an unrelated directory for agents.
- **FR-003**: Agent listing, loading, dependency resolution, revision capture,
  and read-only write refusal MUST preserve their existing behavior while
  returning paths rooted in `docs/agents/`.
- **FR-004**: The configured `/ainative` container mount MUST remain
  read-only, and live-mount checks MUST inspect the current
  `/ainative/docs/agents/` path. This feature MUST NOT copy AiNative into the
  consumer or modify the mounted checkout.
- **FR-005**: Committed methodology fixtures MUST use `docs/agents/` for
  agent folders, reserved folders, and shared skills. They MUST continue to
  cover complete agents, incomplete agents, broken dependencies, revision
  capture, empty-path rejection, and refused writes.
- **FR-006**: Adapter, executor, live-mount, import, and focused integration
  tests MUST assert the current paths and MUST contain no operational
  dependency on the retired numbered agent path.
- **FR-007**: Consumer guidance MUST link agent references through
  `docs/agents/` and MUST not direct maintainers to retired agent URLs.
- **FR-008**: Consumer specifications and design artifacts that still
  prescribe the live AiNative contract MUST be updated to the current agent
  path and four-layer vocabulary. This includes earlier feature specs whose
  requirements are still the adapter contract. Completed historical task
  notes MAY keep old paths as a record of what was built then, unless those
  notes still instruct implementers to use the retired layout. References
  that describe the migration historically MUST NOT prescribe compatibility
  aliases or fallback lookup.
- **FR-009**: The setup workflow used for consuming projects MUST provide
  `docs/agents` and `docs/systems`, remove stale `docs/8-agents` and
  `docs/2-ai-workflows` symlinks, and migrate its managed ignore block to the
  new paths. A real local `docs/systems/` directory MUST remain protected
  unless the documented force option is used. The live Hermes app MUST be
  updated by rerunning that setup **and** by correcting leftover old-path
  references in its own files. The feature MUST NOT leave the live app as a
  later manual-only follow-up.
- **FR-010**: Documentation-link validation MUST scan current Markdown and
  rule documents and MUST resolve links relative to their containing file or
  the documented repository-root convention. It MUST cover the depth changes
  introduced by the nested `records/` folders.
- **FR-011**: Agent-command parity validation MUST use `docs/agents` as its
  agent root and MUST continue to validate the `AGENTS.md`, `SKILL.md`, and
  `rule.md` contract, reserved folders, and command parity.
- **FR-012**: The alignment MUST be a clean break. It MUST NOT add
  compatibility symlinks, duplicate old folders, or fallback lookup logic for
  the retired numbered layout. Existing consuming projects are expected to
  rerun setup.
- **FR-013**: The feature MUST update this Spec Kit repository and the live
  Hermes app so both match the current four-layer contract. The nested
  AiNative checkout remains the reference source and read-only methodology
  mount and MUST NOT be modified or copied.
- **FR-014**: Verification MUST include the focused adapter/executor checks,
  the setup self-check, the agent-command parity check, and the
  documentation-link check, with failures reported rather than masked.

### Key Entities

- **AiNative methodology mount**: The configured read-only checkout exposed to
  the consumer at `/ainative`; its full layout is the source of truth.
- **Semantic documentation layer**: One of `systems`, `agents`, `knowledge`,
  or `records`, with snippets and record types nested under their owning layer.
- **Consumer adapter contract**: The agent discovery and instruction-loading
  boundary that maps the mounted `docs/agents/` tree into Hermes.
- **Methodology fixture**: A committed disposable tree used by hermetic tests
  to prove the adapter contract without reading or modifying the live mount.
- **Migration verifier**: The setup, parity, and link checks that prove the
  new paths are usable and no stale aliases are recreated.

## Out of Scope

- Reorganizing, rewriting, or committing changes to the nested AiNative
  checkout; it is the authoritative reference for this feature. Alignment of
  `personalAgent/` is limited to consuming the current layout (paths, mounts,
  setup outputs, and local references), not forking AiNative.
- Changing Hermes task storage, orchestration, Pi execution, model routing,
  workspaces, GitHub, Telegram, or publication behavior.
- Adding new dependencies, a second methodology copy, or a new task database.
- Preserving old numbered paths through aliases, fallback lookup, duplicate
  folders, or compatibility redirects.
- Redesigning the four semantic layers or changing the accepted AiNative ADR.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: In 100% of full-layout fixture and live-mount checks, agent
  discovery and returned instruction/dependency paths use `docs/agents/`, and
  no check succeeds by using the retired numbered agent path.
- **SC-002**: The focused adapter, executor, import, and integration checks
  pass with fixtures rooted at `docs/agents/`, including read-only refusal,
  revision, incomplete-agent, broken-dependency, and invalid-path cases.
- **SC-003**: The setup self-check passes for both new and existing temporary
  projects: it creates `docs/agents` and `docs/systems`, removes both stale
  numbered symlinks, and leaves the migrated ignore block without old entries.
- **SC-004**: The agent-command parity and documentation-link checks complete
  successfully with the current four-layer tree and report zero broken
  current-path links or agent/command contract violations.
- **SC-005**: An audit of consumer source, tests, guidance, and specifications
  that still prescribe the live adapter contract finds zero operational
  dependencies on retired numbered paths and zero newly introduced
  compatibility aliases. Completed historical task notes may still mention
  the old layout as a record of past work.
- **SC-006**: The `/ainative` mount remains read-only in the existing Docker
  configuration, and no test or implementation writes to the real AiNative
  checkout.
- **SC-007**: The migration can be verified without network access, live model
  credentials, or a production repository; fixture-based checks remain
  deterministic and complete on the existing test toolchain.

## Assumptions

- The nested AiNative checkout and its accepted migration commit are the
  source of truth for the four-layer names and file placement.
- The container mount target remains `/ainative`; only the path below it
  changes from the retired numbered agent layer to `docs/agents/`.
- The existing setup tooling already defines the intended clean-break
  behavior; the consumer alignment will verify and consume that behavior
  rather than add a second setup implementation.
- Existing adapter semantics, read-only guarantees, fixture coverage, and
  operational configuration remain valid unless a path assertion directly
  conflicts with the current AiNative tree.
- Historical specifications and migration records may mention the former
  layout for traceability, but active code, tests, setup, and links never use
  it as a compatibility path.
- Alignment covers both this repository and the live Hermes app. The live
  app is updated by rerunning AiNative setup and by fixing leftover old-path
  references in that app's own files. Operators still rerun setup because
  there are no back-compat aliases.
