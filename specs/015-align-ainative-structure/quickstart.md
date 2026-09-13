# Quickstart: AiNative Structure Alignment

This guide validates the consumer cutover to AiNative's four-layer structure.
It uses disposable projects for setup checks and committed fixtures for
adapter tests. It does not modify or require writes to the nested AiNative
checkout.

## Prerequisites

- Python 3.12 and `uv`
- Node.js
- Git
- Bash
- The repository at `/Users/emad/Projects/playground/agenticCoding`
- The nested `AiNative/` checkout with `docs/agents`, `docs/systems`,
  `docs/knowledge`, and `docs/records`

No model credentials, network access, production repository, or live task
board is required.

## 1. Verify the authoritative checkout

```bash
cd /Users/emad/Projects/playground/agenticCoding/AiNative
test -d docs/systems
test -d docs/agents
test -d docs/knowledge/snippets
test -d docs/records/debugging
test -d docs/records/decisions
test -d docs/records/postmortems
test -d docs/records/evaluations
node scripts/check-doc-links.mjs
scripts/check-agent-commands.sh
scripts/check-ainative-link.sh
```

Expected result: all three checks exit successfully. Old paths may appear only
as stale inputs and negative assertions in the setup self-check and as
historical migration text.

## 2. Re-run setup for the live Hermes app

```bash
cd /Users/emad/Projects/playground/agenticCoding/AiNative
./scripts/setup-project.sh \
  /Users/emad/Projects/playground/agenticCoding/personalAgent \
  --ainative-home /Users/emad/Projects/playground/agenticCoding/AiNative
```

Verify the projection without following or changing the source checkout:

```bash
readlink /Users/emad/Projects/playground/agenticCoding/personalAgent/docs/agents
readlink /Users/emad/Projects/playground/agenticCoding/personalAgent/docs/systems
readlink /Users/emad/Projects/playground/agenticCoding/personalAgent/.cursor/rules/personal
grep -E '^(docs/(agents|systems)|\.cursor/rules/personal)$' \
  /Users/emad/Projects/playground/agenticCoding/personalAgent/.gitignore
```

Expected result: current links and ignore entries exist. Any stale
`docs/8-agents` or `docs/2-ai-workflows` symlink is gone. A real local
`docs/systems/` directory remains in place unless the force option is used.

## 3. Run focused adapter checks

```bash
cd /Users/emad/Projects/playground/agenticCoding/personalAgent
uv run pytest tests/test_ainative_adapter.py
uv run ruff check src tests
```

The focused test must prove:

- fixture agents are rooted at `docs/agents`;
- returned instruction, rule, and shared-skill paths use that root;
- a checkout containing only `docs/8-agents` is rejected;
- complete, partial, incomplete, and broken-dependency cases retain their
  existing behavior;
- revision capture and dirty detection still work; and
- write attempts remain refused without changing the fixture.

## 4. Run the full Hermes checks

```bash
cd /Users/emad/Projects/playground/agenticCoding/personalAgent
uv run pytest
uv run ruff check src tests
```

The full suite must remain hermetic. Executor and integration fixtures must
continue to use the same current-layout methodology fixture.

## 5. Check consumer links and stale references

```bash
cd /Users/emad/Projects/playground/agenticCoding
node AiNative/scripts/check-doc-links.mjs AiNative
node AiNative/scripts/check-doc-links.mjs personalAgent
git -C personalAgent grep -n -E \
  'docs/(8-agents|2-ai-workflows|1-systems|3-reference|4-debugging|5-snippets|6-decisions|7-postmortems|9-evaluations)' \
  -- ':!*.pyc'
```

The final grep may report no lines or only deliberately retained historical
and negative-test references. It must not report an operational adapter root,
consumer guidance link, fixture path, setup output, or active specification
that still requires a retired path.

## Completion criteria

The alignment is complete when:

1. Adapter-focused and full Hermes checks pass.
2. AiNative setup, parity, and link checks pass.
3. The live app has current agent/systems links and no stale numbered
   symlinks or ignore entries.
4. Active consumer guidance and adapter-related specifications use the
   four-layer vocabulary.
5. `/ainative` remains read-only and no test writes to the real checkout.
