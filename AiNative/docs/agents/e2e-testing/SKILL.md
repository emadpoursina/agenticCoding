---
name: e2e-testing
description: >-
  Plan, implement, execute, debug, and maintain end-to-end tests for web,
  native iOS, native Android, React Native, and other application platforms.
  Use when testing real user journeys, adding E2E coverage, verifying
  cross-layer application behavior, or diagnosing E2E failures. Inspect the
  project's existing test stack and available automation tools/MCPs before
  choosing tools. When UI interaction becomes blocked, use available
  inspection capabilities to gather fresh evidence, stop at the retry
  limit, collect diagnostic evidence, request targeted human guidance,
  and resume from the last verified checkpoint.
---

# E2E Testing

## 1. Purpose

Create reliable, maintainable end-to-end tests that verify important
user journeys through the application's real user-facing interface.

Optimize for:
- Confidence in real user workflows.
- Deterministic and independently runnable tests.
- Clear failure diagnosis.
- Minimal test maintenance and duplication.
- Efficient use of execution time and tokens.
- Honest reporting of verification results.

The goal is not to maximize the number of tests. It is to provide
meaningful evidence that important behavior works.

## 2. Core Rules

1. Inspect the project before changing it.
2. Reuse the existing testing framework and conventions when appropriate.
3. Test observable user behavior rather than implementation details.
4. Prefer stable selectors, explicit state assertions, and condition-based waits.
5. Keep tests isolated, deterministic, and safe to execute.
6. Never repeat a failing interaction indefinitely.
7. When the retry limit is reached, stop and request human help with evidence.
8. Never report a test as passing unless it was actually executed successfully.
9. Do not silently weaken assertions, skip required steps, or hide failures.
10. Make the smallest justified change that provides meaningful coverage.
11. Preserve the original test objective when recovering from a failure.
12. Distinguish product defects, test defects, environment blockers, and
    unverified assumptions.

## 3. Discover the Project

Before implementing tests, inspect the repository and available environment.

Identify:

- The application's platform, framework, and entry points.
- Existing E2E frameworks, dependencies, configuration, and test conventions.
- Available commands for starting the app and running tests.
- Existing test helpers, fixtures, page objects, screen objects, and utilities.
- How authentication and test accounts are configured.
- How test data is created, isolated, and cleaned up.
- Required services, backend dependencies, environment variables, and secrets.
- Available browser, simulator, emulator, device, and diagnostic tools.
- Existing CI workflows and expected verification commands.

Use repository evidence instead of guessing.

If a suitable framework already exists, use it unless there is a concrete
reason not to. Do not introduce a competing framework or install new
dependencies without justification.

If no E2E framework exists, choose one based on the target platform,
project stack, required coverage, execution environment, and maintenance cost.

Do not assume a command, tool, device, or capability is available until
the project or runtime confirms it.

### 3.1 Discover Available Automation Tools and MCPs

Before choosing how to interact with the application, inspect the tools
available in the current agent environment, including MCP servers and
their exposed capabilities.

Check whether available tools can provide:

- Browser automation and DOM inspection.
- Screenshots, accessibility trees, and element inspection.
- Mobile simulator, emulator, or real-device interaction.
- App installation, launch, navigation, and UI interaction.
- Logs, traces, test results, and failure artifacts.

Prefer an already available, suitable automation tool when it meets
the testing requirements. Do not assume that a particular MCP exists;
inspect its actual capabilities and limitations.

Choose the execution method based on the project and available tools:

1. Existing project test framework and runner.
2. Suitable MCP tools for application interaction, inspection, and
   debugging.
3. Platform-native CLI or automation APIs when needed.
4. A combination of these when it provides the most reliable workflow.

An MCP used to explore or interact with the UI does not automatically
replace the project's E2E test framework. Prefer implementing
repeatable, maintainable tests in the project's established framework
unless the user explicitly requests a different approach.

If an MCP is unavailable, lacks a required capability, or cannot
provide reliable evidence, fall back to an appropriate supported
method. Do not repeatedly attempt unsupported operations.

Record which tools are available, which method was selected, and
any relevant limitations before implementation.

## 4. Plan the User Journey

Translate the requested behavior into observable user journeys.

For each journey, establish:

- Starting conditions.
- The user's actions.
- The screens, routes, or application states involved.
- Expected visible results.
- Important persisted state or backend side effects.
- Relevant validation and boundary conditions.
- Significant failure and recovery behavior.
- Any external dependencies that require controlled test data.

Prioritize:

1. Critical happy path.
2. Important validation and boundary cases.
3. High-impact failure and recovery paths.
4. Regression cases related to the requested change.

Prefer a few meaningful end-to-end tests over an unnecessarily large suite.

Use unit, integration, or API tests for isolated logic that does not need
to be verified through the UI. Use E2E tests where interaction between
application layers or the real user workflow matters.

When requirements are ambiguous but reasonable assumptions can be made,
document them and proceed. Ask a focused question when an ambiguity
materially affects correctness or test safety.

## 5. Implement Tests Using the Existing Stack

Inspect the actual application before writing selectors or interactions.

Verify relevant routes, screens, controls, accessible names, test IDs,
and expected application state using the available tools.

General requirements:

- Use descriptive test names that express user-visible outcomes.
- Prefer accessible roles, labels, and dedicated test identifiers.
- Reuse existing fixtures, helpers, and conventions.
- Keep setup, actions, and assertions easy to understand.
- Keep tests independent and safe to run individually.
- Control test data and clean up state where appropriate.
- Avoid order-dependent tests and uncontrolled shared mutable state.
- Keep credentials and sensitive information out of source control and logs.
- Avoid duplicating existing coverage without a clear reason.
- Do not create unnecessary abstractions or a custom testing DSL.
- Do not make production changes merely to accommodate an incorrect test.

Use the real backend where its integration is part of the behavior being
verified. Use controlled fixtures, seeded data, or network mocks when
appropriate for determinism, without undermining the behavior the test
is supposed to prove.

Use isolated environments and authorized test accounts for destructive
operations. Do not perform destructive actions against real users or
production data without explicit authorization.

## 6. Platform Adaptation

The workflow is shared across platforms; the automation implementation is not.

First identify the platform and framework. Then follow that framework's
actual APIs, selectors, commands, and diagnostics.

Examples of platform-specific concerns:

### Web

- Browser lifecycle and browser contexts.
- DOM inspection and semantic locators.
- Navigation, routes, dialogs, and overlays.
- Network requests and application loading states.
- Browser traces, screenshots, and console errors.

### React Native

- App build and launch requirements.
- iOS and Android differences.
- Accessibility labels and test identifiers.
- Navigation, native controls, and asynchronous UI state.
- Simulator or emulator execution and device logs.

### Native iOS

- Xcode and simulator/device setup.
- XCTest and XCUIAutomation when used by the project.
- Accessibility identifiers and native UI hierarchies.
- Screenshots, test reports, and relevant device logs.

### Native Android

- Emulator/device setup.
- The project's UI automation framework.
- Accessibility semantics and resource identifiers.
- Android application state, logs, and test artifacts.

These are possible approaches, not mandatory framework choices.

Do not force one framework onto every platform. Reuse test intent and
expected outcomes where possible, but implement interactions using each
platform's actual capabilities.

Do not assume a visual screenshot, DOM tree, accessibility hierarchy,
trace, or device log is available unless the environment provides it.
Use the best available source of evidence and clearly report missing evidence.

## 7. Execute and Verify

Run tests in a controlled sequence:

1. Confirm the required application, dependencies, and test environment
   are available.
2. Run the new or modified test.
3. Inspect failures and make justified corrections.
4. Rerun the affected test.
5. Run relevant regressions.
6. Run the broader suite when appropriate and feasible.

Use the project's existing scripts and commands.

Use framework-native condition-based waiting and retryable assertions.
Avoid arbitrary sleeps when the required application state can be observed.

If a required service, credential, simulator, emulator, or device is
unavailable, report the blocker rather than pretending the test ran.

Static inspection can help review a test, but it is not evidence that
the test passed.

## 8. Interaction Recovery and Human-in-the-Loop Handoff

### 8.1 Detect a blocked interaction

A blocked interaction occurs when the agent cannot make expected progress,
including when:

- Repeated scrolling does not reveal the target.
- A visible control cannot be clicked or tapped.
- An overlay, modal, keyboard, tooltip, or sticky element may obstruct
  the intended target.
