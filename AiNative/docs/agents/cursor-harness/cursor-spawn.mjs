#!/usr/bin/env node
/**
 * Headless Cursor SDK worker. One local agent, one prompt, files on disk.
 * Docs: https://cursor.com/docs/sdk/typescript.md
 *
 * Exit 0: the run finished. Check report.json workerStatus / reportValid.
 * Exit 1: spawn or runtime failure.
 * Exit 2: caller precondition. Nothing was started.
 */
import { appendFileSync, existsSync, mkdirSync, readFileSync, renameSync, statSync, writeFileSync } from "node:fs";
import { createRequire } from "node:module";
import { homedir } from "node:os";
import { dirname, join } from "node:path";
import { fileURLToPath, pathToFileURL } from "node:url";

const SCHEMA_VERSION = 1;
const SKILL_DIR = dirname(fileURLToPath(import.meta.url));
const WORKER_CONTRACT = join(SKILL_DIR, "worker-contract.md");
const SCOUT_TOOLS = ["read", "grep", "glob", "ls"];
const DEFAULT_SETTING_SOURCES = ["project", "user", "plugins"];
const SUMMARY_MAX = 8000;
const ERROR_MAX = 2000;
const HEARTBEAT_MS = 2000;
const MIN_NODE = [22, 13, 0];

const WORKER_STATUS_RE = /^[ \t]*STATUS:[ \t]*(ok|stuck|blocked)\b/im;

function nowIso() {
  return new Date().toISOString();
}

function clip(s, n) {
  if (s == null) return null;
  const text = String(s);
  return text.length <= n ? text : text.slice(0, n);
}

function sanitizeName(name) {
  const cleaned = String(name || "job").replace(/[^A-Za-z0-9._-]+/g, "-").replace(/^-+|-+$/g, "");
  return cleaned.slice(0, 80) || "job";
}

function makeRunId() {
  const stamp = new Date().toISOString().replace(/[-:]/g, "").replace(/\.\d+Z$/, "Z");
  const rand = Math.random().toString(36).slice(2, 8);
  return `${stamp}-${rand}`;
}

function writeAtomic(path, obj) {
  const tmp = `${path}.tmp`;
  writeFileSync(tmp, `${JSON.stringify(obj, null, 2)}\n`);
  renameSync(tmp, path);
}

function parseTimeoutMs(raw) {
  const text = String(raw).trim();
  const ms = /^(\d+)ms$/.exec(text);
  if (ms) return Number(ms[1]);
  if (/^\d+$/.test(text)) return Number(text) * 1000;
  const err = new Error(`--timeout must be seconds or Nms, got ${raw}`);
  err.exitCode = 2;
  throw err;
}

function parseWorkerStatus(text) {
  if (!text || typeof text !== "string") return null;
  const match = WORKER_STATUS_RE.exec(text);
  return match ? match[1].toLowerCase() : null;
}

function takeValue(args, i, flag) {
  const next = args[i + 1];
  if (next == null || next.startsWith("--")) {
    const err = new Error(`${flag} requires a value`);
    err.exitCode = 2;
    throw err;
  }
  return next;
}

function splitCsv(raw) {
  return String(raw)
    .split(",")
    .map((part) => part.trim())
    .filter(Boolean);
}

