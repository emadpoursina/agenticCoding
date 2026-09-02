# Contract: Telegram Messaging (in-process)

**Feature**: `008-telegram` | **Packages**: `hermes_kanban.orchestrator`, `hermes_kanban.messaging`

Extends [007 GitHub publish](../../007-github-integration/contracts/github-publish.md). Same three public operations. Restart persistence, a background worker, merge, a second bot, and native `kanban.db` notify-sub writes remain out of contract.

Types: [data-model.md](../data-model.md). Reuse overlay, GitHost, executor, registry, board. **Surgical orchestrator change**: emit closed-set events at existing transitions; inject `MessagingChannel` like `git_host`.

## Construction

```python
class MessagingChannel(Protocol):
    def deliver(self, kind: str, payload: Mapping[str, object], *, occurrence: str) -> SendRecord: ...
    def reply(self, text: str) -> None: ...

class PivOrchestrator:
    def __init__(
        self,
        executor: AgentExecutor,
        workspaces: WorkspaceManager,
        registry: ProjectRegistry,
        task_board: TaskBoard,
        git_host: GitHost | None = None,
        messaging: MessagingChannel | None = None,
    ) -> None: ...
```

Checks MUST inject `MemoryMessagingChannel`. Omitted or disabled messaging → skip-send; wait-returns unchanged. MUST NOT invent a bot token or a second chat.

`from_config` may pass a live wrapper only when `notifications.telegram.enabled` is true **and** a home chat id exists; otherwise skip channel.

## Wait / slot

Unchanged from 007: wait until `PR_CREATED`, `FAILED`, `HUMAN_DECISION_REQUIRED`, or `BLOCKED`. No background worker. Chat status MUST NOT occupy or release the slot. Chat MUST NOT start a second workflow while the slot is occupied.

Send failure MUST NOT change `state`, MUST NOT close or rewrite a pull request, MUST NOT convert `PR_CREATED` into `FAILED`.

## Outbound events

Orchestrator MUST call `deliver` at most once per occurrence key (research.md §4). Payload MUST include project and task for `task_start`; decision protocol fields for `human_decision`; escalation A/B for `blocked`; PR number + HTML URL for `pr_created`; MUST NOT include secrets.

`MemoryMessagingChannel` records each attempt. Tests MAY set the channel to fail N times then succeed, or fail all three.

Disabled / no target: `SendRecord.status=SKIPPED`, 0 messages in the memory log, wait-return still `PR_CREATED` (or the same park/block/fail as 007).

Enabled + target + transport error: retry the **same** occurrence up to 3 attempts total, then `FAILED` send record; execution state unchanged.

## Inbound

```python
def parse_option_letter(text: str) -> str | None: ...
def handle_inbound(
    orchestrator: PivOrchestrator,
    chat_id: str,
    text: str,
    channel: MessagingChannel,
    *,
    home_chat_id: str,
) -> InboundResult: ...
```

`chat_id != home_chat_id` → `ignored` (0 replies, 0 `resume_workflow`).

Home chat:

| Text | Behavior |
|---|---|
| `/status` | Overlay snapshot; 0 workflow starts |
| `/status <project>` | Scoped; unknown → visible error |
| `/projects` `/tasks` `/blockers` `/prs` | Overlay/registry/board as data-model |
| Valid listed letter while parked/blocked | `resume_workflow`; same wait-returns as 007 |
| Valid letter while not parked/blocked | Reply nothing is waiting; 0 starts |
| Invalid letter while parked/blocked | Stay; correction with listed letters |
| Other text | `ignored` (live pass-through; tests: not delivered as an event) |

Natural-language status phrases are **out of contract** (gateway does not treat free-text as commands).

## Simulated channel

Checks MUST pass with `MemoryMessagingChannel` and **no** live Telegram account. A live proof MAY use the already-connected chat; MUST NOT create a second bot or silently pick a production repository.

## Non-goals in this contract

Forking Hermes `adapter.py` / `commands.py`. Writing `kanban_notify_subs`. Merge. Methodology writes. Phase 7 restart resume from chat.
