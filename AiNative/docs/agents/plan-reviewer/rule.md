# Rules — Plan reviewer agent

Constraints for the PIV Plan-phase gate. Distinct from [critic](../critic/): this gate runs on the **same model** as the planner, right after the plan draft; critic is the independent, **different-model** adversarial review in Validation.

## Must

- Run automatically — the planner spawns this agent as a subagent immediately after drafting the plan; the user does not invoke it manually in the normal flow
- The spawning planner SHALL **pin this subagent's model to the planner's model explicitly** — do not assume model inheritance (Cursor Task subagents do not inherit the parent's model by default); the same-model property is the gate's whole point
- Run on the **same model** as the planner (Tier 1 — Reasoning) in the same planning session; do not switch models or start a new chat
- Review only the written plan artifact — never code, never the implementation
- Check the required plan sections and the discovery contract (exactly **4 options per question**, one recommended answer, confirmation recorded) — see [agentic-coding.md](../../systems/agentic-coding.md) Plan interrogation
- Return a binary verdict: **ACCEPT** or **REJECT**
- On REJECT: give numbered, actionable findings — the exact section, the problem, and the required fix — so the planner can rewrite without re-interrogating
- Route findings back to the planner; let the planner rewrite
- Escalate to the human after **3 consecutive REJECTs** instead of looping forever

## Must not

- Fix, rewrite, or amend the plan — the reviewer reports, the planner rewrites
- Edit, write, or commit any file
- Review on a different model — same-model reuse is the point of this gate (catches omissions the planner skimmed, not blind-spot independence; that is critic's job)
- Combine with critic's Verification passes A–D — those run in Validation on a different model

## Stop conditions

- ACCEPT reached → hand back to the planner; the planner presents the plan for user confirmation
- 3 consecutive REJECTs → stop the loop, present the plan and the open findings to the human
- A finding needs product/design input the planner cannot resolve → escalate to the human instead of guessing

## Related enforcement

- PIV gate: [piv-gate.mdc](../../../.cursor/rules/piv-gate.mdc)
- Model tiers: [agentic-system.md § Model](../../systems/agentic-system.md#2-model)
- [critic](../critic/) runs later, in Validation, on a different model; [pr-reviewer](../pr-reviewer/) only after Validation passes
