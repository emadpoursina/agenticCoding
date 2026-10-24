#!/usr/bin/env python3
"""Cursor-facing Antigravity SDK worker launcher.

Streams stay on disk (events.jsonl). Cursor polls status.json.
Uses google.antigravity Agent — not the agy TUI, not npm antigravity-sdk.
"""
from __future__ import annotations

import argparse
import asyncio
import inspect
import json
import os
import re
import signal
import sys
import traceback
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

SCHEMA_VERSION = 1
SKILL_DIR = Path(__file__).resolve().parent
WORKER_CONTRACT = SKILL_DIR / "worker-contract.md"
HEARTBEAT_S = 2.0
ERROR_MAX = 240
SUMMARY_MAX = 100_000
STDERR_TAIL_MAX = 2000
WORKER_STATUS_RE = re.compile(r"\bSTATUS\s*[:=]?\s*(ok|stuck|blocked)\b", re.I)


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def clip(s: str | None, n: int) -> str | None:
    if s is None:
        return None
    t = str(s)
    return t if len(t) <= n else t[:n] + "…"


def sanitize_name(name: str) -> str:
    s = str(name).strip()
    if not s or "/" in s or "\\" in s or s in (".", ".."):
        raise SystemExit(f"invalid --name: {name}")
    if not re.fullmatch(r"[\w.-]+", s):
        raise SystemExit(f"--name must be letters, digits, _ . - (got {name})")
    return s


def make_run_id() -> str:
    t = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H-%M-%S-%f")[:-3] + "Z"
    return f"{t}_{uuid.uuid4().hex[:6]}"


def parse_timeout_ms(raw: str | None) -> int | None:
    if raw is None or raw == "":
        return None
    s = str(raw).strip()
    m = re.fullmatch(r"(\d+(?:\.\d+)?)\s*ms", s, re.I)
    if m:
        n = float(m.group(1))
        if n <= 0:
            raise SystemExit(f"invalid --timeout: {raw}")
        return int(n)
    try:
        sec = float(s)
    except ValueError as exc:
        raise SystemExit(f"invalid --timeout: {raw}") from exc
    if sec <= 0:
        raise SystemExit(f"invalid --timeout: {raw}")
    return int(sec * 1000)


def parse_worker_status(text: str | None) -> str | None:
    if not text:
        return None
    m = WORKER_STATUS_RE.search(text)
    return m.group(1).lower() if m else None


def write_atomic(path: Path, obj: Any) -> None:
    tmp = path.with_name(f"{path.name}.{os.getpid()}.tmp")
    tmp.write_text(json.dumps(obj, indent=2) + "\n", encoding="utf-8")
    tmp.replace(path)


def empty_state(meta: dict[str, Any]) -> dict[str, Any]:
    return {
        "schemaVersion": SCHEMA_VERSION,
        "jobName": meta["jobName"],
        "runId": meta["runId"],
        "runDir": meta["runDir"],
        "backend": "antigravity-sdk",
        "lifecycle": "starting",
        "processAlive": False,
        "pid": os.getpid(),
        "lastEventType": None,
        "lastEventAt": None,
        "watcherUpdatedAt": now_iso(),
        "current": None,
        "currentAgeMs": None,
        "quietMs": None,
        "lastError": None,
        "sessionId": None,
        "exitCode": None,
        "signal": None,
        "timedOut": False,
        "timeoutMs": meta.get("timeoutMs"),
        "_lastAssistant": None,
    }


def enrich(state: dict[str, Any]) -> dict[str, Any]:
    t = datetime.now(timezone.utc)
    state["watcherUpdatedAt"] = t.isoformat()
    cur = state.get("current")
    if cur and cur.get("startedAt"):
        started = datetime.fromisoformat(cur["startedAt"])
        state["currentAgeMs"] = int((t - started).total_seconds() * 1000)
    else:
        state["currentAgeMs"] = None
    if state.get("lastEventAt"):
        last = datetime.fromisoformat(state["lastEventAt"])
        state["quietMs"] = int((t - last).total_seconds() * 1000)
    else:
        state["quietMs"] = None
    return state


