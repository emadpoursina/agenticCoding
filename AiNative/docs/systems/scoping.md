# Scoping

How much to build before something is decided. Applies to a new project
and to a feature in an existing one, the same way.

> **Status: target methodology — not wired into the current install.**
> Like the rest of the [feature loop](./feature-loop.md). Learn cards are
> groomed by [task-groomer](../agents/task-groomer/SKILL.md), routed by
> [route-work](../agents/route-work/SKILL.md) to the `job` path, and run by
> the [learn](../agents/learn/SKILL.md) worker. How a harness enforces an
> appetite (timeouts, cost caps) is that harness's business, not this
> file's: the parent passes a `DEADLINE` and the worker stops at it.
> Related: [prd-writer](../agents/prd-writer/SKILL.md).

## The problem it solves

Every unit of work in the [feature loop](./feature-loop.md) pays the same
price: PRD, spec, plan, critic, tester, PR review, UAT. That price is right
for work whose *what* is decided. It is waste for work whose *what* is still
a guess: you spec, review, and harden something that may be thrown out.

The fix is to separate **building to learn** from **building to earn**, and
to cap what learning may cost.

## Two modes

Every card is in one of two modes.

| Mode | Purpose | Code | Path |
|---|---|---|---|
| `learn` | Answer one question before deciding what to build | Thrown away. Never merged to the base branch | Lightweight, no spec / critic / pr-review / UAT |
| `build` | Ship decided behavior to real users | Kept | `feature` or `change`, as today |

`build` is the normal mode. A card without `mode:` is `build`. `learn` is
always explicit: the operator opts in, or confirms a groomer suggestion.

### Learn kinds

A `learn` card names exactly one risk it reduces. The risk decides the kind.

| Kind | Risk | Question it answers | Typical output |
|---|---|---|---|
| `spike` | Feasibility | Can this be done, with this stack, within these limits? | A finding: works / does not / works with caveats, plus evidence |
| `demo` | Value, usability | Is this the right thing? Can a person use it? | Something a person tries, plus their verdict |

Viability (can the business sustain it) is a human question, not a card.

A question that touches both risks is two cards: spike first, demo second.

## Learn card contract

A `learn` card must carry all four:

1. **Question** — one sentence, answerable with yes / no / "yes, if…".
2. **Appetite** — how much we are *willing to spend*, not an estimate of
   what it will take. Wall-clock time, and an AI-cost cap where the harness
   supports one. Defaults: spike ≤ 1 day, demo ≤ 3 days.
3. **Exit evidence** — what has to exist for the question to count as
   answered (a run log, a screen recording, a person's verdict).
4. **Out of scope** — what this card will deliberately fake or skip
   (auth, persistence, error handling, real data).

A card missing any of the four is not ready.

### What learn work skips

No PRD, no `spec.md`, no `plan.md` / `tasks.md`, no critic, no tests beyond
what the question needs, no pr-review, no UAT. Mocked data, hard-coded
values, and shortcuts are expected: anything past what answers the question
is waste.

### Where learn output lives

- **The finding** is what reaches the base branch: one file,
  `docs/learn/<YYYY-MM-DD>-<slug>.md` in the project, with the question,
  the answer, the evidence, what was faked, what surprised us, and the
  decision. It ships like any `job` output.
- **Code** is never merged as code. Before the finding ships, the worker
  saves the prototype as `docs/learn/<YYYY-MM-DD>-<slug>.patch` next to the
  finding and reverts it from the worktree, so the PR holds only those two
  files. The patch is reference, never applied. If the answer is *go*, the
  build is redone through `build` mode; with agents, rebuilding is cheaper
  than living with prototype code.
- **The run** is two worker steps on the `job` path: `build` (prototype,
  evidence, one park for the operator's verdict and decision) and `finding`
  (patch, revert, write the finding). See [learn](../agents/learn/SKILL.md).

### Circuit breaker

When the appetite runs out, the work stops. Whatever was learned goes into
the finding. **No extension by default**: running out of appetite usually
means the question was too big or the approach was wrong, and more time
would repeat the mistake. To continue, open a new `learn` card with a
narrower question and a new appetite.

### Decision gate

Every finding ends with one human decision:

| Decision | Next |
|---|---|
| **Go** | The finding becomes input to `build`: a PRD (new product or large feature) or a `feature` card that cites it. |
| **Rework** | A new `learn` card with a changed question or approach. |
| **Kill** | The finding records why. Nothing else happens. |

The decision is recorded in the finding, so the finding's PR merges on
every outcome: a killed idea is a result worth keeping.

The decision is the operator's. An agent may recommend; it never decides.

## Project stage

A project has only two stages, and both come from the phase plan. There is
no separate stage field.

| Stage | True when | What it changes |
|---|---|---|
| **Pre-MVP** | The phase named by `MVP complete after:` is not merged yet | `build` work follows the phase plan only. New ideas go to `learn` or to Deferred, not into the current phase. |
| **Post-MVP** | That phase is merged | No more stages. Every new idea is a feature card; it enters as `learn` or `build` depending on how uncertain it is. |

There is no "full product" stage. A product is never finished, so a stage
for it invites gold-plating. Hardening that real users require (security,
observability, scale) is ordinary work: phase-plan items before MVP, or
feature cards after.

## Picking a mode

Ask what is at risk right now.

| If… | Then |
|---|---|
| The *what* is decided and the *how* is known | `build` — `change` if small, `feature` otherwise |
| The *what* is decided, the *how* might not work | `learn: spike`, then `build` |
| Nobody is sure people want it, or can use it | `learn: demo`, then `build` |
| A new product with an untested idea | `learn: demo` before the PRD |

When unsure between `learn` and `build` for a large or costly piece of
work, pick `learn`: a capped loss beats an uncapped one. For small work,
pick `build`: a `change` costs less than a finding.

## Where this comes from

Adapted, not copied. What AiNative takes from each:

| Source | Taken | Left out |
|---|---|---|
| Shape Up (Basecamp) | Appetite instead of estimate; circuit breaker, no extension by default | Six-week cycles, cooldown, betting-table meeting — human-team cadence |
| SVPG (Marty Cagan) | Build to learn vs build to earn; the four product risks; prototypes are disposable | Separate discovery team roles |
| Dual-track agile | Only validated work enters delivery | Two parallel tracks and backlogs |
| Spotify Think / Build / Ship / Tweak | After launch, a product stays in continuous improvement; keep the costly build stage short | Squad structure |
| Kent Beck 3X | "What is at risk right now?" as the deciding question | Explore / Expand / Extract as named stages |
| Spec-driven development | Full spec rigor for `build` | Applying it to `learn` |
