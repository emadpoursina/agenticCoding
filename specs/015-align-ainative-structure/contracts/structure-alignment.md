# Contract: AiNative Structure Alignment

This feature has three local contracts: the Python adapter, the setup
projection used by consuming projects, and the verification commands. They
are filesystem/process contracts, not HTTP APIs.

## Adapter contract

Existing public types remain in `hermes_kanban.ainative`:

```python
AiNativeSettings(path: Path, read_only: bool)
AiNativeAdapter(settings)
```

Construction MUST:

- require `settings.read_only is True`;
- require `settings.path` to be a directory;
- require `settings.path / "docs" / "agents"` to be a directory; and
- reject an empty path, a path without the current root, or a path containing
  only `docs/8-agents`.

The adapter MUST NOT:

- accept a top-level `agents/` simple roster;
- accept a manifest-only/simple fixture;
- fall back to `docs/8-agents`;
- scan an unrelated directory; or
- create a compatibility alias.

`list_agents()` returns sorted immediate directories below `docs/agents`,
excluding `template` and `_skills`. `get_agent(name)` and
`resolve_agent_dependencies(name)` accept only exact roster names and return
paths below `docs/agents`. Existing raw-text, incomplete-agent, unresolved
dependency, revision, and read-only error behavior remains in force.

## Setup projection contract

Invocation:

```bash
./scripts/setup-project.sh <project> [--ainative-home <path>] [--force-workflows]
```

For a valid AiNative checkout and a consuming project, setup MUST:

1. link `<project>/.cursor/rules/personal` to AiNative rules;
2. link `<project>/docs/agents` to AiNative `docs/agents`;
3. link `<project>/docs/systems` to AiNative `docs/systems` when the target is
   absent or already a symlink;
4. remove stale symlinks at `docs/8-agents` and `docs/2-ai-workflows`;
5. replace old managed ignore lines with `docs/agents` and `docs/systems`; and
6. leave a real local `docs/systems/` directory untouched unless
   `--force-workflows` is supplied.

Setup is idempotent and is the migration operation for existing projects.
It must not copy AiNative into the consumer or alter the source checkout.

## Agent-command parity contract

`check-agent-commands.sh` uses `docs/agents` as the only agent root.
Non-reserved agent directories require matching `.cursor/commands/<name>.md`
files. Each agent and each shared skill must contain the required
`AGENTS.md`, `SKILL.md`, and `rule.md` contract as defined by the current
AiNative tree, with the template's documented frontmatter exception.
Utility commands remain explicitly excluded from parity.

## Documentation-link contract

`node scripts/check-doc-links.mjs <root>` scans `.md` and `.mdc` files,
ignores remote/mail/fragment-only links, strips fragments from local links,
and resolves each remaining path relative to its containing file or the
documented repository-root convention. It MUST catch broken relative links
after files move into nested `docs/records/*` directories.

## Setup self-check contract

`scripts/check-ainative-link.sh` runs only against temporary homes and
projects. It MUST cover:

- valid current AiNative home discovery;
- machine setup idempotence;
- a new project receiving `docs/agents` and `docs/systems`;
- an existing project losing stale numbered symlinks;
- migration of old ignore entries;
- preservation of a real local `docs/systems/` directory; and
- refusal to treat AiNative itself as a consuming project.

Old numbered paths may appear in this script only as intentional stale inputs
and negative assertions. They are not accepted runtime paths.

## Operational invariants

- Docker exposes the configured mount as `/ainative:ro`.
- Hermes runtime discovery reads agents only from `/ainative/docs/agents`.
- `knowledge` and `records` are documentation layers, not new runtime readers.
- No test needs network access, credentials, or writes to the real AiNative
  checkout.
- Existing consumers must rerun setup; no back-compat alias is promised.
