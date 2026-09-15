# Contract: Hermes Startup Context

This feature defines a local Python/filesystem/CLI contract. It does not add
an HTTP API, a second task store, or a provider-specific harness interface.

## Configuration contract

`personalAgent/config/default.yaml` must register exactly three roles:

```yaml
context:
  hermes_instructions: /opt/personal-agent/AGENTS.md
  system: /opt/data/hermes-context/SYSTEM.md
  user: /opt/data/hermes-context/USER.md
```

The implementation may accept different absolute container paths supplied by a
deployment configuration, but it must use those values exactly after mounts
are available. It must not translate `/Users/...`, search fallback paths, or
silently accept an unregistered role.

## Loader contract

The startup-context module exposes a small typed seam equivalent to:

```python
load_startup_context(config_path: Path) -> StartupContextSnapshot
```

Construction must:

1. parse the existing subset YAML configuration;
2. require exactly the three registered role keys;
3. validate each configured path as an absolute container-visible path;
4. require one readable, regular, non-empty UTF-8 file at that exact path;
5. reject two roles that resolve to the same file;
6. hash and retain the bytes for the current run; and
7. return role/path/revision metadata separately from full text.

The loader must not create a missing context file, rewrite a source file, or
fall back to another path. Failure text must name the role, the exact
configured path, and a safe reason such as `missing`, `not readable`,
`directory`, `duplicate registration`, `host-only path`, `empty`, or
`invalid UTF-8`. It must never include file contents.

## Startup boundary contract

`runtime.build_live_orchestrator()` must load and validate the startup
snapshot before it can return an orchestrator capable of handling a command.
The existing live board, harness, project, and workspace validation remains in
place. The snapshot is process-local and must not be serialized into
`WorkflowRecord` or `overlay.json`.

`PivOrchestrator.from_config()` may accept an optional startup snapshot for
the live entry point. Existing fixture callers that do not use the live
startup path remain valid; they do not bypass validation when invoking the
live dispatcher.

## Diagnostic contract

The CLI adds a health/startup mode:

```bash
python -m hermes_kanban \
  --config /opt/personal-agent/config/default.yaml \
  --doctor
```

`--doctor` performs the same startup validation, emits a safe diagnostic, and
exits without selecting or running a task. The diagnostic includes:

```json
{
  "ainative_root": "/ainative",
  "available_agents": ["..."],
  "configured_projects": ["..."],
  "workspace_root": "/workspaces",
  "active_harness": "pi",
  "persistent_state_path": "/var/lib/hermes-kanban",
  "context_registrations": [
    {"role": "hermes_instructions", "path": "...", "revision": "..."},
    {"role": "system", "path": "...", "revision": "..."},
    {"role": "user", "path": "...", "revision": "..."}
  ]
}
```

Only metadata is rendered. The diagnostic must not expose any registered file
body or secret. Normal command startup uses the same validation and reports
the safe registration result before handling the selected command.

## Precedence contract

Hermes resolves conflicts in this order:

```text
platform/safety
Hermes AGENTS.md
live runtime configuration
SYSTEM.md
project instructions
USER.md
current task
```

Runtime configuration wins over descriptive `SYSTEM.md` text. Preferences and
task instructions cannot override safety, project validation, or protected
branch controls. The precedence resolver is pure and must be covered with
conflicting fixture candidates.

## Coding-job isolation contract

Full text from the three registered files is available only to Hermes startup,
planning, and health/doctor code. It must not be added to:

- `ExecutePayload`;
- `AssembledContext` or model messages;
- `HarnessStartRequest` or adapter payloads;
- Kanban/task records;
- worktree or managed-project files; or
- overlay/persistent state.

Coding jobs continue to read the managed project's own instruction files from
their prepared workspace.

## First-delivery file contract

The repository must contain:

```text
personalAgent/AGENTS.md
personalAgent/docs/context/SYSTEM.example.md
personalAgent/docs/context/USER.example.md
```

`AGENTS.md` remains versioned Hermes guidance and includes a short
operator-completion note without losing its existing safety rules. The two
example files are safe placeholders that say the operator must complete them
later. They contain no passwords, API keys, tokens, private keys, or personal
data. Actual `SYSTEM.md` and `USER.md` are copied by the operator into the
persistent mounted data directory before startup and are never auto-created by
Hermes.
