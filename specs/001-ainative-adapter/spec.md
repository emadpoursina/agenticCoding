# Feature Specification: AiNative Adapter

**Feature Branch**: `001-ainative-adapter`

**Created**: 2026-08-28

**Status**: Draft

**Input**: User description: "Implement the AiNative adapter for Hermes Kanban. Spec-first, then code. Do not start other V0 phases. Small adapter that translates Hermes needing an agent into an AiNative execution contract. No PIV, no worktrees, no GitHub, no Telegram, no model calls."

## Clarifications

### Session 2026-08-28

- Q: When the methodology folder is a git repo with uncommitted local edits, how should the adapter stamp the revision so a later reviewer can trust which snapshot actually ran? → A: Succeed with commit identity plus an explicit dirty indicator
- Q: Which names may the adapter accept when loading an agent or resolving its dependencies? → A: Only exact names returned by list (single folder name; reserved folders and path-like names fail as unknown)
- Q: If an agent’s how-to document points at a shared skill that is missing or unreadable, what should resolving that agent’s dependencies do? → A: Fail resolve (and any context assembly that needs those deps) when any referenced skill is missing or unreadable
- Q: What should the adapter return for each supporting rule or skill when resolving an agent’s dependencies? → A: List of items with kind, name, path, and raw text (constraint when present, plus each referenced shared skill)
- Q: How should the three instruction documents appear on a loaded agent so a later executor can tell purpose, how-to, and constraints apart? → A: Three optional raw-text fields (purpose, howto, constraints); no concatenated blob

## User Scenarios & Testing *(mandatory)*

Hermes needs reusable engineering methodology without owning or copying it. AiNative is that methodology: a read-only collection of agent folders (purpose, how-to, and constraints), not runnable programs. This feature is the translator: given a configured methodology location, Hermes can discover agents, load their instructions, attach supporting rules and skills, and stamp the exact methodology revision onto a stable execution context.

The people who benefit are operators of the control plane and later workflow phases that will *use* this contract. This phase does not run agents, call models, or manage tasks.

### User Story 1 - Discover and load an agent by name (Priority: P1)

An operator (or a later Hermes worker) asks: “which agents exist, and what are scout’s instructions?” The adapter scans the methodology’s agent directory, returns names, and for a known name returns a definition: name, locations of the three instruction documents (purpose, how-to, constraints), and three optional raw-text fields (`purpose`, `howto`, `constraints`) — each the unmodified file contents when that file exists, omitted when it does not. There is no concatenated instruction blob. Load and resolve accept only an exact name from that list (a single folder name). An unknown name — including `template`, `_skills`, nested paths, and `../` names — fails with the same clear error. Template folders and the shared skill library are not treated as agents, unless a named agent depends on a skill from that library.

**Why this priority**: Without discovery and load, nothing else in the control plane can ask AiNative for an agent. This is the entire value of the adapter’s first slice.

**Independent Test**: Point the adapter at a small methodology tree (or the real mount). List agents and confirm known names such as scout, tester, and critic appear. Load scout and confirm `purpose`, `howto`, and `constraints` text fields are present for the files that exist (and omitted for any that do not). Ask for a name that does not exist, for `template`, for `_skills`, and for a path-like name, and confirm each fails the same way. Template and skill-library folders must not appear in the list. Resolve an agent whose how-to points at a missing shared skill and confirm resolve fails rather than returning a partial skill list.

**Acceptance Scenarios**:

1. **Given** a valid methodology location containing agent folders under `docs/8-agents/`, **When** the caller lists agents, **Then** the result includes known agent names (scout, tester, critic, and other real agent folders) and excludes `template` and `_skills`.
2. **Given** a valid methodology location with a scout agent, **When** the caller loads agent `scout`, **Then** the definition includes the name `scout`, paths to the purpose / how-to / constraint documents when those files exist, and optional `purpose`, `howto`, and `constraints` text fields holding the raw contents of those files (omitted when a file does not exist). The definition MUST NOT include a concatenated instruction blob.
3. **Given** a valid methodology location, **When** the caller loads an agent name that does not exist, **Then** the adapter fails with a distinct, visible error (not an empty definition and not a generic crash).
4. **Given** a valid methodology location, **When** the caller loads or resolves `template`, `_skills`, a nested path, or a `../` name, **Then** the adapter fails with the same unknown-agent error as (3) and does not read outside the agents roster.
5. **Given** an agent whose how-to document references supporting skills in the shared library, **When** the caller resolves that agent’s dependencies, **Then** the result is a list of items (each with kind, name, path, and raw text) covering those supporting skills and the agent’s own constraint document when it exists, without listing the skill library as an agent.
6. **Given** a listed agent whose how-to document references a shared skill that is missing or unreadable, **When** the caller resolves that agent’s dependencies, **Then** the adapter fails with a visible error and does not return a partial dependency list.

