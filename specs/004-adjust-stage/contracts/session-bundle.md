# Contract: harness session bundle

**Feature**: `specs/004-adjust-stage` | **Requirements**: FR-033–FR-036 | **Plan**: [../plan.md](../plan.md) (W8) | **Research**: [../research.md](../research.md) (D10, D11)

The optional drill-down input. AiNative defines the **shape** (this file and
`adjust/SKILL.md`); each harness adapter defines the **location**. No harness
path, hook name, or database table may appear in `AiNative/docs/systems/**` or in
`docs/agents/adjust/` (FR-036) — that is the line this contract draws.

---

## Shape (adapter-neutral)

| Part | Content | Required |
|---|---|---|
| `worker_prompt` | The exact one-step prompt handed to the worker | Yes |
| `worker_transcript` | Reference to the worker session's transcript, or `unavailable` | Yes (value may be `unavailable`) |
| `subagent_transcripts` | List of references; may be empty | Yes (may be empty) |
| `usage` | Tokens / cost / turns as the adapter reports them, or `unknown` | Yes |
| `completeness` | `complete \| partial \| unavailable` + a one-line reason | Yes |
| `pointer` | Path or id Adjust is given, recorded in the proposal's evidence ref as `transcript:<pointer>` | Yes |

### How Adjust is pointed at a bundle

The parent (never Adjust) attaches the pointer to the Adjust dispatch: a
directory, a file, or a store reference the adapter names. Adjust records
`bundle:<pointer>` in `EVIDENCE_USED` and `transcript:<pointer>` in the
proposal's evidence list. Adjust never searches a host filesystem for sessions.

### Rules of use

1. A bundle is never the first thing read. Card data or a report must already
   show the anomaly (input priority 3, FR-009).
2. A partial or unavailable bundle still permits a proposal, but the proposal
   says the drill-down was partial and what was missing (FR-035). Asserting a
   cause from a partial bundle is a defect.
3. Adjust must run and produce the same output with **no** bundle. A run that
   only works with transcripts violates FR-010.
4. Reading a bundle never changes a metric, a verdict, or a card state.

---

## Per-adapter obligations

Each of the four documents must have a `## Session bundle` section containing:

| Obligation | Detail |
|---|---|
| Contents | What the bundle contains, mapped onto the six parts above |
| Location | Where the worker prompt, worker transcript, subagent transcripts, and usage live on disk or in a store — with the caveat that this is the only place the path may be written |
| Pointing | How the parent points Adjust at it (path, id, export, mount) |
| Usage source | Which fields carry tokens / cost / turns, and what is `unknown` when the runtime does not report it |
| At least one caveat | A real, stated limitation about transcript availability |
| Degrade | One line: partial bundle ⇒ card data + reports + a stated partial drill-down |

### The four adapters and their known caveats

| Adapter | File | Caveat that must appear (evidence in repo / task check) |
|---|---|---|
| `claude-harness` | `docs/agents/claude-harness/SKILL.md` (or a linked section file) | A subagent-stop hook can fire before the transcript file is fully written; and the wrapper's isolated default (`--no-session-persistence`, `SKILL.md:108`) can leave no transcript at all. `report.json` already carries `sessionId`, `numTurns`, `totalCostUsd` (`SKILL.md:237-239`) |
| `cursor-harness` | `docs/agents/cursor-harness/SKILL.md` | Background subagent stop events are unreliable, so subagent transcripts may be missing; `totalCostUsd` is null when the account does not report usage (`SKILL.md:204`) |
| `pi-harness` | `docs/agents/pi-harness/SKILL.md` | A job run with `--no-session` leaves no session file, so the bundle can be unavailable by design (`SKILL.md:131`) |
| Hermes | `docs/knowledge/setup/harness.md` | The session parent link is not populated yet, so worker and subagent records cannot be reliably joined; and the container cannot see host-only transcript directories unless they are mounted |

`antigravity-harness` is **not** in scope for this contract (research D11). Its
`worker-contract.md` gains the `FRICTION` line only. If an implementer can state
its session location truthfully, an optional paragraph may be added; omitting it
fails no requirement.

---

## Verification (TF-4)

```bash
# 1. Shape exists in all four documents (case-insensitive: T025–T028 mandate the
#    heading `## Session bundle`, so an exact-case grep would false-FAIL)
rg -ni 'session bundle' \
  AiNative/docs/agents/claude-harness \
  AiNative/docs/agents/cursor-harness \
  AiNative/docs/agents/pi-harness \
  AiNative/docs/knowledge/setup/harness.md

# 2. No harness mechanics INTRODUCED BY THIS FEATURE into methodology.
#    Only added lines are in scope (SC-006 is scoped to introduced paths).
git diff -U0 AiNative/docs/systems AiNative/docs/agents/adjust | rg '^\+' | \
  rg -n '(/opt/data/mnt|state\.db|kanban\.db|~/.claude|~/.cursor|~/.pi|SubagentStop|task_runs|agent_transcript_path)'
# Expected: no output

# 3. Baseline: the three pre-existing runtime-ownership lines stay, no more.
rg -n '/opt/data/mnt' AiNative/docs/systems
# Expected: feature-loop.md:99, feature-loop.md:365, agentic-system.md:196 only
```

Manual reading: each adapter's section must name all six parts (or explicitly
mark one `unavailable`), the location, the pointing mechanism, and ≥ 1 caveat.

---

## Acceptance

- Four sections exist, one per required adapter, each with contents, location,
  pointing, usage source, caveat, and degrade line.
- The methodology documents and the `adjust` skill gain zero harness paths from
  this change (TF-4 step 2, diff-scoped, returns nothing); the three pre-existing
  runtime-ownership mentions of the read-only mount are out of scope for SC-006.
- The degrade rule appears in `adjust/SKILL.md` as well, phrased as behaviour
  rather than location ("state that the drill-down was partial").