def public_status(state: dict[str, Any]) -> dict[str, Any]:
    out = {k: v for k, v in enrich(dict(state)).items() if k != "_lastAssistant"}
    return out


def set_current(state: dict[str, Any], current: dict[str, Any] | None) -> None:
    if current is None:
        state["current"] = None
        return
    cur = dict(current)
    cur.setdefault("startedAt", now_iso())
    state["current"] = cur


def note_error(state: dict[str, Any], msg: str) -> None:
    state["lastError"] = clip(msg, ERROR_MAX)


def emit_event(events: Path, state: dict[str, Any], ev: dict[str, Any]) -> None:
    ev = {"ts": now_iso(), **ev}
    with events.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(ev) + "\n")
    state["lastEventType"] = ev.get("event")
    state["lastEventAt"] = ev["ts"]


def build_report(state: dict[str, Any], extra: dict[str, Any]) -> dict[str, Any]:
    a = state.get("_lastAssistant") or {}
    summary = extra.get("stdoutText") or a.get("text")
    if isinstance(summary, str):
        summary = summary.strip() or None
    extracted = bool(summary)
    worker_status = parse_worker_status(summary)
    report_valid = worker_status is not None
    error_message = extra.get("spawnError") or state.get("lastError")
    if state.get("timedOut") and not error_message:
        error_message = "timeout"
    if not report_valid and state.get("lifecycle") == "completed":
        missing = "missing worker STATUS (ok|stuck|blocked)"
        error_message = f"{error_message}; {missing}" if error_message else missing
    return {
        "schemaVersion": SCHEMA_VERSION,
        "jobName": state["jobName"],
        "runId": state["runId"],
        "runDir": state["runDir"],
        "backend": "antigravity-sdk",
        "lifecycle": state["lifecycle"],
        "exitCode": state.get("exitCode"),
        "signal": state.get("signal"),
        "timedOut": bool(state.get("timedOut")),
        "timeoutMs": state.get("timeoutMs"),
        "summaryExtracted": extracted,
        "summary": clip(summary, SUMMARY_MAX) if extracted else None,
        "workerStatus": worker_status,
        "reportValid": report_valid,
        "errorMessage": clip(error_message, ERROR_MAX),
        "stderrTail": clip(extra.get("stderrTail"), STDERR_TAIL_MAX),
    }


def parse_args(argv: list[str]) -> argparse.Namespace:
    pre, post = argv, []
    if "--" in argv:
        i = argv.index("--")
        pre, post = argv[:i], argv[i + 1 :]
    p = argparse.ArgumentParser(prog="agy-spawn.py", add_help=True)
    p.add_argument("--name")
    p.add_argument("--cwd", default=os.getcwd())
    p.add_argument("--model")
    p.add_argument("--effort")
    p.add_argument("--timeout")
    p.add_argument("--run-id")
    p.add_argument("--conversation-id")
    p.add_argument("--print", "-p", action="store_true")
    p.add_argument("--scout", action="store_true")
    p.add_argument("--vertex", action="store_true")
    p.add_argument("--self-test", action="store_true")
    p.add_argument("prompt_words", nargs="*", default=[])
    ns = p.parse_args(pre)
    ns.prompt_parts = list(ns.prompt_words) + post
    ns.timeout_ms = parse_timeout_ms(ns.timeout)
    return ns


def config_kwargs(cls: Any, wanted: dict[str, Any]) -> dict[str, Any]:
    try:
        params = inspect.signature(cls).parameters
    except (TypeError, ValueError):
        return {k: v for k, v in wanted.items() if v is not None}
    out = {}
    for key, val in wanted.items():
        if val is None:
            continue
        if key in params or any(p.kind == inspect.Parameter.VAR_KEYWORD for p in params.values()):
            out[key] = val
    return out