function parseArgs(argv) {
  const out = {
    name: null,
    cwd: process.cwd(),
    print: false,
    scout: false,
    model: null,
    modelParams: [],
    timeoutMs: null,
    conversationId: null,
    runId: null,
    selfTest: false,
    allowedTools: null,
    disallowedTools: null,
    sandbox: false,
    autoReview: false,
    promptArgs: [],
  };
  const args = argv.slice(2);
  for (let i = 0; i < args.length; i++) {
    const arg = args[i];
    if (arg === "--") {
      out.promptArgs.push(...args.slice(i + 1));
      break;
    }
    if (arg === "--self-test") out.selfTest = true;
    else if (arg === "--print" || arg === "-p") out.print = true;
    else if (arg === "--scout") out.scout = true;
    else if (arg === "--sandbox") out.sandbox = true;
    else if (arg === "--auto-review") out.autoReview = true;
    else if (arg === "--name") out.name = takeValue(args, i++, "--name");
    else if (arg === "--cwd") out.cwd = takeValue(args, i++, "--cwd");
    else if (arg === "--model") out.model = takeValue(args, i++, "--model");
    else if (arg === "--model-param") out.modelParams.push(takeValue(args, i++, "--model-param"));
    else if (arg === "--timeout") out.timeoutMs = parseTimeoutMs(takeValue(args, i++, "--timeout"));
    else if (arg === "--conversation-id") out.conversationId = takeValue(args, i++, "--conversation-id");
    else if (arg === "--run-id") out.runId = takeValue(args, i++, "--run-id");
    else if (arg === "--allowed-tools") out.allowedTools = takeValue(args, i++, "--allowed-tools");
    else if (arg === "--disallowed-tools") out.disallowedTools = takeValue(args, i++, "--disallowed-tools");
    else if (arg.startsWith("--name=")) out.name = arg.slice(7);
    else if (arg.startsWith("--cwd=")) out.cwd = arg.slice(6);
    else if (arg.startsWith("--model=")) out.model = arg.slice(8);
    else if (arg.startsWith("--model-param=")) out.modelParams.push(arg.slice(14));
    else if (arg.startsWith("--timeout=")) out.timeoutMs = parseTimeoutMs(arg.slice(10));
    else if (arg.startsWith("--conversation-id=")) out.conversationId = arg.slice(18);
    else if (arg.startsWith("--run-id=")) out.runId = arg.slice(9);
    else if (arg.startsWith("--allowed-tools=")) out.allowedTools = arg.slice(16);
    else if (arg.startsWith("--disallowed-tools=")) out.disallowedTools = arg.slice(19);
    else out.promptArgs.push(arg);
  }
  return out;
}

function fail(message, code = "ERR_PRECONDITION") {
  const err = new Error(message);
  err.exitCode = 2;
  err.code = code;
  return err;
}

function requireModel(opts) {
  if (opts.model && String(opts.model).trim()) return;
  throw fail(
    "blocked: --model is required (pass --model <id>; no harness default)",
    "ERR_MODEL_REQUIRED",
  );
}

function modelSelection(opts) {
  const params = opts.modelParams.map((raw) => {
    const eq = raw.indexOf("=");
    if (eq <= 0 || eq === raw.length - 1) {
      throw fail(
        `--model-param must be id=value, got ${raw}`,
        "ERR_MODEL_PARAM",
      );
    }
    return { id: raw.slice(0, eq), value: raw.slice(eq + 1) };
  });
  if (opts.model === "auto-smart" && !params.some((param) => param.id === "optimize_for")) {
    throw fail(
      "auto-smart requires --model-param optimize_for=cost|balanced|intelligence",
      "ERR_ROUTER_PARAM",
    );
  }
  return params.length ? { id: opts.model, params } : { id: opts.model };
}

function toolOptions(opts) {
  if (opts.scout && (opts.allowedTools || opts.disallowedTools)) {
    throw fail(
      "--scout already sets a read-only tool list; do not combine it with --allowed-tools or --disallowed-tools",
      "ERR_SCOUT_TOOLS",
    );
  }
  if (opts.scout) return { tools: SCOUT_TOOLS.slice() };
  const out = {};
  if (opts.allowedTools) out.tools = splitCsv(opts.allowedTools);
  if (opts.disallowedTools) out.disallowedTools = splitCsv(opts.disallowedTools);
  return out;
}

function nodeSatisfies(version) {
  const parts = String(version).split(".").map((part) => Number(part) || 0);
  for (let i = 0; i < MIN_NODE.length; i++) {
    const got = parts[i] || 0;
    if (got > MIN_NODE[i]) return true;
    if (got < MIN_NODE[i]) return false;
  }
  return true;
}

function assertRuntime() {
  if (!nodeSatisfies(process.versions.node)) {
    throw fail(
      `Node ${process.versions.node} is too old. @cursor/sdk requires Node >= 22.13.`,
      "ERR_NODE",
    );
  }
}

function authPresent() {
  if (process.env.CURSOR_API_KEY && process.env.CURSOR_API_KEY.trim()) return "CURSOR_API_KEY";
  const stored = join(homedir(), ".cursor", "sdk", "auth.json");
  try {
    if (existsSync(stored) && statSync(stored).size > 0) return "auth.json";
  } catch {
    return null;
  }
  return null;
}

