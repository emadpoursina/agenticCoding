#!/usr/bin/env node
/**
 * Cursor-facing Pi worker launcher.
 *
 * Pi JSON stays on disk (events.jsonl). Cursor polls status.json.
 * Verified against Pi 1.2.0 CLI. Event shapes (json mode):
 *   Top-level: session, agent_start, agent_end, agent_settled, turn_start,
 *   turn_end, message_start, message_update, message_end,
 *   tool_execution_start|update|end, plus session extras (compaction_*,
 *   auto_retry_*, …).
 *   message_update nests assistantMessageEvent (text_*, thinking_*,
 *   toolcall_start|delta|end, done, error). toolcall_* is the model emitting
 *   a call, not the tool running. Execution is tool_execution_*.
 *   Final text: assistant message_end / last assistant in agent_end.messages,
 *   content[].type === "text".
 */
import { spawn } from "node:child_process";
import {
  mkdirSync,
  writeFileSync,
  appendFileSync,
  renameSync,
  existsSync,
} from "node:fs";
import { join, dirname } from "node:path";
import { fileURLToPath } from "node:url";
import { randomBytes } from "node:crypto";

const SCHEMA_VERSION = 2;
const SKILL_DIR = dirname(fileURLToPath(import.meta.url));
const WORKER_CONTRACT = join(SKILL_DIR, "worker-contract.md");
const HEARTBEAT_MS = 2000;
const STATUS_THROTTLE_MS = 250;
const ERROR_MAX = 240;
const SUMMARY_MAX = 100_000;
const STDERR_TAIL_MAX = 2000;
const RECENT_MAX = 5;
const GRACEFUL_KILL_MS = 2000;
const WORKER_STATUS_RE = /\bSTATUS\s*[:=]?\s*(ok|stuck|blocked)\b/i;

const IMPORTANT = new Set([
  "session",
  "agent_start",
  "agent_end",
  "agent_settled",
  "message_end",
  "tool_execution_start",
  "tool_execution_end",
  "compaction_start",
  "compaction_end",
  "auto_retry_start",
  "auto_retry_end",
]);

function nowIso() {
  return new Date().toISOString();
}

function clip(s, n) {
  if (s == null) return null;
  const t = String(s);
  return t.length <= n ? t : `${t.slice(0, n)}…`;
}

function sanitizeName(name) {
  const s = String(name).trim();
  if (!s || /[\\/]/.test(s) || s === "." || s === "..") {
    throw new Error(`invalid --name: ${name}`);
  }
  if (!/^[\w.-]+$/.test(s)) {
    throw new Error(`--name must be letters, digits, _ . - (got ${name})`);
  }
  return s;
}

function makeRunId() {
  const t = new Date().toISOString().replace(/[:.]/g, "-");
  return `${t}_${randomBytes(3).toString("hex")}`;
}

function pidAlive(pid) {
  if (!pid) return false;
  try {
    process.kill(pid, 0);
    return true;
  } catch {
    return false;
  }
}

function assistantText(msg) {
  if (!msg || msg.role !== "assistant" || !Array.isArray(msg.content)) return "";
  return msg.content
    .filter((c) => c && c.type === "text" && typeof c.text === "string")
    .map((c) => c.text)
    .join("\n")
    .trim();
}

function writeAtomic(path, obj) {
  const tmp = `${path}.${process.pid}.tmp`;
  writeFileSync(tmp, `${JSON.stringify(obj, null, 2)}\n`);
  renameSync(tmp, path);
}

/** Parse --timeout as seconds (plain number) or ms with trailing "ms". */
function parseTimeoutMs(raw) {
  if (raw == null || raw === "") return null;
  const s = String(raw).trim();
  const msMatch = /^(\d+(?:\.\d+)?)\s*ms$/i.exec(s);
  if (msMatch) {
    const n = Number(msMatch[1]);
    if (!Number.isFinite(n) || n <= 0) throw new Error(`invalid --timeout: ${raw}`);
    return Math.floor(n);
  }
  const sec = Number(s);
  if (!Number.isFinite(sec) || sec <= 0) throw new Error(`invalid --timeout: ${raw}`);
  return Math.floor(sec * 1000);
}

