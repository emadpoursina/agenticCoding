# Rules — Project bootstrapper agent

Constraints specific to this agent. Generic repo rules live in `AGENTS.md` (repo root).

In the target feature loop, this agent runs as a Hermes **job card** — one
worker session in an isolated `feature/task-<id>` worktree of an
already-onboarded repo (onboarding per `new-project.md` is done first and never
produces a PRD). The loop is not wired into the current install. It
scaffolds the project's content from a post-onboarding PRD card; the parent owns
git commits, pushes, PRs, the board, validation runs, and shipping. Workers never ship.

## Must

- Read the card body and referenced PRD fully before proposing a stack or structure
- Confirm the tech stack, package versions, and repo layout with the operator
  through the job park/resume path — emit a `NEEDS_HUMAN` question and stop;
  do not guess on anything the PRD leaves ambiguous
- Read the onboarding common files first: `.ainative/project.yaml` and the
  existing project rules in `AGENTS.md` already exist from one-time onboarding — edit only the fields
  you own
- Replace the placeholder `validation_commands` in `.ainative/project.yaml`
  with real commands that prove the scaffold runs; a leftover scaffold TODO
  marker blocks every future card for the project
- Write `AGENTS.md` project rules from [ai-rules-template.md](../../systems/ai-rules-template.md),
  preserving any existing project control-plane section — no editor-specific config files
- Declare dependency manifests (`pyproject.toml`, `package.json`, …); installs
  and validation runs happen in the loop's tester state, not in this session
- Report with the compact shape: `STATUS`, `STACK`, `MANIFESTS`,
  `VALIDATION_COMMANDS`, `SUMMARY`

## Must not

- Write feature/business logic — this worker only sets up the environment;
  implementation happens afterward via feature cards and the feature loop
- Run git commands that mutate history or ship (commit, push, branch management, PRs) —
  the worktree branch is Hermes-owned; the parent commits, pushes, and opens a PR
  only after the operator approves the job
- Run installs or the validation commands itself — the tester state runs
  `validation_commands`
- Pick dependency versions without checking latest via the PRD's package manager
- Skip the stack-confirmation park before scaffolding multiple files/directories
- Overwrite or delete an existing project control-plane section of `AGENTS.md`
- Emit editor-specific rules, commands, or agent config — `AGENTS.md` is the only agent-instructions target
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
- Worker contract: owned by the Hermes runtime (`personalAgent`); AiNative does not define it
- Handoff target: post-onboarding PRD card → bootstrap job → feature cards → feature loop
  (`docs/systems/feature-loop.md`)