function assertAuth() {
  if (authPresent()) return;
  throw fail(
    "blocked: set CURSOR_API_KEY or run Cursor.auth.login() once so ~/.cursor/sdk/auth.json exists. Do not paste the key into chat.",
    "ERR_AUTH",
  );
}

function promptText(opts) {
  const job = opts.promptArgs.join(" ").trim();
  if (!job) throw fail("blocked: prompt is empty", "ERR_PROMPT");
  let contract = "";
  if (existsSync(WORKER_CONTRACT)) contract = readFileSync(WORKER_CONTRACT, "utf8").trim();
  if (!contract) return job;
  return `${contract}\n\n---\n\n${job}`;
}

function assistantText(event) {
  const content = event?.message?.content;
  if (!Array.isArray(content)) return "";
  return content
    .filter((block) => block && block.type === "text" && typeof block.text === "string")
    .map((block) => block.text)
    .join("");
}

async function loadSdk() {
  const manifest = join(SKILL_DIR, "package.json");
  if (!existsSync(manifest)) {
    throw fail(`missing ${manifest}`, "ERR_SDK_MISSING");
  }
  let entry;
  try {
    entry = createRequire(manifest).resolve("@cursor/sdk");
  } catch (err) {
    throw fail(
      `Install the SDK in the harness folder: cd "${SKILL_DIR}" && npm install. ${err.message}`,
      "ERR_SDK_MISSING",
    );
  }
  return import(pathToFileURL(entry).href);
}

function emptyState(meta) {
  return {
    schemaVersion: SCHEMA_VERSION,
    jobName: meta.jobName,
    runId: meta.runId,
    runDir: meta.runDir,
    backend: "cursor-sdk",
    print: Boolean(meta.print),
    lifecycle: "starting",
    processAlive: true,
    pid: process.pid,
    lastEventType: null,
    lastEventAt: null,
    watcherUpdatedAt: nowIso(),
    current: null,
    lastError: null,
    sessionId: null,
    requestId: null,
    totalCostUsd: null,
    numTurns: null,
    tokenUsage: null,
    exitCode: null,
    timedOut: false,
    timeoutMs: meta.timeoutMs ?? null,
  };
}

function buildReport(state, summaryText) {
  const summary = typeof summaryText === "string" ? summaryText.trim() : "";
  const extracted = Boolean(summary);
  const workerStatus = parseWorkerStatus(summary);
  const reportValid = workerStatus != null;
  let errorMessage = state.lastError;
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
    backend: "cursor-sdk",
    lifecycle: state.lifecycle,
    exitCode: state.exitCode,
    timedOut: Boolean(state.timedOut),
    timeoutMs: state.timeoutMs ?? null,
    summaryExtracted: extracted,
    summary: extracted ? clip(summary, SUMMARY_MAX) : null,
    workerStatus,
    reportValid,
    errorMessage: clip(errorMessage, ERROR_MAX),
    totalCostUsd: state.totalCostUsd ?? null,
    numTurns: state.numTurns ?? null,
    sessionId: state.sessionId ?? null,
    requestId: state.requestId ?? null,
    tokenUsage: state.tokenUsage ?? null,
  };
}

function noteEvent(state, event) {
  state.lastEventType = event?.type || null;
  state.lastEventAt = nowIso();
  if (event?.type === "tool_call") {
    state.current = { kind: "tool", name: event.name || "unknown", status: event.status || null };
  } else if (event?.type === "assistant") {
    state.current = { kind: "writing" };
  } else if (event?.type === "usage") {
    state.numTurns = (state.numTurns || 0) + 1;
    state.current = null;
  }
  state.watcherUpdatedAt = nowIso();
}