---

### User Story 2 - Stamp methodology revision onto execution context (Priority: P1)

When later phases debug “why did this task behave that way?”, they must know which methodology snapshot was in use. The adapter builds a stable execution context that always includes the configured methodology location, a revision (repository identity, commit identity, branch or ref, and a dirty indicator), the loaded agent definition, and a workflow phase when one was supplied. Task, project, and workspace slots may be empty in this phase.

**Why this priority**: Revision visibility is a stated debugging requirement. An adapter that loads instructions but cannot say which snapshot they came from is not usable in production debugging.

**Independent Test**: Build a context for a known agent against a versioned methodology location. Confirm the context contains the configured path, a non-empty commit identity, a repository identity, a branch or ref, a dirty indicator, and the agent definition. Omit task/project/workspace and confirm those slots are empty rather than invented. Supply a workflow phase and confirm it is present. Confirm a dirty working tree still succeeds and sets the dirty indicator rather than failing or omitting it.

**Acceptance Scenarios**:

1. **Given** a methodology location that is a versioned repository, **When** the caller captures revision for that path, **Then** the result includes a repository identity, a non-empty commit identity, a branch or ref, and a dirty indicator.
2. **Given** a valid methodology location, a loaded agent, and no task/project/workspace, **When** the caller builds an execution context, **Then** the context includes the configured methodology path, the revision from (1), and the agent definition; task, project, and workspace may be absent.
3. **Given** the same setup plus an explicit workflow phase, **When** the caller builds an execution context, **Then** that phase is present on the context unchanged.
4. **Given** a methodology location that is not a versioned repository, **When** the caller captures revision, **Then** the adapter fails with a clear error (it does not invent a commit identity).
5. **Given** a versioned methodology location whose working tree has uncommitted local edits, **When** the caller captures revision, **Then** the call succeeds with a non-empty commit identity and the dirty indicator set (it does not fail, invent a SHA, or omit the indicator).

---

### User Story 3 - Refuse writes and reject a missing methodology location (Priority: P1)

AiNative is a read-only methodology mount. The adapter must not copy it into workspaces, must not duplicate methodology into the control-plane repo, and must not write to it. A write attempted through the adapter must fail loudly. The methodology location comes from configuration — never from a hardcoded workstation path. If the configured location is missing or invalid, the adapter fails at the trust boundary instead of silently falling back to some other directory.

**Why this priority**: A silent fallback to a host checkout, or a successful write into methodology, would violate the constitution and make later debugging lie about which snapshot ran.

**Independent Test**: Construct the adapter with a missing or empty location and confirm it fails immediately. Construct it with a valid location, attempt a write (create, modify, delete, or copy under that path) through the adapter, and confirm it raises. Confirm no copy of methodology appears in a workspace.

**Acceptance Scenarios**:

1. **Given** configuration whose methodology path is missing, empty, or not an existing directory, **When** the adapter is constructed or first asked to use that path, **Then** it fails at that boundary with a visible error and does not substitute another location.
2. **Given** a valid methodology location (even if the underlying files are writable), **When** a caller attempts to create, modify, delete, or copy files under that path through the adapter, **Then** the adapter raises and does not swallow the failure.
3. **Given** a valid methodology location, **When** the adapter loads agents and builds context, **Then** methodology content is read in place; it is not copied into a workspace or into the control-plane repository.
4. **Given** configuration that claims the methodology is writable, **When** the adapter is constructed, **Then** it fails at the trust boundary (this phase requires a read-only mount).

---

### Edge Cases

