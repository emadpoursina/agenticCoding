#!/usr/bin/env node
/**
 * Cursor-facing Claude Code worker launcher.
 *
 * Official Claude Code headless mode stays on disk (events.jsonl). Cursor polls status.json.
 * Execs official Claude Code print mode (claude -p).
 * Short jobs use default text stdout; long jobs use --output-format stream-json --verbose.
 * Edit jobs pass --permission-mode auto; scout passes --permission-mode plan.
 * Never passes --bare by default, never passes skip-permissions or bypassPermissions.
 * Child stdin is ignored (DEVNULL).
 */
import { spawn, spawnSync } from "node:child_process";
import {
  mkdirSync,
  writeFileSync,
  appendFileSync,
  renameSync,
  existsSync,
  readFileSync,
} from "node:fs";
import { join, dirname } from "node:path";
import { fileURLToPath } from "node:url";
import { randomBytes } from "node:crypto";
import assert from "node:assert";

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
const TIMEOUT_KILL_SIGNALS = ["SIGINT", "SIGTERM", "SIGKILL"];

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
    scout: false,
    model: null,
    effort: null,
    timeoutMs: null,
    conversationId: null,
    runId: null,
    selfTest: false,
    promptArgs: [],
  };
  const args = argv.slice(2);
  for (let i = 0; i < args.length; i++) {
    const a = args[i];
    if (a === "--") {
      out.promptArgs.push(...args.slice(i + 1));
      break;
    }
    if (a === "--self-test") out.selfTest = true;
    else if (a === "--print" || a === "-p") out.print = true;
    else if (a === "--scout") out.scout = true;
    else if (a === "--name") out.name = takeValue(args, i++, "--name");
    else if (a === "--cwd") out.cwd = takeValue(args, i++, "--cwd");
    else if (a === "--model") out.model = takeValue(args, i++, "--model");
    else if (a === "--effort") out.effort = takeValue(args, i++, "--effort");
    else if (a === "--timeout") out.timeoutMs = parseTimeoutMs(takeValue(args, i++, "--timeout"));
    else if (a === "--conversation-id") out.conversationId = takeValue(args, i++, "--conversation-id");
    else if (a === "--run-id") out.runId = takeValue(args, i++, "--run-id");
    else if (a.startsWith("--name=")) out.name = a.slice(7);
    else if (a.startsWith("--cwd=")) out.cwd = a.slice(6);
    else if (a.startsWith("--model=")) out.model = a.slice(8);
    else if (a.startsWith("--effort=")) out.effort = a.slice(9);
    else if (a.startsWith("--timeout=")) out.timeoutMs = parseTimeoutMs(a.slice(10));
    else if (a.startsWith("--conversation-id=")) out.conversationId = a.slice(18);
    else if (a.startsWith("--run-id=")) out.runId = a.slice(9);
    else out.promptArgs.push(a);
  }

  // Also check if --model was placed in promptArgs after --
  if (!out.model) {
    for (let i = 0; i < out.promptArgs.length; i++) {
      const pa = out.promptArgs[i];
      if (pa === "--model") {
        out.model = out.promptArgs[i + 1];
        out.promptArgs.splice(i, 2);
        break;
      }
      if (pa.startsWith("--model=")) {
        out.model = pa.slice(8);
        out.promptArgs.splice(i, 1);
        break;
      }
    }
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

function requireModel(opts) {
  if (opts.model && String(opts.model).trim()) return;
  if (argvHasModel(opts.promptArgs)) return;
  const err = new Error(
    "blocked: --model is required (pass --model <id> before or after --; no harness default)",
  );
  err.code = "ERR_MODEL_REQUIRED";
  err.exitCode = 2;
  throw err;
}

function getWorkerContractContent() {
  if (existsSync(WORKER_CONTRACT)) {
    return readFileSync(WORKER_CONTRACT, "utf8");
  }
  return "";
}

function probeClaudeCapabilities(bin = (process.env.SPECKIT_CLAUDE_BIN || "claude"), customHelpText = null) {
  let helpText = customHelpText;
  if (helpText == null) {
    try {
      const res = spawnSync(bin, ["--help"], { encoding: "utf8", timeout: 5000 });
      if (res.status === 0 && res.stdout) {
        helpText = res.stdout;
      } else {
        helpText = "";
      }
    } catch {
      helpText = "";
    }
  }

  return {
    hasHelp: Boolean(helpText && helpText.length > 0),
    hasAppendSystemPromptFile: helpText.includes("--append-system-prompt-file"),
    hasAppendSystemPrompt: helpText.includes("--append-system-prompt"),
    hasPermissionPrompts: helpText.includes("--permission-prompts"),
    hasNoSessionPersistence: helpText.includes("--no-session-persistence"),
    hasEffort: helpText.includes("--effort"),
    hasPermissionMode: helpText.includes("--permission-mode"),
    hasPrint: helpText.includes("-p") || helpText.includes("--print"),
    hasModel: helpText.includes("--model"),
  };
}

function buildClaudeArgs(opts, capabilities = null) {
  const caps = capabilities || probeClaudeCapabilities();

  if (caps.hasHelp) {
    if (!caps.hasPrint) {
      throw new Error("installed claude does not support required -p/--print flag");
    }
    if (!caps.hasModel) {
      throw new Error("installed claude does not support required --model flag");
    }
    if (!caps.hasPermissionMode) {
      throw new Error("installed claude does not support required --permission-mode flag");
    }
  }

  const args = [];
  // Invariant 1: always -p
  args.push("-p");

  // Invariant 2: output format
  if (!opts.print) {
    args.push("--output-format", "stream-json", "--verbose");
  }

  // Invariant 3: permission mode
  if (opts.scout) {
    args.push("--permission-mode", "plan");
  } else {
    args.push("--permission-mode", "auto");
  }

  // Optional permission-prompts none
  if (caps.hasPermissionPrompts) {
    args.push("--permission-prompts", "none");
  }

  // Model
  if (opts.model) {
    args.push("--model", opts.model);
  }

  // Effort (only if set AND CLI accepts it)
  if (opts.effort) {
    if (caps.hasEffort) {
      args.push("--effort", opts.effort);
    }
  }

  // Session persistence / resume
  if (opts.conversationId) {
    args.push("--resume", opts.conversationId);
  } else if (caps.hasNoSessionPersistence) {
    args.push("--no-session-persistence");
  }

  // Contract attachment
  if (caps.hasAppendSystemPromptFile) {
    args.push("--append-system-prompt-file", WORKER_CONTRACT);
  } else if (caps.hasAppendSystemPrompt) {
    const text = opts.contractContent ?? getWorkerContractContent();
    args.push("--append-system-prompt", text);
  } else {
    const err = new Error(
      "fail-closed: neither --append-system-prompt-file nor --append-system-prompt is supported by installed claude",
    );
    err.code = "ERR_APPEND_UNSUPPORTED";
    throw err;
  }

  // Positional prompt args (job prompt after --)
  if (opts.promptArgs && opts.promptArgs.length > 0) {
    args.push(...opts.promptArgs);
  }

  return args;
}

function failClosedOnRequiredFlag(state, flagName, reason) {
  state.lifecycle = "failed";
  state.processAlive = false;
  state.lastError = `rejected required flag ${flagName}: ${reason} (no retry)`;
  return state;
}

function emptyState(meta) {
  return {
    schemaVersion: SCHEMA_VERSION,
    jobName: meta.jobName,
    runId: meta.runId,
    runDir: meta.runDir,
    backend: "claude-cli",
    print: Boolean(meta.print),
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

  if (ev.session_id || ev.sessionId || ev.id) {
    state.sessionId = ev.session_id || ev.sessionId || ev.id;
  }

  if (state.lifecycle === "starting") {
    state.lifecycle = "running";
  }

  if (ev.type === "system") {
    return "flush";
  }

  if (ev.type === "assistant") {
    if (Array.isArray(ev.content)) {
      const toolUse = ev.content.find((c) => c && c.type === "tool_use");
      if (toolUse) {
        setCurrent(state, { kind: "tool", name: toolUse.name || "unknown" });
      } else {
        setCurrent(state, { kind: "writing" });
      }
    } else {
      setCurrent(state, { kind: "writing" });
    }
    return "flush";
  }

  if (ev.type === "result") {
    setCurrent(state, null);
    return "flush";
  }

  return "throttle";
}

function publicStatus(state) {
  const s = enrich({ ...state });
  delete s._lastAssistant;
  delete s.summary;
  return s;
}

function reconstructStreamJsonText(lines, onParseError = null) {
  let lastResultText = null;
  const mainAssistantTexts = [];
  const subAssistantTexts = [];
  const streamDeltas = [];

  for (const line of lines) {
    if (typeof line !== "string" || !line.trim()) continue;
    let ev;
    try {
      ev = JSON.parse(line);
    } catch (err) {
      if (onParseError) onParseError(err);
      continue;
    }
    if (!ev || typeof ev !== "object") continue;

    // Check type == "result"
    if (ev.type === "result") {
      let r = ev.result;
      if (r && typeof r === "object" && typeof r.result === "string") {
        r = r.result;
      }
      if (typeof r === "string" && r.trim()) {
        lastResultText = r.trim();
      }
    }

    // Check type == "assistant"
    if (ev.type === "assistant" && Array.isArray(ev.content)) {
      const texts = ev.content
        .filter((c) => c && c.type === "text" && typeof c.text === "string")
        .map((c) => c.text);
      if (texts.length > 0) {
        if (ev.parent_tool_use_id != null) {
          subAssistantTexts.push(...texts);
        } else {
          mainAssistantTexts.push(...texts);
        }
      }
    }

    // Check stream_event / text_delta
    if (ev.type === "stream_event" || ev.event === "text_delta") {
      const delta =
        ev.text_delta ||
        ev.delta?.text ||
        ev.data?.text_delta ||
        (ev.event === "text_delta" && typeof ev.text === "string" ? ev.text : null);
      if (typeof delta === "string") {
        streamDeltas.push(delta);
      }
    }
  }

  if (lastResultText) return lastResultText;
  if (mainAssistantTexts.length > 0) return mainAssistantTexts.join("\n").trim();
  if (subAssistantTexts.length > 0) return subAssistantTexts.join("\n").trim();
  if (streamDeltas.length > 0) return streamDeltas.join("").trim();
  return null;
}

function buildReport(state, extra = {}) {
  let summary = extra.summaryText ?? null;
  if (typeof summary === "string") summary = summary.trim() || null;
  const extracted = Boolean(summary);
  const workerStatus = parseWorkerStatus(summary);
  const reportValid = workerStatus != null;
  let errorMessage = extra.spawnError || state.lastError || null;
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
    backend: "claude-cli",
    lifecycle: state.lifecycle,
    exitCode: state.exitCode,
    signal: state.signal,
    timedOut: Boolean(state.timedOut),
    timeoutMs: state.timeoutMs ?? null,
    summaryExtracted: extracted,
    summary: extracted ? clip(summary, SUMMARY_MAX) : null,
    workerStatus,
    reportValid,
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
    if (buf.trim()) onLine(buf);
  });
}