async function runJob(opts) {
  assertRuntime();
  assertAuth();
  const model = modelSelection(opts);
  const tools = toolOptions(opts);
  const prompt = promptText(opts);
  const cwd = opts.cwd;
  const jobName = sanitizeName(opts.name || "job");
  const runId = opts.runId || makeRunId();
  const runDir = join(cwd, ".agent", "cursor", jobName, runId);
  mkdirSync(runDir, { recursive: true });
  const paths = {
    status: join(runDir, "status.json"),
    report: join(runDir, "report.json"),
    events: join(runDir, "events.jsonl"),
  };
  const state = emptyState({ jobName, runId, runDir, print: opts.print, timeoutMs: opts.timeoutMs });
  const writeStatus = () => writeAtomic(paths.status, state);
  writeStatus();
  writeAtomic(join(cwd, ".agent", "cursor", jobName, "latest.json"), { runId, runDir });
  process.stdout.write(`RUN_DIR=${runDir}\nSTATUS_FILE=${paths.status}\n`);

  let agent = null;
  let summary = null;
  const heartbeat = setInterval(writeStatus, HEARTBEAT_MS);
  heartbeat.unref?.();
  try {
    const sdk = await loadSdk();
    const { Agent, JsonlLocalAgentStore } = sdk;
    if (!Agent || !JsonlLocalAgentStore) {
      throw new Error("ERR_SDK_SHAPE: @cursor/sdk did not export Agent and JsonlLocalAgentStore");
    }
    const store = new JsonlLocalAgentStore(join(cwd, ".agent", "cursor", "_store"));
    const local = {
      cwd,
      settingSources: DEFAULT_SETTING_SOURCES,
      store,
      sandboxOptions: { enabled: Boolean(opts.sandbox) },
      autoReview: Boolean(opts.autoReview),
    };
    const createOptions = {
      name: jobName,
      model,
      mode: opts.scout ? "plan" : "agent",
      local,
      ...tools,
    };
    if (opts.conversationId) {
      agent = await Agent.resume(opts.conversationId, createOptions);
    } else {
      agent = await Agent.create(createOptions);
    }
    state.sessionId = agent.agentId;
    state.lifecycle = "running";
    writeStatus();

    const run = await agent.send(prompt);
    state.requestId = run.requestId || null;
    let timer = null;
    const timeout = new Promise((resolve) => {
      if (!(typeof opts.timeoutMs === "number" && opts.timeoutMs > 0)) return;
      timer = setTimeout(() => {
        state.timedOut = true;
        state.lifecycle = "timed_out";
        state.lastError = `timeout after ${opts.timeoutMs}ms`;
        writeStatus();
        resolve({ timedOut: true });
      }, opts.timeoutMs);
      timer.unref?.();
    });

    const streamed = (async () => {
      let lastAssistant = "";
      for await (const event of run.stream()) {
        appendFileSync(paths.events, `${JSON.stringify(event)}\n`);
        noteEvent(state, event);
        if (event.type === "assistant") {
          const text = assistantText(event);
          if (text) lastAssistant = text;
        }
      }
      const result = await run.wait();
      return { result, lastAssistant };
    })();

    const winner = await Promise.race([
      streamed.then((value) => ({ value })),
      timeout,
    ]);
    if (timer) clearTimeout(timer);

    if (winner && winner.timedOut) {
      try {
        await run.cancel();
      } catch (err) {
        state.lastError = `${state.lastError}; cancel failed: ${err.message}`;
      }
      await streamed.catch((err) => {
        state.lastError = `${state.lastError}; stream ended: ${err.message}`;
      });
      state.exitCode = 1;
    } else {
      const { result, lastAssistant } = winner.value;
      state.requestId = result.requestId || state.requestId;
      state.tokenUsage = result.usage || null;
      summary = (typeof result.result === "string" && result.result.trim()) || lastAssistant || null;
      if (result.status === "finished") {
        state.lifecycle = "completed";
        state.exitCode = 0;
      } else if (result.status === "cancelled") {
        state.lifecycle = state.timedOut ? "timed_out" : "terminated";
        state.exitCode = 1;
        state.lastError = state.lastError || result.error?.message || "cancelled";
      } else {
        state.lifecycle = "failed";
        state.exitCode = 1;
        state.lastError = result.error?.message || `run status ${result.status}`;
      }
      try {
        const usage = await agent.getUsage();
        if (usage?.cost && Number.isFinite(usage.cost.chargedCents)) {
          state.totalCostUsd = usage.cost.chargedCents / 100;
        }
      } catch {
        // Local billed usage is account-gated. Token counts on the run still stand.
      }
    }
  } catch (err) {
    if (err.exitCode === 2) throw err;
    state.lifecycle = "failed";
    state.exitCode = 1;
    state.lastError = err.message || String(err);
  } finally {
    clearInterval(heartbeat);
    state.processAlive = false;
    state.current = null;
    if (agent) {
      try {
        await agent[Symbol.asyncDispose]();
      } catch (err) {
        state.lastError = state.lastError
          ? `${state.lastError}; dispose failed: ${err.message}`
          : `dispose failed: ${err.message}`;
      }
    }
    writeStatus();
    const report = buildReport(state, summary);
    writeAtomic(paths.report, report);
    process.stdout.write(`LIFECYCLE=${state.lifecycle}\nREPORT_FILE=${paths.report}\n`);
  }
  return state.exitCode === 0 ? 0 : 1;
}

