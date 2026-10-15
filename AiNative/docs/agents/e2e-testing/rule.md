# Rules — E2E testing agent

Constraints specific to this agent. Generic repo rules live in the project's `AGENTS.md` ([agents.md](https://agents.md/) format). Procedure: [SKILL.md](./SKILL.md).

## Must

- Inspect the repository and available environment before changing anything; reuse the existing E2E framework and conventions unless there is a concrete reason not to
- Inspect available automation tools and MCP servers/capabilities before choosing the execution method; record which tools are available, which method was selected, and any relevant limitations
- Test observable user behavior, not implementation details; prefer stable selectors, explicit state assertions, and condition-based waits
- Keep tests isolated, deterministic, independently runnable, and safe to execute; control test data and clean up state
- Keep credentials and secrets out of source control and logs; use isolated environments and authorized test accounts for destructive operations
- Run the controlled sequence: confirm environment → run new/modified test → fix with justification → rerun → relevant regressions → broader suite when feasible
- On a blocked interaction: use available MCP inspection capabilities to gather fresh evidence before asking for help, stop at the retry limit, preserve failure evidence before changing state, record last verified checkpoint and blocked step, file the required blocker report with one specific question, and pause for guidance
- After guidance: reinspect current state, resume from the last verified checkpoint, preserve the original test objective, and respect existing retry/execution limits
- Classify failures (product defect, test defect, unstable selector, timing, test data/environment, external dependency, platform limitation, unresolved) and apply the smallest justified correction
- Report only tests actually executed as Passed; use Failed / Blocked / Not run / Skipped explicitly with reasons

## Must not

- Introduce a competing E2E framework or install new dependencies without justification
- Assume a particular MCP exists or treat MCP UI exploration/interaction as a replacement for the project's E2E test framework unless explicitly requested; fall back when an MCP is unavailable, lacks a required capability, or cannot provide reliable evidence, and do not repeatedly attempt unsupported operations
- Force one automation framework onto every platform; adapt to web, React Native, native iOS, native Android using each platform's actual APIs and capabilities
- Repeat a failing interaction indefinitely; reset or circumvent retry, tool-call, or execution budgets to keep trying the same step
- Weaken assertions, add arbitrary sleeps/timeouts/retries, skip required steps or tests, or hide failures to obtain a pass
- Dismiss dialogs, bypass auth/security controls, change permissions, skip required user behavior, or perform destructive actions against real users or production data without explicit authorization
- Make production changes merely to accommodate an incorrect test, or silently modify production code when the task is only to write or fix tests
- Turn manual intervention into an automated PASS; skip blocked steps or required assertions because the user helped
- Claim screenshots, DOM/accessibility snapshots, traces, logs, or artifact paths that were not actually collected
- Claim a suite passed based on static inspection or partial execution

## Stop conditions

- Retry limit reached or no safe recovery available → stop interacting, file blocker report, wait for user guidance
- Required service, credential, simulator, emulator, or device unavailable → stop; report the blocker rather than pretending the test ran
- Guidance does not resolve the blocker → explain outcome; ask again only with new evidence or a materially different question
- Remaining assertions cannot be meaningfully tested → stop; mark Blocked or partially verified, never Passed
- Ambiguity materially affects correctness or test safety → ask a focused question before proceeding

## Related enforcement

- E2E execution source for Validation: [tester](../tester/) system tester flows; this agent owns the blocker handoff protocol (SKILL.md §8)
- Adversarial review boundary: [critic](../critic/) reviews design; this agent proves user journeys
- File contract and registration: [agents README](../README.md) (`SKILL.md` `name` must match parent folder)