- **Reserved folders**: `template` and `_skills` are never listed as agents. Load and resolve of those names fail as unknown agents. A skill from `_skills` appears only as a dependency of a named agent that references it.
- **Agent name identity**: Load and resolve accept only an exact name from the list (a single folder name, no slashes or `..`). Path-like names fail as unknown; the adapter MUST NOT join them onto the agents path.
- **Incomplete agent folder**: If a listed agent is missing all three instruction documents, loading it fails clearly. If some but not all exist, the definition includes the paths and text fields for the files that exist; missing documents omit both path and text field.
- **Unknown agent name**: Distinct error; not an empty definition. Reserved names and path-like names use this same error.
- **Missing or unreadable skill reference**: If a listed agent’s how-to document references a shared skill that does not exist or cannot be read, `resolve_agent_dependencies` fails clearly. It MUST NOT skip the broken reference or return only the skills that exist. `get_agent` MAY still succeed (the agent’s own `purpose` / `howto` / `constraints` fields come from its documents). Any later assembly that requires resolved dependencies inherits this failure.
- **Path is a file, not a directory**: Treated as invalid location (same as missing).
- **Path exists but has no `docs/8-agents/` directory**: Fail clearly at the trust boundary. Do not scan the rest of the methodology tree for agent folders.
- **Revision without a remote**: Repository identity falls back to the configured path; commit identity is still required.
- **Detached commit**: Commit identity is still non-empty; branch/ref records the current ref or an explicit detached indicator rather than a fake branch name.
- **Dirty working tree**: Revision capture still succeeds. Commit identity remains the current HEAD; the dirty indicator is set. Document text continues to be read from the working tree (not reconstructed from HEAD blobs).
- **Concurrent readers**: Multiple list/load/context calls against the same read-only location must not interfere; there is no writer.
- **Symlinks**: Follow the configured path as given. Do not rewrite it to a hardcoded host checkout.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The adapter MUST load the methodology location and read-only flag from operational configuration. It MUST NOT hardcode a workstation path.
- **FR-002**: The adapter MUST validate the methodology path at the trust boundary (construction or first use). Missing, empty, or non-directory values MUST fail. The adapter MUST NOT silently default to another path.
- **FR-003**: The adapter MUST require the methodology to be configured read-only. A writable configuration MUST fail at the trust boundary.
- **FR-004**: The adapter MUST discover agents as folders under `docs/8-agents/` at the configured location. If that agents root is missing, the adapter MUST fail clearly (it MUST NOT scan the rest of the methodology tree). It MUST skip `template` and `_skills` unless they are pulled in as dependencies of a named agent.
- **FR-005**: The adapter MUST expose `list_agents()` returning the discovered agent names.
- **FR-006**: The adapter MUST expose `get_agent(name)` returning an agent definition with: name; paths to the purpose document (`AGENTS.md`), how-to document (`SKILL.md`), and constraint document (`rule.md`) when present; and optional raw-text fields `purpose`, `howto`, and `constraints` (each the unmodified file contents when that file exists, omitted when it does not). The definition MUST NOT include a concatenated instruction blob. `name` MUST be an exact name from `list_agents()` (a single folder name). Unknown names, reserved folders (`template`, `_skills`), nested paths, and `../` names MUST fail with the same clean unknown-agent error. The adapter MUST NOT join a caller-supplied name onto the agents path.
- **FR-007**: The adapter MUST expose `resolve_agent_dependencies(name)` returning a list of supporting rules and skills for that agent. Each item MUST include: kind (`rule` or `skill`), name, path, and raw file text. The list MUST include the agent’s own constraint document when that file exists (`kind: rule`) plus each shared skill the how-to document references (`kind: skill`). `name` MUST follow the same identity rules as FR-006. It MUST NOT treat the skill library as an agent roster. If any referenced shared skill is missing or unreadable, the call MUST fail with a visible error; it MUST NOT return a partial list.
- **FR-008**: The adapter MUST expose `capture_revision(path)` returning `{repository, sha, branch, dirty}` with a non-empty commit identity when `path` is a versioned repository. `dirty` MUST be true when the working tree has uncommitted changes and false when it is clean. A dirty tree MUST NOT fail revision capture. When `path` is not a versioned repository, the call MUST fail clearly.
- **FR-009**: The adapter MUST expose `build_execution_context(...)` producing a stable context that MUST include: configured methodology path, revision (repository, commit identity, branch/ref, dirty indicator), agent definition, and workflow phase if given. Task, project, and workspace placeholders MAY be absent.
- **FR-010**: Any adapter operation that would create, modify, delete, or copy files under the configured methodology path MUST raise. Failures MUST NOT be swallowed.
- **FR-011**: The adapter MUST NOT copy methodology into workspaces or duplicate methodology content into this control-plane repository.
- **FR-012**: The adapter MUST NOT execute agents, call models, “run Markdown,” or depend on a specific editor being present at runtime.
- **FR-013**: The adapter MUST NOT introduce a second task store, fork the control-plane host, or expand into project registry, workspaces, Git hosting, messaging, or workflow orchestration.

### Key Entities

- **Methodology location**: Configured path to the read-only AiNative checkout/mount. Source of truth for agent folders. Never inferred from the developer’s machine layout.
- **Agent definition**: A named folder under `docs/8-agents/` with optional purpose, how-to, and constraint documents, plus optional raw-text fields `purpose`, `howto`, and `constraints` (omitted when the corresponding file does not exist). Not a concatenated blob. Not a process.
- **Agent dependency**: One supporting rule or skill attached to a named agent: kind (`rule` or `skill`), name, path, and raw file text. Typically the agent’s own constraint document plus each referenced shared skill. Used when assembling context; not a separate agent in the roster.
- **Revision**: Repository identity, commit identity, branch/ref, and dirty indicator of the methodology location. Required on every execution context. Dirty means uncommitted local changes exist; the commit identity is still HEAD.
- **Execution context**: Stable bundle for a later executor: methodology path, revision, agent definition, optional workflow phase, optional task/project/workspace (empty in this phase).

