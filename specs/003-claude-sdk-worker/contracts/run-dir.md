# Contract: run directory JSON (parent monitoring)

Layout: `.agent/claude/<job-name>/<run-id>/` plus `latest.json` beside the job folder.

Match Pi public keys (`schemaVersion` 2) so the parent poll loop is unchanged.

## `status.json` (poll)

Do not put assistant body in `status.json`.

| Key | Notes |
|-----|--------|
| `schemaVersion` | `2` |
| `jobName`, `runId`, `runDir` | as Pi |
| `backend` | `claude-cli` |
| `print` | whether wrapper `--print` was set |
| `lifecycle` | process layer |
| `processAlive`, `pid` | wrapper tracks child pid for kill |
| `lastEventType`, `lastEventAt` | last persisted event type (`result`, `assistant`, `system`, or synthetic `agent_start`) |
| `current` | `{kind, name?, startedAt}` — `tool` when a tool_use is in flight, else model/writing |
| `lastError`, `sessionId` | `sessionId` from stream `session_id` when present |
| `exitCode`, `signal`, `timedOut`, `timeoutMs` | process outcome |
| `watcherUpdatedAt`, `currentAgeMs`, `quietMs` | heartbeat ~2s |
| `recent`, `parseErrors` | optional, same as Pi |

## `report.json` (after exit)

| Key | Notes |
|-----|--------|
| `schemaVersion` | `2` |
| `backend` | `claude-cli` |
| `lifecycle`, `exitCode`, `signal`, `timedOut`, `timeoutMs` | process layer |
| `summary` / `summaryExtracted` | assistant text used for STATUS parse |
| `workerStatus` | `ok\|stuck\|blocked\|null` |
| `reportValid` | true iff STATUS token found |
| `errorMessage`, `stderrTail` | spawn/timeout/missing STATUS |

## `events.jsonl`

One raw CLI stdout line per row on stream-json jobs. Official objects use `type` (`system`, `assistant`, `result`, `stream_event`, …), not Pi event names and not Antigravity `event`. Parent must not parse this file. Wrapper may parse it only to (1) heartbeat `current` and (2) reconstruct assistant text for `report.json`.

## Stream-json STATUS reconstruction

1. Walk lines; JSON-parse; ignore malformed (count/log, do not crash).
2. If any object has `type == "result"` and a string at `result` (or nested `result.result`), use the last one (trimmed).
3. Else join `type == "assistant"` `content[].text` (skip subagent lines with non-null `parent_tool_use_id` unless no main-thread text exists).
4. Else join `stream_event` `text_delta` fields if present.
5. Run existing `WORKER_STATUS_RE` on that text.

## Process vs STATUS (parent rule, unchanged)

`lifecycle=completed` / wrapper exit 0 is **not** job success. Parent reads `reportValid` and `workerStatus`. Non-zero child exit is `failed` even if summary contains `STATUS: ok`.
