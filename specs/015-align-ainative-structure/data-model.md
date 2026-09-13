# Data Model: AiNative Structure Alignment

**Feature**: `015-align-ainative-structure`

This feature does not add a database or a new runtime state store. The model
describes the filesystem contracts shared by AiNative, the Hermes adapter, the
setup projection, fixtures, and migration checks.

## Authoritative methodology layout

**Entity**: `MethodologyLayout`

| Field | Type | Rules |
|---|---|---|
| `root` | directory path | Configured by the consumer; must be the intended AiNative checkout. |
| `agents_root` | directory path | Exactly `root/docs/agents`; required for adapter construction. |
| `systems_root` | directory path | `root/docs/systems`; exposed to app projects by setup. |
| `knowledge_root` | directory path | `root/docs/knowledge`; written-reference layer, not a Hermes runtime reader. |
| `records_root` | directory path | `root/docs/records`; contains `debugging`, `decisions`, `postmortems`, and `evaluations`. |
| `read_only` | boolean | Consumer configuration must be true; Docker mounts `/ainative` with `:ro`. |

The nested records and snippets are part of the written four-layer contract:

```text
docs/
├── systems/
├── agents/
│   ├── _skills/
│   └── <agent>/
├── knowledge/
│   └── snippets/
└── records/
    ├── debugging/
    ├── decisions/
    ├── postmortems/
    └── evaluations/
```

The adapter validates and reads only `agents_root`. It must not infer a root
from `docs/8-agents`, `root/agents`, a manifest, the current working directory,
or any other directory.

## Agent definition

**Entity**: `AgentDefinition`

The existing Python dataclass remains the read model for one immediate
subdirectory of `MethodologyLayout.agents_root`.

| Field | Type | Rules |
|---|---|---|
| `name` | string | Exact roster name; one path segment; `template` and `_skills` are not agents. |
| `purpose_path` / `purpose` | path / raw text or `None` | `AGENTS.md` when present and readable. |
| `howto_path` / `howto` | path / raw text or `None` | `SKILL.md` when present and readable. |
| `constraints_path` / `constraints` | path / raw text or `None` | `rule.md` when present and readable. |

At least one instruction file must exist. Existing partial-agent behavior,
unknown-name behavior, and raw content preservation remain unchanged. Every
returned path must be below `docs/agents/`.

## Agent dependency

**Entity**: `AgentDependency`

The existing dependency dataclass remains unchanged:

| Field | Type | Rules |
|---|---|---|
| `kind` | `"rule"` or `"skill"` | Identifies the source type. |
| `name` | string | Agent name for a rule; shared skill folder name for a skill. |
| `path` | path | Must resolve below `docs/agents/`. |
| `text` | raw text | Unmodified UTF-8 source content. |

Resolution includes the agent's `rule.md` when present and each unique
`<!-- source: _skills/<name>/SKILL.md -->` reference in first-seen order.
Missing or unreadable referenced skills fail the whole resolution; no partial
dependency list is returned.

## Setup projection

**Entity**: `ProjectSetupProjection`

This is a filesystem projection, not persisted application state.

| Path in consuming project | Expected result |
|---|---|
| `.cursor/rules/personal` | Symlink to AiNative `.cursor/rules`. |
| `docs/agents` | Symlink to AiNative `docs/agents`. |
| `docs/systems` | Symlink to AiNative `docs/systems`, unless a real directory exists and force was not requested. |
| `docs/8-agents` | Stale symlink removed; no replacement alias. |
| `docs/2-ai-workflows` | Stale symlink removed; no replacement alias. |
| `.gitignore` managed block | Contains `.cursor/rules/personal`, `docs/agents`, and `docs/systems`, with no retired entries. |

`setup-project.sh` is idempotent. It may remove stale symlinks, but it must
not delete a real local `docs/systems/` directory without the documented
force option.

## Methodology fixture

**Entity**: `MethodologyFixture`

The committed source fixture is copied into a temporary Git repository by
tests. Its agent root is exactly:

```text
personalAgent/tests/fixtures/ainative-full/docs/agents/
```

It contains representative complete, partial, incomplete, reserved, and
broken-dependency cases. It must not contain a second old-layout roster or a
manifest-only fixture that could exercise compatibility behavior.

## Verification result

**Entity**: `VerificationRun`

No result is stored. Each check exits successfully only when its contract is
proven:

| Check | Contract |
|---|---|
| Adapter pytest | Current root, agent paths, dependencies, revision, invalid paths, and read-only refusal. |
| Setup self-check | New/existing project projection, stale symlink cleanup, ignore migration, and real systems-folder protection. |
| Agent-command parity | Current agent folder and command contract, including reserved folders and shared skills. |
| Documentation links | Local Markdown/MD and MDC links resolve relative to the containing document or documented repository-root convention. |
| Stale-path audit | No active runtime/test/guidance dependency on retired numbered paths; intentional historical/negative-test mentions are classified. |

## State transition

An existing consumer moves from the old projection to the new projection only
when setup is rerun:

```text
old symlinks / old ignore entries
        │ setup-project.sh
        ▼
docs/agents + docs/systems links
current ignore entries
no old aliases
```

The adapter itself does not migrate files or create aliases. A missing
`docs/agents` root is an invalid methodology, not a state that triggers
fallback lookup.