- The expected navigation or state transition does not occur.
- The current screen or application state cannot be determined.
- A control appears disabled or unavailable unexpectedly.
- The same action produces the same failure without new evidence.
- The agent cannot determine a safe, valid next action.

Do not treat every delay or transient state as a permanent blocker.
Use the framework's normal waits for expected asynchronous behavior.
If the expected state does not appear within the applicable timeout,
inspect the actual state before considering recovery.

### 8.2 Stop when the retry budget is exhausted

The runtime or caller may already enforce interaction retry limits,
tool-call limits, or an overall execution budget.

Respect those limits. Do not reset them, circumvent them, or continue
trying the same interaction through a different tool merely to bypass
the limit.

When the applicable retry limit is reached, or no safe recovery is
available:

1. Stop interacting with the blocked UI.
2. Preserve the current failure evidence.
3. Record the last verified checkpoint and exact blocked step.
4. Prepare a human-readable blocker report.
5. Ask the user a focused question that would help resolve the blocker.
6. Pause the task and wait for guidance.

Do not continue autonomously while waiting for the user.

If the runtime cannot pause and resume a task, leave the blocker report
as the handoff and wait for the user's next instruction. Do not claim
that an automatic resume mechanism exists when it does not.

### 8.3 Capture evidence before changing state

Collect the best available evidence before dismissing overlays, navigating
away, restarting the app, refreshing the page, or resetting the device.

Record:

- Test or user journey name.
- Last successfully completed step.
- Exact action that became blocked.
- Expected screen, element, or state.
- Actual observed screen, element, or state.
- Screenshot or equivalent visual evidence, when supported.
- DOM snapshot, accessibility tree, element details, logs, or trace,
  when available and relevant.
- Recovery strategies already attempted and their outcomes.
- Most likely cause, explicitly labeled as a hypothesis.
- Any limitations that prevent better diagnosis.

Preserve exact error messages and useful element details when available.

Use artifact paths, links, or attachments that the user can actually
access. Do not invent artifact paths or claim that evidence exists if
it was not collected.

If the environment does not support screenshots or other diagnostics,
say so and provide the evidence that is available.

### 8.4 Recover using evidence, not blind repetition

Before reaching the retry limit, a recovery attempt should be informed
by the observed state.

When a UI interaction becomes blocked, use available MCP inspection
capabilities to gather fresh evidence before asking the user for help.
If an MCP provides a more reliable way to inspect or interact with the
blocked element, consider switching to it within the existing retry
and execution limits.

Examples include:

- Inspecting whether a modal is covering the target.
- Checking whether the target exists but is outside the correct
  scroll container.
- Inspecting the accessibility hierarchy or DOM to find the correct
  element.
- Determining whether a loading state or navigation transition is incomplete.
- Checking whether a control is disabled or not available in the current state.
- Inspecting logs or the latest failure details for a likely application defect.

Do not repeat identical clicks, scrolls, waits, or selector attempts
without new evidence or a materially different strategy.

Only perform recovery actions that are safe and consistent with the
intended journey. Do not dismiss a dialog, bypass an authentication step,
change permissions, or skip required user behavior without justification.

### 8.5 Required blocker report

When human help is needed, report the problem in this format:

**E2E test blocked — [test or journey name]**

**Progress:** [last verified checkpoint] → [blocked step]

**Goal:** [what the agent was trying to accomplish]

**Expected:** [expected element, screen, or application state]

**Observed:** [what actually happened]

**Evidence:**
- [Screenshot or artifact link, if available]
- [DOM/accessibility snapshot, logs, trace, or error, if available]

**Attempts:** [recovery strategies already tried and their outcomes]

**Likely cause:** [best hypothesis, clearly marked as unconfirmed when appropriate]

**Suggested recovery:** [most promising next step and why]

**Question:** [one specific question that helps the user provide the
missing information or authorize the next action]

Make the report actionable and concise. Do not dump large logs or
unfiltered snapshots into the user's message. Reference the relevant
artifacts and include only the details needed to make a decision.

Prefer a concrete question when possible, such as:

- "The modal appears to cover the button. Should I dismiss it and retry?"
- "I cannot find the expected item in the visible hierarchy. Can you
  identify the intended control or explain where it should appear?"
- "The app remains on the loading screen. Is this an expected environment
  dependency, or should I record this as a defect?"