async function runJob(opts) {
  const jobName = sanitizeName(opts.name);
  const runId = opts.runId || makeRunId();
  const cwd = opts.cwd || process.cwd();
  const claudeBin = process.env.SPECKIT_CLAUDE_BIN || "claude";

  const runDir = join(cwd, ".agent", "claude", jobName, runId);
  mkdirSync(runDir, { recursive: true });

  const paths = {
    status: join(runDir, "status.json"),
    report: join(runDir, "report.json"),
    events: join(runDir, "events.jsonl"),
    stderr: join(runDir, "stderr.log"),
    latest: join(cwd, ".agent", "claude", jobName, "latest.json"),
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

  const writeStatus = () => writeAtomic(paths.status, publicStatus(state));
  writeStatus();

  let capabilities;
  try {
    capabilities = probeClaudeCapabilities(claudeBin);
  } catch (err) {
    state.lifecycle = "failed";
    noteError(state, `probe error: ${err.message}`);
    writeStatus();
    writeAtomic(paths.report, buildReport(state, { spawnError: err.message }));
    process.stdout.write(`RUN_DIR=${runDir}\nSTATUS_FILE=${paths.status}\nLIFECYCLE=failed\nREPORT_FILE=${paths.report}\n`);
    return 1;
  }

  let claudeArgs;
  try {
    claudeArgs = buildClaudeArgs(opts, capabilities);
  } catch (err) {
    state.lifecycle = "failed";
    noteError(state, err.message);
    writeStatus();
    writeAtomic(paths.report, buildReport(state, { spawnError: err.message }));
    process.stdout.write(`RUN_DIR=${runDir}\nSTATUS_FILE=${paths.status}\nLIFECYCLE=failed\nREPORT_FILE=${paths.report}\n`);
    return 1;
  }

  let stdoutText = "";
  let stderrTail = "";
  let spawnError = null;
  let timeoutTimer = null;
  const rawEvents = [];

  const handleJsonLine = (line) => {
    if (!line.trim()) return;
    appendFileSync(paths.events, `${line}\n`);
    rawEvents.push(line);
    let ev;
    try {
      ev = JSON.parse(line);
    } catch (err) {
      state.parseErrors += 1;
      noteError(state, `malformed json: ${err.message}`);
      writeStatus();
      return;
    }
    applyEvent(state, ev);
    writeStatus();
  };

  let child;
  try {
    child = spawn(claudeBin, claudeArgs, {
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
    process.stdout.write(`RUN_DIR=${runDir}\nSTATUS_FILE=${paths.status}\nLIFECYCLE=failed\nREPORT_FILE=${paths.report}\n`);
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
    } catch {}
  };

  let shuttingDown = false;
  const abortChild = (sig, reason) => {
    if (shuttingDown) return;
    shuttingDown = true;
    if (reason === "timeout") {
      state.timedOut = true;
      state.lifecycle = "timed_out";
      noteError(state, `timeout after ${state.timeoutMs}ms`);
      writeStatus();
    }
    forward("SIGINT");
    setTimeout(() => {
      forward("SIGTERM");
      setTimeout(() => {
        forward("SIGKILL");
      }, GRACEFUL_KILL_MS);
    }, GRACEFUL_KILL_MS);
  };

  if (typeof opts.timeoutMs === "number" && opts.timeoutMs > 0) {
    timeoutTimer = setTimeout(() => {
      abortChild("SIGINT", "timeout");
    }, opts.timeoutMs);
    timeoutTimer.unref?.();
  }

  const exitPromise = new Promise((resolve) => {
    child.on("close", (code, signal) => {
      if (timeoutTimer) clearTimeout(timeoutTimer);
      clearInterval(heartbeat);
      state.processAlive = false;
      state.exitCode = code;
      state.signal = signal;

      if (state.timedOut) {
        state.lifecycle = "timed_out";
      } else if (signal) {
        state.lifecycle = "terminated";
      } else if (code === 0) {
        state.lifecycle = "completed";
      } else {
        state.lifecycle = "failed";
        if (stderrTail && (/permission-mode/i.test(stderrTail) || /unknown option/i.test(stderrTail))) {
          failClosedOnRequiredFlag(state, "--permission-mode", stderrTail);
        }
      }

      writeStatus();

      let summaryText = null;
      if (opts.print) {
        summaryText = stdoutText;
      } else {
        summaryText = reconstructStreamJsonText(rawEvents, () => {
          state.parseErrors += 1;
        });
      }

      const rep = buildReport(state, { summaryText, stderrTail, spawnError });
      writeAtomic(paths.report, rep);

      process.stdout.write(`RUN_DIR=${runDir}\nSTATUS_FILE=${paths.status}\nLIFECYCLE=${state.lifecycle}\nREPORT_FILE=${paths.report}\n`);

      resolve(state.lifecycle === "completed" ? 0 : 1);
    });
  });

  return await exitPromise;
}

function selfTest() {
  // 1. Argument parsing & sanitizer
  assert(sanitizeName("valid-job_name.1") === "valid-job_name.1", "valid name");
  let threw = false;
  try {
    sanitizeName("../evil");
  } catch {
    threw = true;
  }
  assert(threw, "reject path-like name");

  // Timeout parsing
  assert(parseTimeoutMs("30") === 30000, "parse timeout sec");
  assert(parseTimeoutMs("500ms") === 500, "parse timeout ms");
  let timeoutThrew = false;
  try {
    parseTimeoutMs("0");
  } catch {
    timeoutThrew = true;
  }
  assert(timeoutThrew, "reject zero timeout");

  // STATUS parsing regex
  assert(parseWorkerStatus("STATUS: ok") === "ok", "parse STATUS: ok");
  assert(parseWorkerStatus("STATUS: stuck\nDone") === "stuck", "parse STATUS: stuck");
  assert(parseWorkerStatus("STATUS=blocked") === "blocked", "parse STATUS=blocked");
  assert(parseWorkerStatus("no status here") === null, "no status token");

  // TF-1: Short print job shape
  const printOpts = parseArgs([
    "node",
    "claude-spawn.mjs",
    "--name",
    "short-job",
    "--model",
    "claude-3-5-sonnet-20241022",
    "--print",
    "--",
    "do something",
  ]);
  const dummyCaps = {
    hasHelp: true,
    hasPrint: true,
    hasModel: true,
    hasPermissionMode: true,
    hasAppendSystemPromptFile: true,
    hasAppendSystemPrompt: true,
    hasPermissionPrompts: true,
    hasNoSessionPersistence: true,
    hasEffort: true,
  };
  const printArgs = buildClaudeArgs(printOpts, dummyCaps);
  assert(printArgs.includes("-p") || printArgs.includes("--print"), "print job has -p");
  assert(printArgs.includes("--model") && printArgs.includes("claude-3-5-sonnet-20241022"), "print job has model");
  assert(!printArgs.includes("--output-format"), "print job omits --output-format");
  assert(!printArgs.includes("--bare"), "print job omits --bare");
  assert(!printArgs.includes("--dangerously-skip-permissions"), "print job omits skip permissions");
  assert(!printArgs.includes("bypassPermissions"), "print job omits bypassPermissions");
  assert(!printArgs.includes("--input-format"), "print job omits --input-format");
  assert(!printArgs.includes("--bg") && !printArgs.includes("--background"), "print job omits --bg");
  assert(!printArgs.includes("--desktop"), "print job omits --desktop");
  assert(!printArgs.includes("--prompt-interactive"), "print job omits --prompt-interactive");
  assert(!printArgs.includes("--cloud"), "print job omits --cloud");
  assert(printArgs.includes("--permission-mode") && printArgs[printArgs.indexOf("--permission-mode") + 1] === "auto", "default edit has auto");

  // TF-2: Long stream-json job shape
  const longOpts = parseArgs([
    "node",
    "claude-spawn.mjs",
    "--name",
    "long-job",
    "--model",
    "claude-3-5-sonnet-20241022",
    "--",
    "long task",
  ]);
  const longArgs = buildClaudeArgs(longOpts, dummyCaps);
  assert(longArgs.includes("-p"), "long job has -p");
  assert(longArgs.includes("--output-format") && longArgs[longArgs.indexOf("--output-format") + 1] === "stream-json", "long job has stream-json");
  assert(longArgs.includes("--verbose"), "long job has --verbose");
  assert(!longArgs.includes("--bare"), "long job omits --bare");
  assert(!longArgs.includes("--input-format"), "long job omits --input-format");
  assert(!longArgs.includes("--bg") && !longArgs.includes("--background"), "long job omits --bg");
  assert(!longArgs.includes("--desktop"), "long job omits --desktop");
  assert(!longArgs.includes("--prompt-interactive"), "long job omits --prompt-interactive");
  assert(!longArgs.includes("--cloud"), "long job omits --cloud");

  // TF-3: Scout vs edit
  const scoutOpts = parseArgs([
    "node",
    "claude-spawn.mjs",
    "--name",
    "scout-job",
    "--model",
    "claude-3-5-sonnet-20241022",
    "--scout",
    "--",
    "inspect only",
  ]);
  const scoutArgs = buildClaudeArgs(scoutOpts, dummyCaps);
  assert(scoutArgs.includes("--permission-mode") && scoutArgs[scoutArgs.indexOf("--permission-mode") + 1] === "plan", "scout has permission-mode plan");
  assert(!scoutArgs.includes("auto"), "scout omits auto");
  assert(!scoutArgs.includes("--dangerously-skip-permissions"), "scout omits skip permissions");
  assert(!scoutArgs.includes("bypassPermissions"), "scout omits bypassPermissions");

  // Fail-closed helper assertion
  const testState = emptyState({ jobName: "test", runId: "r1", runDir: "/tmp" });
  failClosedOnRequiredFlag(testState, "--permission-mode auto", "rejected by cli");
  assert(testState.lifecycle === "failed", "required flag rejection finalizes failed");
  assert(testState.processAlive === false, "processAlive false on rejection");
  assert(testState.lastError.includes("--permission-mode auto"), "error records rejected flag");

  // TF-5: Error / edge cases
  // Missing model throws with exit code 2
  let noModelThrown = false;
  let noModelCode = null;
  try {
    requireModel(parseArgs(["node", "claude-spawn.mjs", "--name", "no-model", "--", "hi"]));
  } catch (err) {
    noModelThrown = true;
    noModelCode = err.exitCode;
  }
  assert(noModelThrown, "missing --model throws");
  assert(noModelCode === 2, "missing --model exit code 2");

  // Model after -- is accepted
  const modelAfterDash = parseArgs(["node", "claude-spawn.mjs", "--name", "j", "--", "--model", "custom-model", "hi"]);
  requireModel(modelAfterDash);
  assert(modelAfterDash.model === "custom-model", "model parsed from promptArgs");

  // Timeout sets wrapper timer fields only, does not add --max-turns or --max-budget-usd
  const timeoutOpts = parseArgs([
    "node",
    "claude-spawn.mjs",
    "--name",
    "timeout-job",
    "--model",
    "sonnet",
    "--timeout",
    "2",
    "--",
    "hi",
  ]);
  assert(timeoutOpts.timeoutMs === 2000, "timeoutMs set to 2000");
  const timeoutArgs = buildClaudeArgs(timeoutOpts, dummyCaps);
  assert(!timeoutArgs.includes("--max-turns"), "no --max-turns flag in argv");
  assert(!timeoutArgs.includes("--max-budget-usd"), "no --max-budget-usd flag in argv");

  // Omitted timeout has no wrapper-invented timer
  assert(longOpts.timeoutMs === null, "omitted timeout has null timeoutMs");

  // Conversation-id maps to --resume and omits --no-session-persistence
  const resumeOpts = parseArgs([
    "node",
    "claude-spawn.mjs",
    "--name",
    "resume-job",
    "--model",
    "sonnet",
    "--conversation-id",
    "sess-123",
    "--",
    "continue",
  ]);
  const resumeArgs = buildClaudeArgs(resumeOpts, dummyCaps);
  assert(resumeArgs.includes("--resume") && resumeArgs[resumeArgs.indexOf("--resume") + 1] === "sess-123", "maps to --resume sess-123");
  assert(!resumeArgs.includes("--no-session-persistence"), "resume omits --no-session-persistence");
  assert(!resumeArgs.includes("--continue"), "never pass --continue");

  // Default isolated includes --no-session-persistence when probed present and never --continue / --resume without id
  assert(printArgs.includes("--no-session-persistence"), "default isolated includes --no-session-persistence");
  assert(!printArgs.includes("--continue"), "default isolated omits --continue");
  assert(!printArgs.includes("--resume"), "default isolated omits --resume");

  // Contract append: preference 1 file, preference 2 text
  const fileAppendCaps = { ...dummyCaps, hasAppendSystemPromptFile: true, hasAppendSystemPrompt: false };
  const fileArgs = buildClaudeArgs(printOpts, fileAppendCaps);
  assert(fileArgs.includes("--append-system-prompt-file"), "uses --append-system-prompt-file when present");

  const textAppendCaps = { ...dummyCaps, hasAppendSystemPromptFile: false, hasAppendSystemPrompt: true };
  const textArgs = buildClaudeArgs({ ...printOpts, contractContent: "my contract text" }, textAppendCaps);
  assert(textArgs.includes("--append-system-prompt") && textArgs.includes("my contract text"), "fallback to --append-system-prompt");

  // Dual-append failure is fail-closed
  const noAppendCaps = { ...dummyCaps, hasAppendSystemPromptFile: false, hasAppendSystemPrompt: false };
  let appendFail = false;
  try {
    buildClaudeArgs(printOpts, noAppendCaps);
  } catch (err) {
    appendFail = true;
    assert(err.code === "ERR_APPEND_UNSUPPORTED", "append fail code");
  }
  assert(appendFail, "dual-append failure is fail-closed");

  // Non-zero child exit -> lifecycle=failed even if stdout has STATUS: ok
  const failState = emptyState({ jobName: "f", runId: "r2", runDir: "/tmp" });
  failState.lifecycle = "failed";
  failState.exitCode = 1;
  const failReport = buildReport(failState, { summaryText: "STATUS: ok\nall good" });
  assert(failReport.lifecycle === "failed", "lifecycle stays failed on exit 1");
  assert(failReport.workerStatus === "ok", "workerStatus ok parsed from text");
  assert(failReport.reportValid === true, "reportValid true");

  // Stream-json reconstruct: type=="result" wins over assistant text
  const streamFixture = [
    JSON.stringify({ type: "system", message: "init" }),
    JSON.stringify({ type: "assistant", content: [{ type: "text", text: "STATUS: stuck\nNeed info" }] }),
    JSON.stringify({ type: "result", result: "STATUS: ok\nEverything finished successfully" }),
  ];
  const reconstructed = reconstructStreamJsonText(streamFixture);
  assert(reconstructed.includes("STATUS: ok"), "result text wins over assistant text");
  assert(parseWorkerStatus(reconstructed) === "ok", "worker status ok from result");

  // Fixture with only text_delta still parses STATUS: ok
  const deltaFixture = [
    JSON.stringify({ type: "stream_event", text_delta: "STATUS: " }),
    JSON.stringify({ type: "stream_event", text_delta: "ok\nDone" }),
  ];
  const deltaReconstructed = reconstructStreamJsonText(deltaFixture);
  assert(deltaReconstructed.includes("STATUS: ok"), "stream_event text_delta reconstructs text");
  assert(parseWorkerStatus(deltaReconstructed) === "ok", "worker status ok from delta");

  // Malformed JSONL lines increment parseErrors and do not crash
  let parseErrCount = 0;
  const malformedFixture = [
    "not valid json {{{",
    JSON.stringify({ type: "assistant", content: [{ type: "text", text: "STATUS: blocked\nGate error" }] }),
    "another bad json",
  ];
  const malformedReconstructed = reconstructStreamJsonText(malformedFixture, () => {
    parseErrCount += 1;
  });
  assert(parseErrCount === 2, "malformed lines counted");
  assert(malformedReconstructed.includes("STATUS: blocked"), "valid line extracted despite malformed lines");
  assert(parseWorkerStatus(malformedReconstructed) === "blocked", "status parsed despite malformed lines");

  // SIGINT-then-SIGTERM-then-SIGKILL order encoded in timeout helper fields
  assert.deepStrictEqual(TIMEOUT_KILL_SIGNALS, ["SIGINT", "SIGTERM", "SIGKILL"], "signal sequence is SIGINT then SIGTERM then SIGKILL");

  console.log("SELFTEST: ok");
}

const opts = parseArgs(process.argv);
if (opts.selfTest) {
  try {
    selfTest();
    process.exit(0);
  } catch (err) {
    console.error(err);
    process.exit(1);
  }
} else {
  if (!opts.name) {
    console.error(
      "usage: claude-spawn.mjs --name <job> --model <id> [--cwd dir] [--print] [--scout] [--effort <level>] [--timeout <sec|Nms>] [--conversation-id <id>] -- <prompt>",
    );
    process.exit(2);
  }
  try {
    sanitizeName(opts.name);
  } catch (err) {
    console.error(err.message);
    process.exit(2);
  }
  try {
    requireModel(opts);
  } catch (err) {
    console.error(err.message);
    process.exit(err.exitCode || 2);
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
