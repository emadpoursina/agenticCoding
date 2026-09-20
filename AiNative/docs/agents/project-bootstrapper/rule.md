# Rules — Project bootstrapper agent

Constraints specific to this agent. Generic repo rules live in `AGENTS.md` (repo root).

## Must

- Read the input project documentation file fully before proposing a stack or structure
- Confirm the tech stack, package versions, and repo layout with the user before running installs — ask, do not guess, on anything the doc leaves ambiguous
- Follow the [Bootstrap checklist](../../knowledge/setup/new-project.md#bootstrap-checklist) in `new-project.md`
- Write `AGENTS.md` at the repo root from [ai-rules-template.md](../../systems/ai-rules-template.md), dropping the legacy Cursor frontmatter — use only the markdown body. Fill it with the confirmed stack and constraints
- Add a PIV-gate section inside `AGENTS.md` that enforces plan approval before multi-file implementation (point it at [agentic-coding.md](../../systems/agentic-coding.md) and the critic/tester agents)
- Create `scratch/` and add it to `.gitignore`
- Use Conventional Commits for the initial scaffold commit(s)

## Must not

- Write feature/business logic — this agent only sets up the environment; implementation happens afterward via PIV
- Pick dependency versions without checking latest via `bun` (or the doc's package manager)
- Skip the PIV-gate plan confirmation before scaffolding multiple files/directories
- Emit editor-specific config files (`.cursor/`, `.opencode/`, `.github/copilot-instructions.md`, etc.) — `AGENTS.md` is the only agent config target
- Create symlinks — opencode uses its own native subagents; no AiNative symlink setup is needed

## Stop conditions

- The input doc is missing stack, structure, or business-model basics — ask before choosing defaults
- Multiple valid stack choices exist and the doc doesn't decide — ask the user
- Any step would overwrite existing project files — confirm first

## Related enforcement

- PIV gate: `AGENTS.md` PIV-gate section
- Handoff target for implementation: [agentic-coding.md](../../systems/agentic-coding.md)