function parseWorkerStatus(text) {
  if (!text || typeof text !== "string") return null;
  const m = WORKER_STATUS_RE.exec(text);
  return m ? m[1].toLowerCase() : null;
}

function takeValue(args, i, flag) {
  const next = args[i + 1];
  if (next == null || next.startsWith("--")) {
    throw new Error(`${flag} requires a value`);
  }
  return args[i + 1];
}

function parseArgs(argv) {
  const out = {
    name: null,
    cwd: process.cwd(),
    print: false,
    runId: null,
    selfTest: false,
    timeoutMs: null,
    provider: null,
    model: null,
    thinking: null,
    piArgs: [],
  };
  const args = argv.slice(2);
  for (let i = 0; i < args.length; i++) {
    const a = args[i];
    if (a === "--") {
      out.piArgs.push(...args.slice(i + 1));
      break;
    }
    if (a === "--self-test") out.selfTest = true;
    else if (a === "--print" || a === "-p") out.print = true;
    else if (a === "--name") out.name = takeValue(args, i++, "--name");
    else if (a === "--cwd") out.cwd = takeValue(args, i++, "--cwd");
    else if (a === "--run-id") out.runId = takeValue(args, i++, "--run-id");
    else if (a === "--timeout") out.timeoutMs = parseTimeoutMs(takeValue(args, i++, "--timeout"));
    else if (a === "--provider") out.provider = takeValue(args, i++, "--provider");
    else if (a === "--model") out.model = takeValue(args, i++, "--model");
    else if (a === "--thinking") out.thinking = takeValue(args, i++, "--thinking");
    else if (a.startsWith("--name=")) out.name = a.slice(7);
    else if (a.startsWith("--cwd=")) out.cwd = a.slice(6);
    else if (a.startsWith("--run-id=")) out.runId = a.slice(9);
    else if (a.startsWith("--timeout=")) out.timeoutMs = parseTimeoutMs(a.slice(10));
    else if (a.startsWith("--provider=")) out.provider = a.slice(11);
    else if (a.startsWith("--model=")) out.model = a.slice(8);
    else if (a.startsWith("--thinking=")) out.thinking = a.slice(11);
    else out.piArgs.push(a);
  }
  return out;
}

/** True if argv already contains --model / --model=. */
function argvHasModel(argv) {
  for (let i = 0; i < argv.length; i++) {
    const a = argv[i];
    if (a === "--model") {
      const v = argv[i + 1];
      return Boolean(v && !v.startsWith("--"));
    }
    if (a.startsWith("--model=") && a.length > 8) return true;
  }
  return false;
}

/**
 * Parent must supply --model (wrapper flag or after --).
 * --provider and --thinking are optional (Pi accepts provider/id in --model).
 * No harness default model.
 */
function requireModel(opts) {
  if (opts.model && String(opts.model).trim()) return;
  if (argvHasModel(opts.piArgs)) return;
  throw new Error(
    "blocked: --model is required (pass --model <id> before or after --; no harness default)",
  );
}

function buildPiArgs({ print, provider, model, thinking, piArgs }) {
  const prefix = [];
  if (print) prefix.push("-p");
  else prefix.push("--mode", "json");
  if (provider) prefix.push("--provider", provider);
  if (model) prefix.push("--model", model);
  if (thinking) prefix.push("--thinking", thinking);
  prefix.push("--append-system-prompt", WORKER_CONTRACT);
  return [...prefix, ...piArgs];
}

function emptyState(meta) {
  return {
    schemaVersion: SCHEMA_VERSION,
    jobName: meta.jobName,
    runId: meta.runId,
    runDir: meta.runDir,
    print: meta.print,
    lifecycle: "starting",
    processAlive: false,
    pid: null,
    lastEventType: null,
    lastEventAt: null,
    watcherUpdatedAt: nowIso(),
    current: null,
    currentAgeMs: null,
    quietMs: null,
    recent: [],
    parseErrors: 0,
    lastError: null,
    sessionId: null,
    exitCode: null,
    signal: null,
    timedOut: false,
    timeoutMs: meta.timeoutMs ?? null,
  };
}

