# Contract: run directory JSON (parent monitoring)

Layout: `.agent/antigravity/<job-name>/<run-id>/` plus `latest.json` beside the job folder.

## `status.json` (poll)

Keep today’s public keys. `backend` value changes to `agy-cli`.

| Key | Notes |
|-----|--------|
| `schemaVersion` | `1` |
| `jobName`, `runId`, `runDir` | as today |
| `backend` | `agy-cli` |
| `lifecycle` | process layer |
| `processAlive`, `pid` | wrapper process; `pid` of wrapper, child tracked internally for kill |
| `lastEventType`, `lastEventAt` | last persisted event type (`init` / `step_update` / `result` or synthetic `agent_start`) |
| `current` | `{kind, name?, startedAt}` — `tool` when `step_type=tool`, else model/writing |
| `lastError`, `sessionId` | `sessionId` from stream `conversation_id` when present |
| `exitCode`, `signal`, `timedOut`, `timeoutMs` | process outcome |
| `watcherUpdatedAt`, `currentAgeMs`, `quietMs` | heartbeat |

Do not put assistant body in `status.json`.

## `report.json` (after exit)

| Key | Notes |
|-----|--------|
| `schemaVersion` | `1` |
| `backend` | `agy-cli` |
| `lifecycle`, `exitCode`, `signal`, `timedOut`, `timeoutMs` | process layer |
| `summary` / `summaryExtracted` | assistant text used for STATUS parse |
| `workerStatus` | `ok\|stuck\|blocked\|null` |
| `reportValid` | true iff STATUS token found |
| `errorMessage`, `stderrTail` | spawn/timeout/missing STATUS |

## `events.jsonl`

One raw CLI stdout line per row on stream-json jobs. Official objects use `event` (`init`, `step_update`, `result`), not Pi `type`. Parent must not parse this file. Wrapper may parse it only to (1) heartbeat `current` and (2) reconstruct assistant text for `report.json`.

## Stream-json STATUS reconstruction

1. Walk lines; JSON-parse; ignore malformed (count/log, do not crash the wrapper).
2. If any `event=="result"` with string `result.response`, use the last one (trimmed).
3. Else join `step_update.text_delta` where `step_type=="agent_response"`.
4. Run existing `WORKER_STATUS_RE` on that text.

## Process vs STATUS (parent rule, unchanged)

`lifecycle=completed` / wrapper exit 0 is **not** job success. Parent reads `reportValid` and `workerStatus`.
