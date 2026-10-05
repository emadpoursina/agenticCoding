# New project onboarding (one-time)

One-time setup when adding/cloning a project. Run once per project, before any
feature work. This is **not** per-card work and **not** PRD setup.

Three things with similar names — do not conflate them:

| Step | When | Owner | Report |
|---|---|---|---|
| Install gate (`hermes-readiness.sh`) | Before onboarding; proves Hermes can run | Install | `PASS`/`FAIL`/`GAP`, `ONBOARDING:`/`STEP3:` |
| **Project onboarding (this file)** | Once per project; makes the repo ready for cards | Operator + Hermes CLI | Enrolled project + board + common files |
| Per-card gate (`ready`) | Before every card; branch + Spec Kit preflight | `ready` worker | `READY: ok\|blocked` |

PRD work (`prd-writer`, `project-bootstrapper`) happens **after** onboarding,
as cards through the [feature loop](../../systems/feature-loop.md). Onboarding
never reads or writes a PRD. Even an empty repo is onboarded first; then a PRD
job and a full setup loop follow.

> **Status: target flow — not wired into the current install.** The Hermes
> install provides native `hermes project` and `hermes kanban` commands, but
> no automated onboarding operation exists yet. Run the commands below by hand.

## Checklist (common things every project needs)

Same checklist for empty and non-empty repos. Never overwrite existing content.

1. **GitHub repo exists, default branch set.** Create it if missing. Clone under
   the Hermes workspace root (default `/opt/data/mnt/workspace`) as
   `<workspace-root>/<project-id>` (ID from repo name). Confirm
   `git -C <path> ls-remote --heads origin` works.
2. **Register in Hermes and give it a board:**
   ```bash
   hermes project create <name> <workspace-root>/<project-id>
   hermes kanban init
   hermes project bind-board <name> <board-slug>
   ```
   Verify (`hermes project show <name>`, `hermes kanban boards`). Hermes kanban
   is the only board. Registration records project + board; it creates no cards
   and scaffolds no code.
3. **Common files exist (create only what is missing):**
   - `README.md` — what the project is, 5 lines minimum.
   - `AGENTS.md` — project rules from
     [ai-rules-template.md](../../systems/ai-rules-template.md); preserve any
     existing control-plane section.
   - `.ainative/project.yaml` — declare `validation_commands` (copy
     [project.yaml.template](./project.yaml.template), never edit it in
     place); a scaffold TODO marker is acceptable here (the loop blocks
     cards until bootstrap replaces it with real commands).
   - `scratch/` + gitignored.
   - `.gitignore` covers scratch, env, build output.
4. **Spec Kit layout (required for `feature` cards, skipped for `change`/`job`):**
   Source is always the official Spec Kit — never copy `.specify/` or
   `.opencode/` from a sibling project repo (those contain that project's
   version, integration settings, and possibly a filled `constitution.md`).
   From the repo root, inside the container:
   ```bash
   uv tool install specify-cli==<version>  # record version in the report; 1.0.13 verified 2026-10-05
   export PATH="/opt/data/home/.local/bin:$PATH"  # uv tool dir is not on PATH in the container
   specify init --here --force --integration opencode --script sh --non-interactive --ignore-agent-tools
   ```
   (`--force` is for the non-empty repo; `--ignore-agent-tools` because the
   agent runs elsewhere. Init creates no commit.) Verify the 8 required paths:
   `.specify/` + `.opencode/commands/speckit.{specify,clarify,plan,tasks,analyze,implement,converge}.md`.
   Newer CLI versions may add extra commands (e.g. `constitution`, `checklist`,
   `taskstoissues`) — a superset is fine. If missing, note it — the per-card
   `ready` gate will block `feature` cards until it is added.
5. **Local services (if the project needs a DB):** one database per project per
   [local-shared-services.md](./local-shared-services.md).

Stop here. Do not write a PRD, scaffold the app, declare dependencies, or open
cards during onboarding.

## After onboarding

* Empty repo: file a `job` card (`## Skill: prd-writer`) to write the PRD, then
  a `job` card (`## Skill: project-bootstrapper`) to scaffold from it. See
  [project-bootstrapper](../../agents/project-bootstrapper/).
* Non-empty repo: file cards directly. If the repo needs understanding first,
  Hermes may call `scout` (read-only brief / Repo Q&A) or the standalone
  `legacy-system-assessment-agent` as on-hand tools — neither is a loop stage
  and neither runs automatically at onboarding.
* Every card ends the same way: workers never ship; the parent commits,
  pushes the branch, and opens a PR only after operator approval.

## Development (unchanged)

The card's `## Path` selects the workflow; internal workflow stages are not
Kanban cards. See the [target feature loop](../../systems/feature-loop.md).

* `feature` — desired outcome; full spec/plan/implementation/review flow.
* `change` — a small, already-specified code change.
* `job` — one named skill, such as PRD writing or bootstrap from a PRD.

## Local services

[Local shared services](./local-shared-services.md) documents MariaDB,
MongoDB, and Adminer via Docker. Create a database per project.

## Deployment

Deploy checklists and release flow: [release-management-system.md](../../systems/release-management-system.md).