function enrich(state) {
  const t = Date.now();
  state.watcherUpdatedAt = nowIso();
  state.currentAgeMs =
    state.current && state.current.startedAt
      ? t - Date.parse(state.current.startedAt)
      : null;
  state.quietMs = state.lastEventAt ? t - Date.parse(state.lastEventAt) : null;
  if (state.pid && state.lifecycle === "running") {
    state.processAlive = pidAlive(state.pid);
  }
  return state;
}

function setCurrent(state, current) {
  state.current = current
    ? { ...current, startedAt: current.startedAt || nowIso() }
    : null;
}

function noteError(state, msg) {
  state.lastError = clip(msg, ERROR_MAX);
}

function applyEvent(state, ev) {
  if (!ev || typeof ev !== "object" || typeof ev.type !== "string") {
    state.parseErrors += 1;
    noteError(state, "event missing type");
    return "throttle";
  }
  state.lastEventType = ev.type;
  state.lastEventAt = nowIso();

  if (ev.type === "session" && typeof ev.id === "string") {
    state.sessionId = ev.id;
    if (state.lifecycle === "starting") state.lifecycle = "running";
    return "flush";
  }

  if (ev.type === "agent_start") {
    if (state.lifecycle === "starting") state.lifecycle = "running";
    if (!state.current) setCurrent(state, { kind: "model" });
    return "flush";
  }

  if (ev.type === "tool_execution_start") {
    const name = typeof ev.toolName === "string" ? ev.toolName : "unknown";
    const id = typeof ev.toolCallId === "string" ? ev.toolCallId : null;
    setCurrent(state, { kind: "tool", name, id });
    return "flush";
  }

  if (ev.type === "tool_execution_end") {
    const name = typeof ev.toolName === "string" ? ev.toolName : "unknown";
    const id = typeof ev.toolCallId === "string" ? ev.toolCallId : null;
    const started = state.current?.id && state.current.id === id
      ? Date.parse(state.current.startedAt)
      : null;
    const durationMs = started ? Date.now() - started : null;
    const outcome = ev.isError === true ? "error" : "ok";
    state.recent.push({
      kind: "tool",
      name,
      id,
      outcome,
      durationMs,
      endedAt: nowIso(),
    });
    if (state.recent.length > RECENT_MAX) state.recent.shift();
    if (outcome === "error") {
      noteError(state, `tool ${name} failed`);
    }
    if (!state.current || state.current.kind !== "tool" || !id || state.current.id === id) {
      setCurrent(state, { kind: "model" });
    }
    return "flush";
  }

  if (ev.type === "message_update") {
    const inner = ev.assistantMessageEvent;
    if (inner && typeof inner === "object" && typeof inner.type === "string") {
      state.lastEventType = `message_update.${inner.type}`;
      if (state.current?.kind === "tool") return "throttle";
      if (inner.type === "toolcall_start" && typeof inner.toolName === "string") {
        setCurrent(state, { kind: "emitting_tool_call", name: inner.toolName });
      } else if (inner.type.startsWith("thinking_")) {
        setCurrent(state, { kind: "thinking" });
      } else if (inner.type.startsWith("text_")) {
        setCurrent(state, { kind: "writing" });
      } else if (inner.type === "error") {
        const reason = inner.reason || "error";
        noteError(state, `model ${reason}`);
      }
    }
    return "throttle";
  }

  if (ev.type === "message_end") {
    const msg = ev.message;
    if (msg && msg.role === "assistant") {
      state._lastAssistant = {
        text: assistantText(msg),
        stopReason: typeof msg.stopReason === "string" ? msg.stopReason : null,
        errorMessage: typeof msg.errorMessage === "string" ? msg.errorMessage : null,
      };
      if (msg.stopReason === "error" || msg.stopReason === "aborted") {
        noteError(state, msg.errorMessage || msg.stopReason);
      }
      if (msg.stopReason === "toolUse") {
        setCurrent(state, { kind: "model" });
      } else if (msg.stopReason === "stop" || msg.stopReason === "length") {
        setCurrent(state, { kind: "writing" });
      }
    }
    return "flush";
  }

  if (ev.type === "agent_end") {
    if (Array.isArray(ev.messages)) {
      for (let i = ev.messages.length - 1; i >= 0; i--) {
        const msg = ev.messages[i];
        if (msg && msg.role === "assistant") {
          const text = assistantText(msg);
          const stopReason = typeof msg.stopReason === "string" ? msg.stopReason : null;
          if (text || stopReason === "error" || stopReason === "aborted") {
            state._lastAssistant = {
              text,
              stopReason,
              errorMessage: typeof msg.errorMessage === "string" ? msg.errorMessage : null,
            };
            break;
          }
        }
      }
    }
    setCurrent(state, null);
    return "flush";
  }

  if (ev.type === "compaction_start") {
    setCurrent(state, { kind: "compaction" });
    return "flush";
  }
  if (ev.type === "auto_retry_start") {
    setCurrent(state, { kind: "retry" });
    if (typeof ev.errorMessage === "string") noteError(state, ev.errorMessage);
    return "flush";
  }
  if (ev.type === "compaction_end" || ev.type === "auto_retry_end") {
    setCurrent(state, { kind: "model" });
    return "flush";
  }

  return IMPORTANT.has(ev.type) ? "flush" : "throttle";
}