function assert(cond, message) {
  if (!cond) throw new Error(`self-test failed: ${message}`);
}

function selfTest() {
  assert(nodeSatisfies("22.13.0"), "22.13.0 is new enough");
  assert(nodeSatisfies("22.13.1"), "patch above minimum passes");
  assert(nodeSatisfies("24.0.0"), "newer major passes");
  assert(!nodeSatisfies("22.12.9"), "22.12 is too old");
  assert(!nodeSatisfies("20.18.0"), "node 20 is too old");
  assert(parseWorkerStatus("STATUS: ok") === "ok", "STATUS ok");
  assert(parseWorkerStatus("note\nSTATUS: stuck\n") === "stuck", "STATUS stuck");
  assert(parseWorkerStatus("no status") === null, "missing status");

  const opts = parseArgs([
    "node",
    "cursor-spawn.mjs",
    "--name",
    "fix-auth",
    "--cwd",
    "/tmp/repo",
    "--model",
    "composer-2.5",
    "--timeout",
    "30",
    "--",
    "Fix the login bug",
  ]);
  assert(opts.name === "fix-auth", "name");
  assert(opts.cwd === "/tmp/repo", "cwd");
  assert(opts.model === "composer-2.5", "model");
  assert(opts.timeoutMs === 30000, "timeout seconds");
  assert(opts.promptArgs.join(" ") === "Fix the login bug", "prompt");
  assert(modelSelection(opts).id === "composer-2.5", "model selection");

  const router = parseArgs([
    "node",
    "cursor-spawn.mjs",
    "--model",
    "auto-smart",
    "--model-param",
    "optimize_for=balanced",
    "--",
    "hi",
  ]);
  const selection = modelSelection(router);
  assert(selection.params[0].value === "balanced", "router param");

  let threw = false;
  try {
    modelSelection(parseArgs(["node", "cursor-spawn.mjs", "--model", "auto-smart", "--", "hi"]));
  } catch (err) {
    threw = err.code === "ERR_ROUTER_PARAM";
  }
  assert(threw, "auto-smart without optimize_for is rejected");

  threw = false;
  try {
    requireModel(parseArgs(["node", "cursor-spawn.mjs", "--", "hi"]));
  } catch (err) {
    threw = err.code === "ERR_MODEL_REQUIRED";
  }
  assert(threw, "missing model is rejected");

  const scout = parseArgs(["node", "cursor-spawn.mjs", "--model", "composer-2.5", "--scout", "--", "look"]);
  assert(toolOptions(scout).tools.join() === SCOUT_TOOLS.join(), "scout tools");

  threw = false;
  try {
    toolOptions(parseArgs([
      "node",
      "cursor-spawn.mjs",
      "--model",
      "composer-2.5",
      "--scout",
      "--allowed-tools",
      "read",
      "--",
      "look",
    ]));
  } catch (err) {
    threw = err.code === "ERR_SCOUT_TOOLS";
  }
  assert(threw, "scout plus allowed-tools is rejected");

  const state = emptyState({ jobName: "j", runId: "r", runDir: "/tmp/r", timeoutMs: null });
  state.lifecycle = "completed";
  const bad = buildReport(state, "done but no status");
  assert(bad.reportValid === false && bad.workerStatus === null, "invalid report");
  const good = buildReport(state, "STATUS: blocked\nNeed a spec");
  assert(good.workerStatus === "blocked" && good.reportValid === true, "valid report");
  process.stdout.write("SELFTEST: ok\n");
}

const opts = parseArgs(process.argv);
if (opts.selfTest) {
  try {
    selfTest();
  } catch (err) {
    process.stderr.write(`${err.message}\n`);
    process.exit(1);
  }
} else {
  runJob(opts)
    .then((code) => process.exit(code))
    .catch((err) => {
      process.stderr.write(`${err.message}\n`);
      process.exit(err.exitCode || 1);
    });
}