### Out of Scope

This specification covers only the adapter. Explicitly deferred:

- Executing an agent (`execute_agent`)
- PIV orchestration
- Project registry
- Workspace manager
- Git safety beyond reading revision metadata
- GitHub pull requests
- Telegram / notifications
- Model routing or model calls
- Installing a planning framework into this repo
- Obsidian
- Copying or forking AiNative
- Any other V0 Phase 1 item that is not this adapter (configuration *loading* for `ainative.path` / `read_only` is in scope; other config keys are ignored)

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Given a valid methodology location, a caller can list available agent names and load a known agent’s purpose, how-to, and constraint text (as separate fields) on the first attempt without consulting AiNative’s internal layout beyond the adapter.
- **SC-002**: 100% of listed agent names that correspond to a complete or partial instruction folder can be loaded; unknown names, reserved folders, and path-like names produce a clear failure 100% of the time (never an empty or guessed definition, never a read outside the agents roster).
- **SC-003**: 100% of execution contexts built against a versioned methodology location include the configured location, a non-empty commit identity, repository, branch/ref, and a dirty indicator, so a later reviewer can answer “which methodology snapshot ran?” and whether loaded files may differ from that commit.
- **SC-004**: 100% of write, copy, or modify attempts through the adapter against the methodology location fail with a visible error; zero writes succeed.
- **SC-005**: 100% of constructions with a missing or invalid methodology location fail at the boundary; zero runs silently substitute a different location.
- **SC-006**: A reviewer can complete five contract checks — list known agents, load scout, capture revision, refused write, invalid path — and each check fails if that behavior breaks.

## Assumptions

- **This phase is adapter-only.** Phase 0 (discovery) is done. Docker already mounts methodology read-only and operational config already contains `ainative.path` and `ainative.read_only`. Nothing else in Phase 1 (registry, workspaces, Git safety, execution identity) is started here.
- **Agents are documents, not processes.** Folders with purpose / how-to / constraint files. The adapter turns those into a contract. It does not run them.
- **Roster is discovered, not hardcoded.** Discovery notes once listed `specs-planner`; the current methodology tree may not include that folder. Tests MUST use a fixture tree that contains representative names (scout, tester, critic, and similar) so they do not depend on a live mount’s exact roster. Optional extra checks against the real mount may assert only agents that are actually present.
- **Reserved names**: `template` (starter copy) and `_skills` (shared library) are skipped as agents. `get_agent` / `resolve_agent_dependencies` accept only an exact listed name (single folder name). Reserved names and path-like names fail as unknown agents. Dependencies resolve shared skills via the how-to document’s source references (`source: _skills/<name>/...`) plus the agent’s own constraint file. Each returned dependency is `{kind, name, path, text}`. A missing or unreadable referenced skill fails resolve; it does not omit that skill from the result.
- **Instruction fields**: `purpose`, `howto`, and `constraints` are the raw contents of `AGENTS.md`, `SKILL.md`, and `rule.md` respectively, when those files exist. A missing file omits both its path and its text field. The adapter does not concatenate them, insert headings, or rewrite or summarize them.
- **Revision fields**: `sha` is the current commit identity (HEAD). `branch` is the current branch name, or a detached-ref indicator if there is no branch. `repository` is the remote `origin` URL when present, otherwise the configured path. `dirty` is true when the working tree has uncommitted changes, otherwise false. A dirty tree does not fail revision capture.
- **Trust boundary**: Adapter construction (or an explicit load of config + path) is the boundary. Invalid path or `read_only: false` fails there. Callers never receive an adapter instance bound to a guessed location.
- **Config other than `ainative.path` / `ainative.read_only` is ignored** in this phase.
- **No new third-party libraries** without an explicit owner request. Configuration parsing and revision capture must use capabilities already present on the platform.
- **Checks** live with the existing control-plane package. One set of checks must fail if the five contract behaviors break. A fixture methodology tree is preferred over requiring a live mount during those checks.
- **Public operation names** (`list_agents`, `get_agent`, `resolve_agent_dependencies`, `build_execution_context`, `capture_revision`) are the agreed contract from the implementation plan. `execute_agent` remains out of scope. Exact module layout inside the existing control-plane package is an implementation choice.
- **Cursor / editor commands are a human harness**, not a runtime dependency.
- **Implementation follows this spec**, then code; other V0 phases do not start until this adapter’s checks pass and a later spec/plan asks for them.