function publicStatus(state) {
  const { _lastAssistant, ...rest } = enrich({ ...state });
  return rest;
}

/**
 * lifecycle = process outcome (wrapper-verified).
 * workerStatus = claim parsed from assistant text (ok|stuck|blocked|null).
 * reportValid = true only when a worker STATUS token was found.
 * Do not treat exit 0 alone as a valid worker result.
 */
function buildReport(state, extra) {
  const a = state._lastAssistant;
  let summary = extra.stdoutText ?? a?.text ?? null;
  if (typeof summary === "string") summary = summary.trim() || null;
  const extracted = Boolean(summary);
  const workerStatus = parseWorkerStatus(summary);
  const reportValid = workerStatus != null;
  let errorMessage =
    a?.errorMessage || extra.spawnError || state.lastError || null;
  if (state.timedOut && !errorMessage) errorMessage = "timeout";
  if (!reportValid && state.lifecycle === "completed") {
    const missing = "missing worker STATUS (ok|stuck|blocked)";
    errorMessage = errorMessage ? `${errorMessage}; ${missing}` : missing;
  }
  return {
    schemaVersion: SCHEMA_VERSION,
    jobName: state.jobName,
    runId: state.runId,
    runDir: state.runDir,
    lifecycle: state.lifecycle,
    exitCode: state.exitCode,
    signal: state.signal,
    timedOut: Boolean(state.timedOut),
    timeoutMs: state.timeoutMs ?? null,
    summaryExtracted: extracted,
    summary: extracted ? clip(summary, SUMMARY_MAX) : null,
    workerStatus,
    reportValid,
    stopReason: a?.stopReason ?? null,
    errorMessage: clip(errorMessage, ERROR_MAX),
    stderrTail: extra.stderrTail ? clip(extra.stderrTail, STDERR_TAIL_MAX) : null,
  };
}

function attachLineParser(stream, onLine) {
  let buf = "";
  stream.setEncoding("utf8");
  stream.on("data", (chunk) => {
    buf += chunk;
    for (;;) {
      const i = buf.indexOf("\n");
      if (i < 0) break;
      onLine(buf.slice(0, i));
      buf = buf.slice(i + 1);
    }
  });
  stream.on("end", () => {
    if (buf.length) onLine(buf);
    buf = "";
  });
}