- "The intended screen is unreachable through the current flow.
  Do you know the correct navigation path?"

If the cause is uncertain, say so. Do not present speculation as fact.

Ask only for information that is not already available in the evidence.
Do not ask the user to repeat the original request or details already
established by the task.

### 8.6 Resume after the user responds

After receiving guidance:

1. Interpret the response in the context of the blocked step and its evidence.
2. Apply the user's instruction only to the relevant blocker.
3. Reinspect the current application state before acting.
4. Resume from the last verified checkpoint instead of restarting the
   entire journey unnecessarily.
5. Preserve the original test objective and assertions unless the user
   explicitly authorizes a change.
6. Continue respecting the existing retry and execution limits.
7. Collect new evidence if the suggested recovery fails.

Do not assume the UI is unchanged while the task was paused. Always
verify the current state before resuming.

If the guidance does not resolve the problem, explain what happened.
Ask for further help only when new evidence or a materially different
question makes another intervention useful.

### 8.7 Preserve test integrity after intervention

Human assistance must not turn an incomplete journey into a false pass.

- Record meaningful manual interventions that change the application state.
- Do not silently skip the blocked step or required assertions.
- If the user manually performs an action that the test was supposed
  to automate, do not claim that action was automatically verified.
- If the recovery changes preconditions, re-establish or verify the
  required test state before continuing.
- If the evidence indicates a product defect, document it rather than
  concealing it with a workaround.
- Mark the journey blocked or partially verified if the required behavior
  could not be tested.

A clear handoff and an accurately reported incomplete test are preferable
to an endless interaction loop.

## 9. Diagnose Test Failures

For failures that are not already handled as blocked interactions:

1. Inspect the exact failing action or assertion.
2. Inspect the available logs, screenshots, traces, and application state.
3. Reproduce the failure when feasible.
4. Classify the likely cause:
   - Product defect.
   - Incorrect test expectation.
   - Unstable selector.
   - Synchronization or timing problem.
   - Incorrect test data or environment.
   - External dependency failure.
   - Platform/framework limitation.
   - Unresolved cause.
5. Apply the smallest justified correction.
6. Rerun the affected test and relevant regressions.

Do not weaken assertions, add arbitrary waits, increase timeouts, skip
tests, or add retries solely to obtain a passing result.

If a test must be skipped or its expectation changed, explain the reason
and the effect on coverage.

Do not silently modify production code when the requested task is only
to write or fix tests.

## 10. Review Before Finishing

Verify that:

- The test covers the intended user-visible behavior.
- Selectors and synchronization are reasonably stable.
- Setup and cleanup are safe.
- The test can run independently where appropriate.
- Secrets and real user data are not exposed.
- Existing project conventions are preserved.
- Assertions remain meaningful.
- Human intervention, if any, is documented.
- Actual test execution results are recorded.
- Blocked, skipped, and unexecuted tests are not represented as passing.

## 11. Final Report

Provide a concise report covering:

- User journeys and scenarios tested.
- Files created or changed.
- Framework, commands, and automation tools/MCPs used, including the selected execution method and any limitations.
- Tests actually executed and their results.
- Bugs discovered and whether they were resolved.
- Tests that were blocked, skipped, or not run, with reasons.
- Diagnostic evidence when relevant.
- Remaining coverage gaps or limitations.

Use explicit statuses such as:

- **Passed:** Executed successfully.
- **Failed:** Executed and an assertion or behavior failed.
- **Blocked:** Could not proceed because of an unresolved obstacle.
- **Not run:** Execution did not occur.
- **Skipped:** Deliberately excluded, with a reason.

Never claim a suite passed based only on code inspection or partial execution.

## 12. Scope Boundaries

This skill owns the shared E2E planning, implementation, execution,
recovery, and reporting workflow.

It does not automatically:

- Replace unit, integration, API, or accessibility testing.
- Introduce a new test framework without justification.
- Require all platforms to use the same automation framework.
- Modify production architecture to simplify test implementation.
- Bypass authentication, security controls, or destructive-operation safeguards.
- Continue interacting indefinitely after a retry or execution limit.
- Claim the test passed when required behavior remains unverified.

The key outcome is reliable user-journey coverage, actionable failure
evidence, and a clear human handoff whenever autonomous execution cannot
safely continue.