def load_contract() -> str:
    if not WORKER_CONTRACT.is_file():
        raise SystemExit(f"missing worker contract: {WORKER_CONTRACT}")
    return WORKER_CONTRACT.read_text(encoding="utf-8").strip()


async def run_agent(ns: argparse.Namespace, state: dict[str, Any], paths: dict[str, Path]) -> None:
    try:
        from google.antigravity import Agent, LocalAgentConfig
        from google.antigravity.hooks import policy
    except ImportError as exc:
        raise RuntimeError(
            "google.antigravity is not importable; install the PyPI package "
            "`google-antigravity` (wheel includes localharness)"
        ) from exc

    try:
        from google.antigravity import CapabilitiesConfig
    except ImportError:
        from google.antigravity.types import CapabilitiesConfig  # type: ignore

    from google.antigravity.types import BuiltinTools

    cwd = str(Path(ns.cwd).resolve())
    conversation_id = ns.conversation_id or str(uuid.uuid4())
    save_dir = str(paths["runDir"] / "session")
    Path(save_dir).mkdir(parents=True, exist_ok=True)
    state["sessionId"] = conversation_id

    cap_wanted: dict[str, Any] = {"enable_subagents": False}
    if ns.scout:
        cap_wanted["enabled_tools"] = BuiltinTools.read_only()
    capabilities = CapabilitiesConfig(**config_kwargs(CapabilitiesConfig, cap_wanted))

    wanted = {
        "model": ns.model,
        "system_instructions": load_contract(),
        "workspaces": [cwd],
        "capabilities": capabilities,
        "policies": [] if ns.scout else [policy.allow_all()],
        "save_dir": save_dir,
        "conversation_id": conversation_id,
        "vertex": True if ns.vertex else None,
    }
    if ns.effort:
        wanted["effort"] = ns.effort
    cfg = LocalAgentConfig(**config_kwargs(LocalAgentConfig, wanted))

    prompt = " ".join(ns.prompt_parts).strip()
    if not prompt:
        raise RuntimeError("prompt is required after --")

    emit_event(paths["events"], state, {"event": "agent_start"})
    set_current(state, {"kind": "model"})
    state["lifecycle"] = "running"
    write_atomic(paths["status"], public_status(state))

    async with Agent(cfg) as agent:
        response = await agent.chat(prompt)

        async def thoughts() -> None:
            try:
                stream = response.thoughts
            except Exception:
                return
            async for _token in stream:
                set_current(state, {"kind": "thinking"})
                emit_event(paths["events"], state, {"event": "thought"})

        async def tools() -> None:
            try:
                stream = response.tool_calls
            except Exception:
                return
            async for call in stream:
                name = getattr(call, "name", None) or "unknown"
                set_current(state, {"kind": "tool", "name": name})
                emit_event(paths["events"], state, {"event": "tool_call", "name": name})

        await asyncio.gather(thoughts(), tools())
        text = await response.text()

    state["_lastAssistant"] = {"text": text or ""}
    emit_event(paths["events"], state, {"event": "agent_end"})
    set_current(state, None)


async def heartbeat(state: dict[str, Any], status_path: Path, stop: asyncio.Event) -> None:
    while not stop.is_set():
        write_atomic(status_path, public_status(state))
        try:
            await asyncio.wait_for(stop.wait(), timeout=HEARTBEAT_S)
        except asyncio.TimeoutError:
            pass


