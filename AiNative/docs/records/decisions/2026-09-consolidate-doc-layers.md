# ADR-003: Consolidate 9 doc layers into 4

**Date:** 2026-09-13
**Status:** Accepted
**Supersedes:** ADR-001 (structure), clarifies ADR-002

## Context

ADR-001 adopted a nine-folder structure under `docs/`: systems, ai-workflows, reference, debugging, snippets, decisions, postmortems, evaluations, plus the numbered `1-`…`9-` prefixes added later. In practice the structure created capture-time friction out of proportion to its retrieval value:

- Several layers were nearly empty (`postmortems/` — 0 incidents; `debugging/` — 1 real note and 6 placeholder READMEs; `snippets/` — 2 real files and 3 empty folders).
- Two pairs required a judgment call on every capture: `2-ai-workflows/` vs `8-agents/` ("generic AI template vs per-task agent"), and `3-reference/` vs `5-snippets/` ("prose vs no-prose"). That decision cost was paid constantly and produced no retrieval benefit.
- `scratch/` accumulated 16 files, signalling the Friday promotion step was too expensive with nine targets.
- The folder inventory disagreed with `ENGINEERING-OS.md`, which already used the simpler names.

The core contract — *how you work* vs *evergreen knowledge* vs *what happened* — was still valid; the split into nine was the problem.

## Decision

Consolidate `docs/` into four layers, dropping numbered prefixes:

- `docs/systems/` ← `1-systems/` + `2-ai-workflows/` (workflows + AI methodology)
- `docs/agents/` ← `8-agents/` (per-task agents, unchanged shape)
- `docs/knowledge/` ← `3-reference/` + `5-snippets/` (snippets become `knowledge/snippets/`)
- `docs/records/` ← `4-debugging/` + `6-decisions/` + `7-postmortems/` + `9-evaluations/` (dated, append-only; one subfolder per record type)

`scratch/` is unchanged. `docs/records/` gets a top-level README documenting the four record contracts. This is itself recorded here, per the ADR ritual.

The symlink tooling is updated for the clean break: `setup-project.sh` now links `docs/agents` and `docs/systems`, and removes stale `docs/8-agents` / `docs/2-ai-workflows` symlinks from existing project repos. Existing projects must re-run `./scripts/setup-project.sh <app>`.

## Consequences

**Enables:**

- One capture-time decision instead of two: *how you work / AI partner / evergreen knowledge / past record* → else `scratch/`
- Fewer folders to scan in the Friday review — fewer, larger layers
- Folder names match `ENGINEERING-OS.md`; the spec and the tree are the same vocabulary
- `records/` makes the "dated, never rewrite" contract explicit across all four record types

**Trade-offs:**

- Relative links in ~90 files had to be recomputed; the four `records/*` moves are the only depth-changing ones
- Existing app repos break until `setup-project.sh` is re-run (accepted clean break)
- `docs/2-ai-workflows/` semantics now live under `systems/`, which is a slightly broader word — the README splits workflows from AI methodology to keep retrieval clear

**Harder:**

- Nothing relied on numeric ordering, so no ordering loss; sorting is now alphabetical

## Rejected alternatives

- **Keep 9 folders** — the empty layers and the two judgment-call pairs cost more than they returned; violates ADR-002's "remove layers that add no value"
- **Keep number prefixes on the 4 folders** — numbers were a sorting device for 9 layers; with 4 they add noise and must be renumbered on any change
- **5 folders (keep `ai-workflows/` separate)** — isolates AI methodology but reintroduces the generic-vs-task-specific judgment at capture time
- **Back-compat symlinks for old paths** — reintroduces the clutter being removed; a documented re-run is cheaper
- **Merge `records/` types into one flat folder** — collides on `template.md` and `README.md`; subfolders keep each contract self-contained
