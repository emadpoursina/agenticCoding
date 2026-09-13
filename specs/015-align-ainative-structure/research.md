# Research: AiNative Structure Alignment

**Feature**: `015-align-ainative-structure` | **Date**: 2026-09-13

Phase 0 compares the authoritative `AiNative/` checkout with the nested
Hermes consumer, its fixtures, setup projection, checks, and tracked
specifications. The current AiNative migration is already present; the
consumer is the part that is still mixed between the old and current
contracts. There are no unresolved clarifications from the feature spec.

## 1. Treat the nested AiNative checkout as read-only source of truth

**Decision**: Use the existing `AiNative/docs/` tree and its current scripts as
the reference contract:

```text
docs/systems/
docs/agents/
docs/knowledge/snippets/
docs/records/{debugging,decisions,postmortems,evaluations}/
```

The checkout already contains the rewritten README, `ENGINEERING-OS.md`,
rules, commands, ADR-003, setup projection, agent-command parity check, and
documentation-link checker. Do not move, copy, or rewrite those files as part
of consumer alignment.

**Rationale**: The feature explicitly names AiNative as authoritative and
read-only. Reimplementing its migration in the consumer would create a second
methodology copy and a second setup contract.

**Alternatives considered**:

- Recreate the four-layer tree inside `personalAgent/` — duplicates
  methodology and violates the constitution.
- Keep the consumer's old numbered paths — the live mount and current
  setup contract no longer provide them.
- Add compatibility aliases — explicitly rejected by ADR-003 and the feature
  clean-break requirement.

## 2. Make `docs/agents/` the only adapter root

**Decision**: Change `personalAgent/src/hermes_kanban/ainative.py` to require
`{configured_path}/docs/agents/`. Remove the current compatibility branches
that accept a manifest-only/simple roster or `{configured_path}/agents`.
Agent listing, document loading, shared-skill resolution, revision capture,
and refused writes retain their existing semantics with paths rooted in the
new directory.

**Rationale**: The current adapter has `_simple_roster` behavior and accepts a
top-level `agents/` fallback when the old structured root is absent. That
allows a checkout which does not satisfy the current AiNative contract to
appear valid. A trust boundary must reject the missing current root rather
than guess another layout.

**Alternatives considered**:

- Accept both old and new roots during a transition — would preserve the
  retired contract and make tests unable to prove a clean break.
- Use `manifest.yaml` to select a roster — metadata does not replace the
  required `docs/agents/` directory.
- Scan all directories for plausible agent files — unsafe ambiguity and
  violates the explicit root contract.

## 3. Move the fixture contract, not the live methodology

**Decision**: Move the committed fixture tree with `git mv` from
`personalAgent/tests/fixtures/ainative-full/docs/8-agents/` to
`personalAgent/tests/fixtures/ainative-full/docs/agents/`. Remove the
fixture's unused simple-roster `agents/scout.md` and `manifest.yaml`.
Update the adapter tests and live-mount guard to use the current root, and
add a negative test for a checkout containing only the retired root.

**Rationale**: The fixture is the hermetic source used by the adapter,
executor, and integration checks. Leaving an old tree or fallback fixture
would let green tests validate a structure no longer mounted in production.
The fixture remains disposable and does not copy AiNative.

**Alternatives considered**:

- Point tests at the live mount — introduces host/container, credential, and
  roster dependence.
- Keep both fixture roots — tests could pass through the wrong root and hide
  a fallback.
- Rewrite fixture content instead of moving the directory — loses useful Git
  history and creates unnecessary churn.

## 4. Use the existing setup projection for the live app

**Decision**: Re-run `AiNative/scripts/setup-project.sh` against
`personalAgent/`. The current script already:

- links `.cursor/rules/personal` and `docs/agents`;
- links `docs/systems` unless a real local directory is present;
- removes stale `docs/8-agents` and `docs/2-ai-workflows` symlinks;
- migrates the managed `.gitignore` entries; and
- preserves a real `docs/systems` directory unless `--force-workflows` is
  explicitly supplied.

Fix remaining old-path references in the app's own `AGENTS.md` and active
`docs/v0-implementation-plan.md`. Keep `/ainative:ro` in Docker unchanged.

**Rationale**: Setup is the migration operation for existing consumers.
Rerunning it verifies the clean break in the actual enrolled test app and
keeps local project files from silently depending on aliases.

**Alternatives considered**:

- Manually create links in the app — duplicates setup behavior and misses the
  managed ignore migration.
- Change Docker to mount a second tree — does not repair the app's links or
  written guidance.
- Force-replace a real local systems directory — risks data loss and violates
  the documented setup safety behavior.

## 5. Keep verification scripts focused on current behavior

**Decision**: Use the current AiNative checks as release gates:

- `scripts/check-ainative-link.sh` validates new projects, existing projects,
  stale numbered symlink removal, ignore migration, and preservation of a
  real systems folder.
- `scripts/check-agent-commands.sh` uses `docs/agents` and checks agent,
  command, `AGENTS.md`, `SKILL.md`, rule, reserved-folder, and shared-skill
  parity.
- `scripts/check-doc-links.mjs` scans `.md` and `.mdc` files, resolves links
  relative to the containing file and the documented root convention, and
  catches the depth changes under `docs/records/*`.

The implementation should patch these scripts only if a focused run exposes a
gap; the current checked-in versions already exercise the required contract.
Old path strings in the setup self-check are intentional test inputs, not
runtime aliases.

**Rationale**: The authoritative repository already contains the requested
verification tooling. Reusing it avoids parallel validators that can drift.

**Alternatives considered**:

- Search-only audits — cannot prove symlink cleanup, link resolution, or
  command/agent parity.
- A new Python migration tool — adds a dependency and duplicates Node/Bash
  behavior.
- Delete all old-path strings, including negative assertions — would remove
  proof that the clean break actually removes stale links.

## 6. Align active specifications, preserve history deliberately

**Decision**: Update all active adapter contract/design references in
`specs/001-ainative-adapter/` and the stale fixture path prescriptions in
specs 004, 005, and 006. Update consumer guidance and links as well. Keep
retired paths only when the document is explicitly recording migration
history or testing removal of those paths, including the accepted AiNative
ADR and setup self-check fixtures.

**Rationale**: A plan or task that still tells an implementer to use
`docs/8-agents` is an operational dependency even if its code example is
old. Conversely, the ADR and negative setup assertions must name the old
paths to explain and verify the clean break.

**Alternatives considered**:

- Replace every historical mention indiscriminately — destroys useful
  migration traceability.
- Update only Python source — leaves future implementers and validators with
  the retired contract.
- Add redirects in Markdown — creates the same compatibility promise the
  feature rejects.

## 7. Verification and delivery

**Decision**: Verify in layers: focused adapter tests, full Hermes pytest and
Ruff, AiNative setup/parity/link checks, setup rerun against `personalAgent`,
and a final stale-path audit. Record the delivered consumer change in the
existing changelogs using their current semantic-versioning schemes.

**Rationale**: The migration crosses runtime code, fixtures, symlinks,
documentation links, and specifications. One green unit test cannot establish
that all consuming surfaces agree.

**Known ceiling**: The link checker validates local Markdown/MDX-style
relative links and repository-root paths, not remote URL availability. The
setup check uses disposable temporary projects, not a production app.