async function runJob(opts) {
  const jobName = sanitizeName(opts.name);
  const runId = opts.runId || makeRunId();
  const cwd = opts.cwd;
  const runDir = join(cwd, ".agent", "pi", jobName, runId);
  mkdirSync(runDir, { recursive: true });

  const paths = {
    status: join(runDir, "status.json"),
    report: join(runDir, "report.json"),
    events: join(runDir, "events.jsonl"),
    stderr: join(runDir, "stderr.log"),
    latest: join(cwd, ".agent", "pi", jobName, "latest.json"),
  };
  writeFileSync(paths.events, "");
  writeFileSync(paths.stderr, "");
  writeAtomic(paths.latest, { jobName, runId, runDir, status: paths.status });

  const state = emptyState({
    jobName,
    runId,
    runDir,
    print: opts.print,
    timeoutMs: opts.timeoutMs,
  });
  const writeStatus = () => {
    try {
      writeAtomic(paths.status, publicStatus(state));
    } catch (err) {
      noteError(state, `status write failed: ${err.message}`);
    }
  };
  writeStatus();

  process.stdout.write(`RUN_DIR=${runDir}\nSTATUS_FILE=${paths.status}\n`);

  const piBin = process.env.PI_SPAWN_PI || "pi";
  const piArgs = opts.piArgv || buildPiArgs(opts);
  let lastFlush = 0;
  let pendingThrottle = false;
  let stdoutText = "";
  let stderrTail = "";
  let spawnError = null;
  let timeoutTimer = null;

  const flushIfDue = (mode) => {
    const t = Date.now();
    if (mode === "flush" || t - lastFlush >= STATUS_THROTTLE_MS) {
      lastFlush = t;
      pendingThrottle = false;
      writeStatus();
    } else {
      pendingThrottle = true;
    }
  };

  const handleJsonLine = (line) => {
    if (!line.trim()) return;
    appendFileSync(paths.events, `${line}\n`);
    let ev;
    try {
      ev = JSON.parse(line);
    } catch (err) {
      state.parseErrors += 1;
      noteError(state, `malformed json: ${err.message}`);
      flushIfDue("flush");
      return;
    }
    const mode = applyEvent(state, ev);
    flushIfDue(mode);
  };

  let child;
  try {
    child = spawn(piBin, piArgs, {
      cwd,
      env: process.env,
      stdio: ["ignore", "pipe", "pipe"],
    });
  } catch (err) {
    spawnError = err.message;
    state.lifecycle = "failed";
    state.processAlive = false;
    noteError(state, spawnError);
    writeStatus();
    writeAtomic(paths.report, buildReport(state, { spawnError, stderrTail }));
    process.stdout.write(`LIFECYCLE=failed\n`);
    return 1;
  }

  state.pid = child.pid ?? null;
  state.processAlive = true;
  state.lifecycle = "running";
  writeStatus();

  if (opts.print) {
    child.stdout.setEncoding("utf8");
    child.stdout.on("data", (chunk) => {
      stdoutText += chunk;
    });
  } else {
    attachLineParser(child.stdout, handleJsonLine);
  }

  child.stderr.setEncoding("utf8");
  child.stderr.on("data", (chunk) => {
    appendFileSync(paths.stderr, chunk);
    stderrTail = (stderrTail + chunk).slice(-STDERR_TAIL_MAX);
  });

  child.on("error", (err) => {
    spawnError = err.message;
    state.lifecycle = "failed";
    state.processAlive = false;
    noteError(state, spawnError);
    writeStatus();
  });

  const heartbeat = setInterval(() => writeStatus(), HEARTBEAT_MS);
  heartbeat.unref?.();

  const forward = (sig) => {
    try {
      if (state.pid && pidAlive(state.pid)) process.kill(state.pid, sig);
    } catch {
      /* child already gone */
    }
  };
  let shuttingDown = false;
  const abortChild = (sig, reason) => {
    if (shuttingDown) return;
    shuttingDown = true;
    if (reason === "timeout") {
      state.timedOut = true;
      noteError(state, `timeout after ${state.timeoutMs}ms`);
      writeStatus();
    }
    forward(sig);
    setTimeout(() => {
      try {
        if (state.pid && pidAlive(state.pid)) process.kill(state.pid, "SIGKILL");
      } catch {
        /* gone */
      }
    }, GRACEFUL_KILL_MS).unref();
  };
  process.on("SIGTERM", () => abortChild("SIGTERM", "signal"));
  process.on("SIGINT", () => abortChild("SIGINT", "signal"));

  if (opts.timeoutMs) {
    timeoutTimer = setTimeout(() => {
      abortChild("SIGTERM", "timeout");
    }, opts.timeoutMs);
    timeoutTimer.unref?.();
  }

  const exit = await new Promise((resolve) => {
    child.on("close", (code, signal) => {
      resolve({ code, signal });
    });
  });
  clearInterval(heartbeat);
  if (timeoutTimer) clearTimeout(timeoutTimer);
  if (pendingThrottle) writeStatus();

  state.exitCode = exit.code;
  state.signal = exit.signal;
  state.processAlive = false;
  setCurrent(state, null);

  if (state.timedOut) state.lifecycle = "timed_out";
  else if (exit.signal) state.lifecycle = "terminated";
  else if (spawnError) state.lifecycle = "failed";
  else if (exit.code === 0) state.lifecycle = "completed";
  else state.lifecycle = "failed";

  if (opts.print) {
    state._lastAssistant = state._lastAssistant || {
      text: stdoutText.trim(),
      stopReason: exit.code === 0 && !state.timedOut ? "stop" : "error",
      errorMessage: exit.code === 0 && !state.timedOut ? null : stderrTail || spawnError,
    };
    if (!state._lastAssistant.text) state._lastAssistant.text = stdoutText.trim();
  }

  if (stderrTail && state.lifecycle !== "completed") {
    noteError(state, stderrTail.trim().split("\n").pop());
  }

  writeStatus();
  const report = buildReport(state, {
    stdoutText: opts.print ? stdoutText : null,
    stderrTail,
    spawnError,
  });
  writeAtomic(paths.report, report);
  process.stdout.write(`LIFECYCLE=${state.lifecycle}\nREPORT_FILE=${paths.report}\n`);
  // Exit 0 only when the process completed cleanly. reportValid is separate —
  // Cursor must still read report.json (do not treat exit 0 as worker success).
  return state.lifecycle === "completed" ? 0 : exit.code || 1;
}

