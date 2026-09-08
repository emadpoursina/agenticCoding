# Contract: Generic Harness Execution

**Feature**: `013-harness-adapter-pi`

Hermes owns task selection, worktrees, human decisions, validation, Git
safety, and GitHub publication. The selected harness owns the agent loop and
the Spec Kit playbook. This contract deliberately exposes one start/result
boundary and no framework lifecycle API.

## Configuration and adapter selection

The live configuration selects exactly one harness and one supported playbook:

```yaml
harness:
  adapters:
    - id: pi
      active: true
      runtime_path_env: HERMES_PI_RUNTIME
  playbook: speckit-orchestrate
  model_profile: default
```

The loader MUST:

1. require exactly one active adapter;
2. reject an unsupported adapter, empty identity, or missing runtime setting;
3. accept only `speckit-orchestrate` as the V1 playbook;
4. resolve the adapter runtime through the configured environment variable or
   injected fixture port;
5. verify the runtime's provider/version/revision marker before starting a
   model or harness run;
6. keep model profile values as named references, not provider names, client
   objects, or Cursor model slugs;
7. fail before workspace execution when configuration or runtime validation
   fails.

Pi-specific model mapping belongs in the Pi runtime configuration, outside the
generic request/result records. Credentials remain in the environment or the
operator's existing secret store.

## Provider-neutral Python surface

The generic surface lives in
`personalAgent/src/hermes_kanban/external_framework.py`, reused as the
provider-neutral boundary. It MUST expose equivalent typed records:

```python
class HarnessAdapter(Protocol):
    identity: str

    def start(self, request: HarnessStartRequest) -> HarnessResult: ...


@dataclass(frozen=True)
class HarnessStartRequest:
    project_id: str
    task_id: str
    task_context: TaskContext
    repository_context: RepositoryContext
    workspace_path: Path
    workspace_branch: str
    playbook_id: str
    model_profile: str
    timeout_seconds: float
    safety_limits: SafetyLimits
    operator_flags: tuple[str, ...] = ()
    resume_context: ResumeContext | None = None


@dataclass(frozen=True)
class HarnessResult:
    status: Literal["completed", "failed", "needs_human", "stuck"]
    reason: str
    next_action: str
    artifacts: tuple[HarnessArtifact, ...] = ()
    changes: tuple[str, ...] = ()
    output_reference: str | None = None
    retryable: bool = False
    questions: tuple[str, ...] = ()
    resume_context: ResumeContext | None = None
    harness_id: str = ""
```

`HarnessStartRequest` MUST NOT contain a stage list, stage name, Pi SDK type,
Pi client, Cursor model slug, private reasoning, token, transcript, or secret.
`HarnessResult` MUST be safe to serialize and must contain only relative
worktree paths for artifacts, changes, and output references.

Hermes MUST reject any direct request that attempts to name or invoke a
Spec Kit stage. There is no `execute_framework`, `execute_step`, plan,
tasks, implement, analyze, converge, or `PLANNING_COMPLETE` lifecycle call in
the live API.

## Request validation

Before calling `HarnessAdapter.start`, Hermes MUST validate:

- task/project identity and complete required task context;
- prepared worktree equality with the expected project/task location;
- feature branch identity and protected/default branch exclusion;
- repository/default-branch context;
- `playbook_id == "speckit-orchestrate"`;
- non-empty named model profile;
- finite positive timeout;
- safety limits that force worktree-only writes, no publication, and no
  protected/default-branch writes;
- bounded, secret-free operator flags and resume/diagnostic context.

The adapter MUST repeat the safety checks at its own boundary. A missing
timeout is rejected before the Pi runtime starts. An expired timeout returns
`failed`, never `completed`, and is counted as one whole-run attempt.

## Result validation

Before Hermes stores or acts on a result, it MUST validate:

- the status is one of the four closed values;
- `reason`, `next_action`, questions, diagnostics, and output references are
  bounded strings without secrets or private reasoning;
- `needs_human` includes at least one safe question and a resumable next
  action;
- failed/stuck results do not claim fabricated successful artifacts;
- every artifact/change/output path is relative, normalizes below the current
  worktree, is not a symlink, and is readable when it claims an existing
  native artifact;
- no result path names `AiNative`, the enrolled project root, Hermes control
  state, a sibling worktree, or a protected branch;
- no provider name, SDK object, Cursor model slug, token, or credential leaks
  into generic metadata.

Malformed, unknown, unsafe, or secret-bearing output becomes visible
`failed` state and cannot start validation or publication.

## Pi adapter contract

