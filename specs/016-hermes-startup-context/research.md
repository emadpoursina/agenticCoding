# Research: Hermes Startup Context Files

**Feature**: `016-hermes-startup-context` | **Date**: 2026-09-14

The existing Hermes package already has a stdlib-only configuration parser,
the live dispatcher entry point, the AiNative adapter, the project registry,
the workspace manager, and the single overlay record. The design below adds
one narrow startup-context seam and keeps the existing task and harness
contracts unchanged. The two clarification decisions in `spec.md` are
resolved and are not reopened here.

## 1. Validate exact configured files with the existing config parser

**Decision**: Add a small startup-context module that reads a required
`context` mapping through the existing `_parse_document` subset YAML parser.
It accepts exactly these roles:

```yaml
context:
  hermes_instructions: /opt/personal-agent/AGENTS.md
  system: /opt/data/hermes-context/SYSTEM.md
  user: /opt/data/hermes-context/USER.md
```

The loader requires all three role keys, rejects unexpected role keys, keeps
the configured path unchanged for diagnostics, and resolves each file only
after configuration has been loaded. It requires an absolute container-visible
path, one readable regular file, non-empty UTF-8 content, and a distinct
resolved file for each role. It never searches a fallback path and never
creates a missing file. `/Users/...` and other host-only path forms are
rejected as invalid container configuration rather than translated.

**Rationale**: This reuses the parser and the current live `build_live_orchestrator`
startup boundary. It also makes a missing mount fail before the dispatcher can
accept a task.

**Alternatives considered**:

- Searching common host/container paths — violates exact-path and
  fail-closed requirements.
- Creating `SYSTEM.md` or `USER.md` from a template — hides an operator setup
  error and can create a file in the wrong persistent volume.
- Adding a YAML dependency — duplicates an existing parser for a small fixed
  configuration shape.

## 2. Use a content hash as the per-file revision

**Decision**: Read each file's bytes once, compute a SHA-256 hex digest, then
decode the bytes as UTF-8 for the in-memory Hermes snapshot. A metadata-only
registration record contains the role, the configured path, and the digest.
The digest is stable for the same source bytes and works for both the
versioned `AGENTS.md` and persistent files that are not Git repositories.

**Rationale**: Git commit identity is not sufficient for a persistent file and
filesystem timestamps are not a stable content revision. SHA-256 is already
available in Python's standard library and does not require storing the body.

**Alternatives considered**:

- Store full text in the operational record — creates the forbidden second
  source of truth.
- Use only `mtime`/size — can miss replacements with the same metadata.
- Require Git metadata for all three files — excludes persistent data outside
  Git.

## 3. Keep full text in a startup-only snapshot

**Decision**: Represent the loaded files with an in-memory
`StartupContextSnapshot`. It exposes role-scoped text to Hermes startup,
planning, and health/doctor code, plus a separate `registrations` view that
contains only role/path/revision metadata. The snapshot is attached only to
the live orchestrator for the current process and is never included in
`WorkflowRecord`, `ExecutePayload`, `AssembledContext`,
`HarnessStartRequest`, model messages, task records, worktrees, or overlay
JSON.

The existing coding-job path remains unchanged. In particular, project-local
files continue to be collected by `_read_workspace_files`; the three
registered Hermes files are not appended to that collection or copied into a
job payload.

**Rationale**: This satisfies the Hermes-only full-text rule without adding a
second memory store or changing the provider-neutral harness boundary.

**Alternatives considered**:

- Add the files to `ExecutePayload` or `AssembledContext` — directly leaks
  Hermes-wide context into coding jobs.
- Persist the snapshot in the overlay — exposes secrets and duplicates source
  text across runs.
- Add a separate database — violates the single native Kanban/overlay design.

## 4. Make precedence an explicit pure resolver

**Decision**: Define one ordered precedence list and a small resolver used by
Hermes planning and diagnostics:

1. platform and safety rules;
2. Hermes `AGENTS.md`;
3. live runtime configuration;
4. `SYSTEM.md`;
5. project instructions;
6. `USER.md`;
7. current task instructions.

The resolver returns the first applicable source for a named instruction and
does not merge lower-priority text over a higher-priority safety rule.
Runtime configuration is a distinct input and therefore wins over descriptive
`SYSTEM.md` text. The coding-job payload still receives project/task data
through its existing contracts, not the full registered snapshot.

**Rationale**: A named order is testable without inventing a general policy
language. Keeping it pure avoids mixing precedence calculation with filesystem
or network actions.

**Alternatives considered**:

- Concatenate all files and let a model decide — makes safety precedence
  implicit and non-deterministic.
- Make `USER.md` highest priority — conflicts with the clarified safety and
  protected-operation rules.
- Add a full policy engine — exceeds the requested startup registration slice.

## 5. Produce a safe startup diagnostic through the existing dispatcher

**Decision**: Add a `StartupDiagnostic` read model and a `--doctor` CLI mode.
The diagnostic reports:

- configured AiNative root and sorted available agents;
- configured project identities;
- workspace root;
- active harness identity;
- persistent overlay/state path; and
- each context role's configured path and content revision.

It reports no context body, environment secret, token, or private key. Normal
live startup performs the same context validation before command dispatch; the
doctor mode prints the complete safe diagnostic and exits without running a
task. Context-load failures name the role, exact configured path, and safe
reason.

**Rationale**: The existing `runtime.py` is already the live startup boundary,
and the existing adapter/registry/workspace objects provide all required
diagnostic locations without a new discovery mechanism.

**Alternatives considered**:

- Add a new service or health database — unnecessary for a read-only report.
- Print file contents for debugging — violates secret-safe diagnostics.
- Make diagnostics depend on a coding job — too late and leaks unrelated
  context.

## 6. Ship templates, not persistent files

**Decision**: Keep the actual persistent files outside Git under the mounted
Hermes data directory. Add safe templates at:

```text
personalAgent/docs/context/SYSTEM.example.md
personalAgent/docs/context/USER.example.md
```

The existing `personalAgent/AGENTS.md` remains the versioned Hermes
instruction file and receives a short startup-context/operator-completion
section without removing its current safety guidance. The templates contain
only short placeholder instructions, state that the operator must complete
them later, and contain no credentials. The operator copies them into the
mounted persistent directory before startup; Hermes never performs that copy.

**Rationale**: The repository already contains substantive safety guidance in
`AGENTS.md`, so replacing it with a placeholder would silently weaken Hermes.
Templates provide the requested first-delivery starting point while preserving
the current source of truth.

**Alternatives considered**:

- Commit actual `SYSTEM.md` and `USER.md` — risks deployment and personal
  information entering Git.
- Replace `AGENTS.md` wholesale with a placeholder — removes existing rules
  needed by the control plane.
- Auto-copy templates at startup — violates the clarified missing-file rule.

No unresolved technical clarification remains for Phase 1 design.
