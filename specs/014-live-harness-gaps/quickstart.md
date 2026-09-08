# Quickstart: Live Harness Adapter Gaps

This guide proves the live process wiring and the two small state/config fixes.
The offline checks remain deterministic and use the existing fake Pi. The
Docker proof must use the real project `pi` program and a disposable project.

## Prerequisites

- Python 3.12 and `uv`
- Git
- Docker 29 or compatible Docker Compose
- A container-runnable copy of the project Pi program, available in a runtime
  directory with its matching `manifest.json` and executable marker
- No production repository, live GitHub publication, or production task board

From the repository root:

```bash
cd personalAgent
uv sync --extra dev
```

## Offline focused checks

Run the fake-Pi and configuration checks:

```bash
uv run pytest tests/test_harness_adapter.py
uv run pytest tests/test_piv_orchestrator.py tests/test_restart_recovery.py
uv run pytest tests/test_live_piv_bridge.py tests/test_legacy_stage_removal.py
uv run ruff check src tests
```

These checks must prove:

1. The fake runtime still receives one generic request and returns one result.
2. The production-shaped process transport sends one JSON job and rejects
   malformed, extra, unsafe, or unknown output.
3. A child is stopped after its first result and after timeout.
4. The checked-in default timeout loads as `1800.0`; numeric strings are
   accepted and invalid values are rejected before start.
5. An unacknowledged legacy record remains parked without starting Pi.
6. After acknowledgement, the marker is cleared and a new process starts the
   generic harness path once.
7. No Pi SDK import, model/provider leakage, forbidden write, validation, or
   publication occurs outside its existing boundary.

The runtime marker is not executable by itself. It must name a runnable
container-visible `pi` program; Hermes rejects a marker-only directory before
using the task worktree.

## Docker live proof

Prepare a disposable runtime directory containing the real project `pi`
launcher/binary and a matching marker. The executable must run inside the
Hermes container, not only on the Mac host. Set the compose runtime mount to
that directory using the repository's documented environment variable.

Build and start the container:

```bash
export PI_RUNTIME_HOST_PATH=/absolute/path/to/container-runnable-pi-runtime
docker compose -f personalAgent/docker-compose.yml build
docker compose -f personalAgent/docker-compose.yml up -d --force-recreate
```

Verify the actual program inside the container before starting a task:

```bash
docker exec hermes-personal-agent pi --version
docker exec hermes-personal-agent sh -lc 'command -v pi'
```

The runtime directory must contain the real project Pi launcher and a
`manifest.json` with matching `adapter_id`, `version`, `revision`, and
`executable` fields. Do not substitute the offline protocol fixture for this
proof.

Run one named disposable task through the existing Hermes dispatcher, using a
disposable enrolled project and credentials kept outside the repository:

```bash
docker exec hermes-personal-agent \
  python -m hermes_kanban --config /opt/personal-agent/config/default.yaml \
  --smoke --repo owner/disposable-repo --task TASK_ID --skip
```

The proof is successful only when logs and the retained task worktree show:

- one separate `pi --mode rpc` child;
- the child working directory is the task worktree;
- exactly one JSON job entered Pi and exactly one JSON result returned;
- the result mapped to the existing generic status;
- no Pi child remained running after result or timeout;
- native worktree files remain inspectable;
- the enrolled project root, AiNative mount, overlay control state, and sibling
  worktree were not modified by the harness.

A marker-only runtime must fail before task execution. A Pi binary present only
on the Mac host must also fail the container availability check.

## Full quality gates

```bash
cd personalAgent
uv run pytest
uv run ruff check src tests
```

Do not run the Docker proof against a production repository or allow the
harness to publish. Hermes remains the owner of validation and any later
commit, push, and pull-request workflow.