The Pi implementation is the only provider-specific adapter delivered in V1.
It may define private types such as `PiSdkPort`, `PiRunRequest`, and
`PiRunResponse`, but those types MUST stay inside the Pi adapter module.

`PiHarnessAdapter.start` MUST:

1. map the generic request to one Pi SDK run;
2. map the named model profile through Pi-owned configuration;
3. enforce the worktree-only/no-publish safety policy and deadline;
4. invoke the Pi Spec Kit playbook as one internal loop;
5. let the playbook run specify, clarify/return, one continue gate, plan,
   tasks, conditional analyze, and implement/converge internally;
6. stop and map human questions to `needs_human` without contacting the
   operator;
7. map timeout, unavailable runtime, SDK failure, malformed output, or
   forbidden operations to `failed`;
8. map an unrecoverable or retryable internal stuck point to `stuck`;
9. return native `spec.md`, `plan.md`, `tasks.md`, and related worktree files
   as safe relative artifacts when present;
10. never push, merge, create/update a PR, deploy, approve as a human, write
    AiNative, or write outside the current task worktree.

The Pi adapter MUST not implement a Hermes retry loop. Hermes starts another
whole run when the normalized result allows it.

## Human parking and resume

When Pi returns `needs_human`, Hermes:

1. stores the questions and safe resume context on the existing workflow
   record;
2. records a decision brief through the existing messaging channel;
3. prevents validation, publication, and later playbook work while parked;
4. passes the selected answer back in a new generic start request.

When `skip` is active for specify/clarify:

1. Hermes records the documented assumptions and choice report;
2. Hermes asks for exactly one continuation confirmation;
3. the confirmation and assumptions are passed as `ResumeContext`;
4. Pi resumes its own playbook and proceeds to plan;
5. skip does not bypass plan, tasks, analyze, implement, or converge.

Pi has no operator chat channel. A second question batch is another
`needs_human` result handled through the same record/resume boundary.

## Hermes orchestration sequence

For a new eligible task:

```text
select task
  -> prepare isolated worktree
  -> start one generic harness request
  -> receive one normalized result
  -> needs_human / stuck / failed
       -> park, bounded whole-run retry, or visible failure
  -> completed
       -> existing project validation
       -> existing feature-branch commit/push/create-or-update PR
```

The orchestrator MUST not call `scout -> plan -> tasks -> PLANNING_COMPLETE ->
implement`. It MUST not use an AiNative planner/builder fallback when Pi is
missing or fails. Validation recovery that needs workspace changes starts
another generic harness request with safe validation/diagnostic context.

Whole-run retry rules:

- a timeout/failure consumes one attempt;
- recoverable `stuck` results may be retried up to three attempts at the same
  stuck point;
- after the third failed attempt Hermes parks the task for a human;
- no fourth automatic harness attempt starts;
- validation's existing recovery budget remains separate and still controls
  validation-fix attempts.

## Legacy records and removed entry points

At startup/reclaim, a record from the old Hermes stage path or historical
`PLANNING_COMPLETE` state MUST be parked with a clear migration reason. Hermes
must not finish it on the old machine, rewrite its history, or auto-start Pi.

Any compatibility method for a removed direct-stage request MUST fail before a
provider call with an unsupported-operation error. No command, fallback, or
recovery path may sequence the removed stages.

## Validation and publication

`completed` is playbook completion only. Hermes MUST:

1. validate the current task worktree through the existing project checks;
2. keep GitHub unreachable for failed, human, stuck, and pre-validation
   results;
3. on a validation pass, reuse the existing history-safe commit,
   feature-branch push, create-or-update pull request, number/URL validation,
   and `pr_created` notice;
4. keep merge, deployment, protected/default-branch writes, and human
   approval unavailable to the harness.

## Error mapping

| Condition | Required behavior |
|---|---|
| Zero/multiple active adapters | Configuration error before harness/model work |
| Unsupported adapter or playbook | Visible failure before adapter start |
| Missing/mismatched Pi runtime | `failed`; no fallback stage machine |
| Missing timeout | Request rejection before runtime start |
| Timeout | `failed`; count one whole-run attempt |
| Invalid worktree/branch/secret | Request rejection before start |
| SDK/runtime cannot start | `failed`; retain inspectable files if any |
| Pi question | `needs_human`; park and wait for Hermes resume |
| Unknown/malformed status or unsafe path | `failed`; no validation/publish |
| Recoverable stuck point | `stuck`; Hermes may start another whole run |
| Third same-point stuck failure | Park for human; no fourth attempt |
| `completed` | Existing Hermes validation only |
| Validation pass | Existing Hermes GitHub publication only |
