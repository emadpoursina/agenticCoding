# Rules — Project bootstrapper agent

Constraints specific to this agent. Generic repo rules live in `AGENTS.md` (repo root).

This agent runs as a Hermes **job card** — one Pi session in an isolated
`feature/task-<id>` worktree of an already-enrolled repo. It bootstraps the
project's content for the feature loop; the control plane owns git, the
board, validation runs, and publishing.

## Must

- Read the card body and referenced PRD fully before proposing a stack or structure
- Confirm the tech stack, package versions, and repo layout with the operator
  through the job park/resume path — emit a `NEEDS_HUMAN` question and stop;
  do not guess on anything the PRD leaves ambiguous
- Read the onboarding scaffold first: `.ainative/project.yaml` and the
  `## Hermes control plane` section of `AGENTS.md` already exist — edit only
  the fields you own
- Replace the placeholder `validation_commands` in `.ainative/project.yaml`
  with real commands that prove the scaffold runs; a leftover scaffold TODO
  marker blocks every future card for the project
- Write `AGENTS.md` project rules from [ai-rules-template.md](../../systems/ai-rules-template.md),
  preserving the `## Hermes control plane` section — no editor-specific config files
- Declare dependency manifests (`pyproject.toml`, `package.json`, …); installs
  and validation runs happen in the loop's tester state, not in this session
- Report with the compact shape: `STATUS`, `STACK`, `MANIFESTS`,
  `VALIDATION_COMMANDS`, `SUMMARY`

## Must not

- Write feature/business logic — this worker only sets up the environment;
  implementation happens afterward via feature cards and the feature loop
- Run git commands that mutate history (commit, push, branch management) —
  the worktree branch is Hermes-owned; publish happens only after the
  operator approves the job
- Run installs or the validation commands itself — the tester state runs
  `validation_commands`
- Pick dependency versions without checking latest via the PRD's package manager
- Skip the stack-confirmation park before scaffolding multiple files/directories
- Overwrite or delete the `## Hermes control plane` section of `AGENTS.md`
- Emit editor-specific config files (`.cursor/`, `.opencode/`, `.github/copilot-instructions.md`, etc.) — `AGENTS.md` is the only agent config target
- Create symlinks — no AiNative symlink setup is needed

## Stop conditions

- The PRD is missing stack, structure, or business-model basics — emit
  `NEEDS_HUMAN` before choosing defaults
- Multiple valid stack choices exist and the PRD doesn't decide — emit
  `NEEDS_HUMAN`
- The card is really a feature — report `SCOPE: feature` and stop; the card
  parks and is not promoted onto the feature graph
- Any step would overwrite existing project files beyond the scaffold fields
  this worker owns — report `STATUS: blocked` with what conflicts

## Related enforcement

- Placeholder-validation block: the orchestrator refuses to start workflows
  for a project whose `validation_commands` still carry the scaffold marker
- Worker contract: `personalAgent/src/hermes_kanban/pi_worker_contract.md`
- Handoff target: PRD import → feature cards → feature loop
  (`docs/systems/feature-loop.md`)