function assert(cond, msg) {
  if (!cond) throw new Error(msg);
}

function selfTest() {
  const state = emptyState({
    jobName: "self",
    runId: "r1",
    runDir: "/tmp/pi-harness-self",
    print: false,
  });
  applyEvent(state, { type: "session", id: "sess-1" });
  assert(state.sessionId === "sess-1", "session id");
  applyEvent(state, { type: "agent_start" });
  applyEvent(state, {
    type: "message_update",
    usage: {},
    assistantMessageEvent: { type: "thinking_delta", delta: "x" },
  });
  assert(state.current?.kind === "thinking", "thinking current");
  applyEvent(state, {
    type: "message_update",
    assistantMessageEvent: { type: "toolcall_start", id: "c1", toolName: "bash" },
  });
  assert(state.current?.kind === "emitting_tool_call", "emit tool call is not execution");
  applyEvent(state, {
    type: "tool_execution_start",
    toolCallId: "c1",
    toolName: "bash",
    args: { command: "sleep 1" },
  });
  assert(state.current?.kind === "tool" && state.current.name === "bash", "tool running");
  applyEvent(state, {
    type: "message_update",
    assistantMessageEvent: { type: "thinking_delta", delta: "ignored" },
  });
  assert(state.current?.kind === "tool", "do not clobber active tool");
  applyEvent(state, {
    type: "tool_execution_end",
    toolCallId: "c1",
    toolName: "bash",
    result: { huge: "no" },
    isError: false,
  });
  assert(state.recent.length === 1 && state.recent[0].outcome === "ok", "recent tool");
  applyEvent(state, {
    type: "message_end",
    message: {
      role: "assistant",
      stopReason: "stop",
      content: [
        { type: "thinking", thinking: "secret" },
        { type: "text", text: "STATUS: ok\nSUMMARY done\nfiles changed: none" },
      ],
    },
  });
  assert(
    state._lastAssistant.text.startsWith("STATUS: ok"),
    "extract text not thinking",
  );
  applyEvent(state, { type: "not_a_real_type" });
  applyEvent(state, null);
  assert(state.parseErrors >= 1, "malformed counted");
  assert(!JSON.stringify(publicStatus(state)).includes("STATUS: ok"), "status omits report body");

  state.lifecycle = "completed";
  state.exitCode = 0;
  const good = buildReport(state, {});
  assert(good.workerStatus === "ok", "parse worker STATUS");
  assert(good.reportValid === true, "reportValid when STATUS present");

  state._lastAssistant = { text: "all done, no status token", stopReason: "stop", errorMessage: null };
  const badReport = buildReport(state, {});
  assert(badReport.workerStatus === null, "missing STATUS");
  assert(badReport.reportValid === false, "reportValid false without STATUS");
  assert(/missing worker STATUS/i.test(badReport.errorMessage || ""), "flag missing STATUS");

  assert(parseTimeoutMs("30") === 30_000, "timeout seconds");
  assert(parseTimeoutMs("500ms") === 500, "timeout ms");
  let timeoutThrew = false;
  try {
    parseTimeoutMs("0");
  } catch {
    timeoutThrew = true;
  }
  assert(timeoutThrew, "reject zero timeout");

  const parsed = parseArgs([
    "node",
    "x",
    "--name",
    "j",
    "--timeout",
    "10",
    "--model",
    "glm-test",
    "--provider",
    "opencode-go",
    "--",
    "hi",
  ]);
  assert(parsed.timeoutMs === 10_000, "parse --timeout");
  assert(parsed.model === "glm-test", "parse --model");
  assert(parsed.provider === "opencode-go", "parse --provider");
  assert(parsed.piArgs[0] === "hi", "prompt after --");

  let noModel = false;
  try {
    requireModel(parseArgs(["node", "x", "--name", "j", "--", "hi"]));
  } catch {
    noModel = true;
  }
  assert(noModel, "block when --model missing");

  requireModel(
    parseArgs(["node", "x", "--name", "j", "--", "--model", "x/y", "hi"]),
  );
  const built = buildPiArgs({
    print: true,
    provider: "opencode-go",
    model: "mimo-v2.6-flash",
    thinking: "high",
    piArgs: ["do it"],
  });
  assert(built.includes("--model") && built.includes("mimo-v2.6-flash"), "forward model");
  assert(!built.includes("glm-5.3-flash"), "no default model");

  const bad = parseArgs(["node", "x", "--name", "../evil"]);
  let threw = false;
  try {
    sanitizeName(bad.name);
  } catch {
    threw = true;
  }
  assert(threw, "reject path-like names");

  state.timedOut = true;
  state.lifecycle = "timed_out";
  state.timeoutMs = 1000;
  state._lastAssistant = null;
  const timed = buildReport(state, {});
  assert(timed.lifecycle === "timed_out", "timed_out lifecycle in report");
  assert(timed.timedOut === true, "timedOut flag");

  console.log("self-test ok");
}

const opts = parseArgs(process.argv);
if (opts.selfTest) {
  try {
    selfTest();
  } catch (err) {
    console.error(err.message);
    process.exit(1);
  }
} else {
  if (!opts.name) {
    console.error(
      "usage: pi-spawn.mjs --name <job> --model <id> [--provider <name>] [--thinking <level>] [--cwd dir] [--print] [--timeout <sec|Nms>] -- <prompt or pi args>",
    );
    process.exit(2);
  }
  try {
    requireModel(opts);
  } catch (err) {
    console.error(err.message);
    process.exit(2);
  }
  if (!existsSync(WORKER_CONTRACT)) {
    console.error(`missing worker contract: ${WORKER_CONTRACT}`);
    process.exit(2);
  }
  runJob(opts)
    .then((code) => process.exit(code))
    .catch((err) => {
      console.error(err);
      process.exit(1);
    });
}