async def run_job(ns: argparse.Namespace) -> int:
    if not ns.model or not str(ns.model).strip():
        print(
            "blocked: --model is required (no harness default)",
            file=sys.stderr,
        )
        return 2
    job_name = sanitize_name(ns.name or "")
    if not ns.name:
        print("blocked: --name is required", file=sys.stderr)
        return 2

    cwd = Path(ns.cwd).resolve()
    run_id = ns.run_id or make_run_id()
    run_dir = cwd / ".agent" / "antigravity" / job_name / run_id
    run_dir.mkdir(parents=True, exist_ok=True)
    paths = {
        "runDir": run_dir,
        "status": run_dir / "status.json",
        "report": run_dir / "report.json",
        "events": run_dir / "events.jsonl",
        "stderr": run_dir / "stderr.log",
        "latest": cwd / ".agent" / "antigravity" / job_name / "latest.json",
    }
    paths["events"].write_text("", encoding="utf-8")
    paths["stderr"].write_text("", encoding="utf-8")
    write_atomic(
        paths["latest"],
        {
            "jobName": job_name,
            "runId": run_id,
            "runDir": str(run_dir),
            "status": str(paths["status"]),
        },
    )

    state = empty_state(
        {
            "jobName": job_name,
            "runId": run_id,
            "runDir": str(run_dir),
            "timeoutMs": ns.timeout_ms,
        }
    )
    write_atomic(paths["status"], public_status(state))
    sys.stdout.write(f"RUN_DIR={run_dir}\nSTATUS_FILE={paths['status']}\n")
    sys.stdout.flush()

    state["processAlive"] = True
    stop = asyncio.Event()
    beat = asyncio.create_task(heartbeat(state, paths["status"], stop))
    spawn_error = None
    timed_out = False

    def _on_signal(signum: int, _frame: Any) -> None:
        state["signal"] = signal.Signals(signum).name
        raise KeyboardInterrupt

    signal.signal(signal.SIGTERM, _on_signal)
    signal.signal(signal.SIGINT, _on_signal)

    try:
        coro = run_agent(ns, state, paths)
        if ns.timeout_ms:
            await asyncio.wait_for(coro, timeout=ns.timeout_ms / 1000)
        else:
            await coro
        state["lifecycle"] = "completed"
        state["exitCode"] = 0
    except asyncio.TimeoutError:
        timed_out = True
        state["timedOut"] = True
        state["lifecycle"] = "timed_out"
        state["exitCode"] = 1
        note_error(state, f"timeout after {ns.timeout_ms}ms")
        spawn_error = "timeout"
    except KeyboardInterrupt:
        state["lifecycle"] = "terminated"
        state["exitCode"] = 1
    except Exception as exc:  # noqa: BLE001 — surface SDK/spawn failures in report.json
        spawn_error = str(exc)
        state["lifecycle"] = "failed"
        state["exitCode"] = 1
        note_error(state, spawn_error)
        paths["stderr"].write_text(traceback.format_exc(), encoding="utf-8")
    finally:
        state["processAlive"] = False
        set_current(state, None)
        stop.set()
        await beat
        write_atomic(paths["status"], public_status(state))
        report = build_report(
            state,
            {
                "spawnError": spawn_error,
                "stderrTail": paths["stderr"].read_text(encoding="utf-8")[-STDERR_TAIL_MAX:],
            },
        )
        write_atomic(paths["report"], report)
        sys.stdout.write(f"LIFECYCLE={state['lifecycle']}\nREPORT_FILE={paths['report']}\n")
        sys.stdout.flush()

    if timed_out:
        return 1
    return 0 if state["lifecycle"] == "completed" else 1


def self_test() -> int:
    assert parse_worker_status("STATUS: ok\nSUMMARY hi") == "ok"
    assert parse_worker_status("nope") is None
    assert parse_timeout_ms("2") == 2000
    assert parse_timeout_ms("250ms") == 250
    assert sanitize_name("speckit-ready") == "speckit-ready"
    state = empty_state(
        {"jobName": "self", "runId": "r1", "runDir": "/tmp/agy-harness-self", "timeoutMs": None}
    )
    report = build_report(state | {"lifecycle": "completed", "_lastAssistant": {"text": "STATUS: ok"}}, {})
    assert report["reportValid"] is True
    assert report["workerStatus"] == "ok"
    print("SELFTEST: ok")
    return 0


def main(argv: list[str] | None = None) -> int:
    ns = parse_args(sys.argv[1:] if argv is None else argv)
    if ns.self_test:
        return self_test()
    return asyncio.run(run_job(ns))


if __name__ == "__main__":
    raise SystemExit(main())
