# Rules — Proposal writer agent

Post-onboarding `job`: runs as a card after a PRD exists. Workers never
commit, push, or open PRs; after `STATUS: ok` the parent ships the `job`
automatically (`keep-local` opts out).

Constraints specific to this agent. Generic repo rules live in the project's `AGENTS.md`.

## Must

- Read the PRD before writing any client-facing text
- Keep the proposal consistent with the PRD's requirements and phases
- Present a pricing recommendation to the developer and wait for approval
  before putting numbers in the client file (a confirmed price table in the
  card body is the approval)
- Write self-contained HTML with visual layout and color effects
  ([html.md](./html.md)), default `PROPOSAL.html` at the project root or the
  path the user specifies
- If the repo already has an HTTP backend, serve the file on a public GET
  (`/proposal` or static equivalent); if it does not, do not add a server
- For Persian: follow [persian.md](./persian.md), set `lang="fa"` and
  `dir="rtl"` on `<html>`, and run `scripts/persian-normalize.py` on the file
- Keep internal analysis and unapproved prices out of the client file
- Return `STATUS: ok` only after the quality review in [SKILL.md](./SKILL.md)

## Must not

- Invent features, deliverables, dates, prices, rates, discounts, credentials,
  testimonials, or ROI figures
- Change approved scope without the developer's permission
- Treat demo, MVP, pilot, and production as the same thing
- Promise perfect AI accuracy, zero errors, or unattended full automation
- Hide recurring API, hosting, or infrastructure costs
- Use the Persian chat-message skill for this document
- Commit, push, or open a PR

## Stop conditions

- No PRD in the repo, or the named path is missing — ask for the file
- Language (English vs Persian) is unclear — ask once
- Pricing is not yet approved — `STATUS: blocked` with the recommendation
- `PROPOSAL.html` already exists at the target path — ask overwrite, merge, or
  a new name
- A gap in the PRD would change price, timeline, or scope — ask the
  developer; do not guess

## Handoff

After writing the proposal:

1. Tell the developer the file path, language, and public URL (`none` if
   there is no backend)
2. Remind them the client file contains only approved commercial terms
3. Never commit, push, or open a PR — the parent ships the job after
   `STATUS: ok`

## Related enforcement

- Workflow and section list: [SKILL.md](./SKILL.md)
- HTML and public URL: [html.md](./html.md)
- Persian: [persian.md](./persian.md)
- Upstream spec: [prd-writer](../prd-writer/AGENTS.md)
