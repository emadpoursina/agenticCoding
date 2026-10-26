#!/usr/bin/env python3
"""Cursor-facing Antigravity CLI worker launcher.

Spawns official headless agy -p (never the TUI, never bare agy).
Streams stay on disk (events.jsonl for stream-json jobs). Parent polls status.json.
Ready checks agy on PATH + agy models. The Python SDK is not the worker runtime.
Wrapper --print means CLI text mode; default is --output-format stream-json.
Never mix -p with --input-format stream-json.
"""
from __future__ import annotations

import argparse
import json
import math
import os
import re
import signal
import subprocess
import sys
import tempfile
import threading
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
GRACEFUL_KILL_S = 2.0
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
        "backend": "agy-cli",
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
    return enrich(dict(state))


def set_current(state: dict[str, Any], current: dict[str, Any] | None) -> None:
    if current is None:
        state["current"] = None
        return
    cur = dict(current)
    cur.setdefault("startedAt", now_iso())
    state["current"] = cur


def note_error(state: dict[str, Any], msg: str) -> None:
    state["lastError"] = clip(msg, ERROR_MAX)


def load_contract() -> str:
    if not WORKER_CONTRACT.is_file():
        raise SystemExit(f"missing worker contract: {WORKER_CONTRACT}")
    return WORKER_CONTRACT.read_text(encoding="utf-8").strip()


def reconstruct_assistant_text(events_path: Path) -> str | None:
    if not events_path.exists():
        return None
    try:
        content = events_path.read_text(encoding="utf-8")
    except Exception:
        return None
    lines = content.splitlines()
    last_result_response: str | None = None
    deltas: list[str] = []
    for line in lines:
        line = line.strip()
        if not line:
            continue
        try:
            ev = json.loads(line)
        except Exception:
            continue
        if not isinstance(ev, dict):
            continue
        ev_type = ev.get("event")
        if ev_type == "result":
            res = ev.get("result")
            if isinstance(res, dict) and isinstance(res.get("response"), str):
                last_result_response = res["response"].strip()
            elif isinstance(ev.get("response"), str):
                last_result_response = ev["response"].strip()
        elif ev_type == "step_update":
            su = ev.get("step_update")
            step_type = ev.get("step_type")
            delta = ev.get("text_delta")
            if isinstance(su, dict):
                step_type = step_type or su.get("step_type")
                delta = delta or su.get("text_delta")
            if step_type == "agent_response" and isinstance(delta, str):
                deltas.append(delta)
    if last_result_response is not None:
        return last_result_response
    if deltas:
        return "".join(deltas).strip()
    return None


def build_report(state: dict[str, Any], extra: dict[str, Any]) -> dict[str, Any]:
    summary = extra.get("stdoutText")
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
        "backend": "agy-cli",
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
    p.add_argument("--print", "-p", dest="print_mode", action="store_true")
    p.add_argument("--scout", action="store_true")
    p.add_argument("--vertex", action="store_true")
    p.add_argument("--self-test", action="store_true")
    p.add_argument("prompt_words", nargs="*", default=[])
    ns = p.parse_args(pre)
    ns.prompt_parts = list(ns.prompt_words) + post
    ns.timeout_ms = parse_timeout_ms(ns.timeout)
    return ns


def build_agy_argv(ns: argparse.Namespace) -> list[str]:
    job_prompt = " ".join(ns.prompt_parts).strip()
    contract = load_contract()
    full_prompt = f"{contract}\n\n{job_prompt}" if contract else job_prompt

    cmd = ["agy", "-p", full_prompt]
    if ns.scout:
        cmd.extend(["--mode", "plan"])
    else:
        cmd.extend(["--mode", "accept-edits", "--dangerously-skip-permissions"])

    cmd.append("--disable-slash-commands")
    if ns.model:
        cmd.extend(["--model", str(ns.model)])
    if not ns.print_mode:
        cmd.extend(["--output-format", "stream-json"])
    if ns.effort:
        cmd.extend(["--effort", str(ns.effort)])
    if ns.timeout_ms is not None:
        sec = max(1, math.ceil(ns.timeout_ms / 1000.0))
        cmd.extend(["--print-timeout", f"{sec}s"])
    if ns.conversation_id:
        cmd.extend(["--conversation", str(ns.conversation_id)])
    return cmd


def check_skip_permissions_fail_closed(state: dict[str, Any], exit_code: int, stderr: str) -> None:
    """If installed agy rejects skip-permissions, finalize failed with no SDK fallback."""
    if exit_code != 0:
        state["lifecycle"] = "failed"
        state["exitCode"] = exit_code
        low = stderr.lower()
        if "dangerously-skip-permissions" in low:
            note_error(state, "dangerously-skip-permissions rejected by agy; fail closed")


def run_job(ns: argparse.Namespace) -> int:
    if not ns.model or not str(ns.model).strip():
        print("blocked: --model is required (no harness default)", file=sys.stderr)
        return 2
    if not ns.name:
        print("blocked: --name is required", file=sys.stderr)
        return 2
    job_name = sanitize_name(ns.name)
    prompt = " ".join(ns.prompt_parts).strip()
    if not prompt:
        print("blocked: prompt is required after --", file=sys.stderr)
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
    if ns.conversation_id:
        state["sessionId"] = ns.conversation_id
    write_atomic(paths["status"], public_status(state))
    sys.stdout.write(f"RUN_DIR={run_dir}\nSTATUS_FILE={paths['status']}\n")
    sys.stdout.flush()

    cmd = build_agy_argv(ns)
    spawn_error: str | None = None
    stdout_text_chunks: list[str] = []
    stderr_tail_chunks: list[str] = []
    child: subprocess.Popen[str] | None = None
    timed_out = False

    try:
        child = subprocess.Popen(
            cmd,
            stdin=subprocess.DEVNULL,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            cwd=str(cwd),
            text=True,
            bufsize=1,
        )
    except FileNotFoundError as exc:
        spawn_error = f"agy not on PATH: {exc}"
        state["lifecycle"] = "failed"
        state["exitCode"] = 127
        note_error(state, spawn_error)
    except Exception as exc:
        spawn_error = f"failed to start agy: {exc}"
        state["lifecycle"] = "failed"
        state["exitCode"] = 1
        note_error(state, spawn_error)

    if child is None:
        state["processAlive"] = False
        write_atomic(paths["status"], public_status(state))
        report = build_report(state, {"spawnError": spawn_error, "stderrTail": ""})
        write_atomic(paths["report"], report)
        sys.stdout.write(f"LIFECYCLE={state['lifecycle']}\nREPORT_FILE={paths['report']}\n")
        sys.stdout.flush()
        return 1

    state["processAlive"] = True
    state["lifecycle"] = "running"
    set_current(state, {"kind": "model"})
    write_atomic(paths["status"], public_status(state))

    def read_stderr() -> None:
        assert child and child.stderr
        with paths["stderr"].open("a", encoding="utf-8") as f:
            for line in child.stderr:
                f.write(line)
                f.flush()
                stderr_tail_chunks.append(line)
                if len(stderr_tail_chunks) > 50:
                    stderr_tail_chunks.pop(0)

    def read_stdout() -> None:
        assert child and child.stdout
        if ns.print_mode:
            for line in child.stdout:
                stdout_text_chunks.append(line)
        else:
            with paths["events"].open("a", encoding="utf-8") as f:
                for line in child.stdout:
                    f.write(line)
                    f.flush()
                    line_str = line.strip()
                    if not line_str:
                        continue
                    try:
                        ev = json.loads(line_str)
                    except Exception:
                        continue
                    if isinstance(ev, dict):
                        ev_type = ev.get("event")
                        state["lastEventType"] = ev_type
                        state["lastEventAt"] = now_iso()
                        if ev_type == "init":
                            set_current(state, {"kind": "model"})
                            if ev.get("conversation_id"):
                                state["sessionId"] = ev["conversation_id"]
                        elif ev_type == "step_update":
                            su = ev.get("step_update")
                            step_type = ev.get("step_type")
                            if isinstance(su, dict):
                                step_type = step_type or su.get("step_type")
                            if step_type == "tool":
                                name = (
                                    ev.get("tool_name")
                                    or (su.get("tool_name") if isinstance(su, dict) else None)
                                    or (su.get("name") if isinstance(su, dict) else None)
                                    or "tool"
                                )
                                set_current(state, {"kind": "tool", "name": name})
                            else:
                                set_current(state, {"kind": "model"})
                        elif ev_type == "result":
                            set_current(state, None)

    t_err = threading.Thread(target=read_stderr, daemon=True)
    t_out = threading.Thread(target=read_stdout, daemon=True)
    t_err.start()
    t_out.start()

    stop_heartbeat = threading.Event()

    def heartbeat_loop() -> None:
        while not stop_heartbeat.wait(HEARTBEAT_S):
            write_atomic(paths["status"], public_status(state))

    t_beat = threading.Thread(target=heartbeat_loop, daemon=True)
    t_beat.start()

    def kill_child(sig: signal.Signals, reason: str) -> None:
        nonlocal timed_out
        if child.poll() is not None:
            return
        if reason == "timeout":
            timed_out = True
            state["timedOut"] = True
            state["lifecycle"] = "timed_out"
            note_error(state, f"timeout after {state['timeoutMs']}ms")
        elif reason == "signal":
            state["lifecycle"] = "terminated"
        try:
            child.send_signal(sig)
        except ProcessLookupError:
            return

        def send_sigkill() -> None:
            if child.poll() is None:
                try:
                    child.kill()
                except ProcessLookupError:
                    pass

        grace = threading.Timer(GRACEFUL_KILL_S, send_sigkill)
        grace.daemon = True
        grace.start()

    timeout_timer: threading.Timer | None = None
    if ns.timeout_ms:
        timeout_timer = threading.Timer(
            ns.timeout_ms / 1000.0,
            lambda: kill_child(signal.SIGTERM, "timeout"),
        )
        timeout_timer.daemon = True
        timeout_timer.start()

    def sig_handler(signum: int, _frame: Any) -> None:
        state["signal"] = signal.Signals(signum).name
        kill_child(signal.SIGTERM, "signal")

    prev_sigterm = signal.signal(signal.SIGTERM, sig_handler)
    prev_sigint = signal.signal(signal.SIGINT, sig_handler)

    try:
        return_code = child.wait()
    finally:
        signal.signal(signal.SIGTERM, prev_sigterm)
        signal.signal(signal.SIGINT, prev_sigint)
        if timeout_timer:
            timeout_timer.cancel()
        t_err.join(timeout=2.0)
        t_out.join(timeout=2.0)
        stop_heartbeat.set()
        t_beat.join(timeout=2.0)

    state["exitCode"] = return_code
    state["processAlive"] = False
    set_current(state, None)

    stderr_tail = "".join(stderr_tail_chunks)

    if timed_out or state.get("timedOut"):
        state["lifecycle"] = "timed_out"
    elif state.get("signal"):
        state["lifecycle"] = "terminated"
    elif return_code == 0:
        state["lifecycle"] = "completed"
    else:
        state["lifecycle"] = "failed"
        check_skip_permissions_fail_closed(state, return_code, stderr_tail)

    if ns.print_mode:
        stdout_text = "".join(stdout_text_chunks).strip() or None
    else:
        stdout_text = reconstruct_assistant_text(paths["events"])

    report = build_report(
        state,
        {
            "stdoutText": stdout_text,
            "spawnError": spawn_error,
            "stderrTail": stderr_tail,
        },
    )
    write_atomic(paths["status"], public_status(state))
    write_atomic(paths["report"], report)
    sys.stdout.write(f"LIFECYCLE={state['lifecycle']}\nREPORT_FILE={paths['report']}\n")
    sys.stdout.flush()

    if timed_out or state.get("timedOut"):
        return 1
    return 0 if state["lifecycle"] == "completed" else 1


def self_test() -> int:
    assert parse_worker_status("STATUS: ok\nSUMMARY hi") == "ok"
    assert parse_worker_status("STATUS: stuck") == "stuck"
    assert parse_worker_status("STATUS: blocked") == "blocked"
    assert parse_worker_status("nope") is None
    assert parse_timeout_ms("2") == 2000
    assert parse_timeout_ms("250ms") == 250
    assert parse_timeout_ms(None) is None
    assert sanitize_name("speckit-ready") == "speckit-ready"

    # Missing --model returns exit 2 and does not spawn
    ns_no_model = parse_args(["--name", "test-job"])
    assert run_job(ns_no_model) == 2

    # TF-1: Short print job shape (wrapper --print without --scout)
    ns1 = parse_args(["--model", "gemini-2.5", "--name", "job1", "--print", "--", "hello"])
    argv1 = build_agy_argv(ns1)
    assert argv1[0] == "agy"
    assert "-p" in argv1
    assert "--disable-slash-commands" in argv1
    assert "--mode" in argv1 and argv1[argv1.index("--mode") + 1] == "accept-edits"
    assert "--dangerously-skip-permissions" in argv1
    assert "--output-format" not in argv1
    assert "--input-format" not in argv1
    assert "--prompt-interactive" not in argv1 and "-i" not in argv1
    contract_text = load_contract()
    p1 = argv1[argv1.index("-p") + 1]
    assert p1.startswith(contract_text)
    assert p1.endswith("hello")

    # TF-2: Long stream-json job shape (default without wrapper --print)
    ns2 = parse_args(["--model", "gemini-2.5", "--name", "job2", "--", "long job"])
    argv2 = build_agy_argv(ns2)
    assert "-p" in argv2
    assert "--output-format" in argv2 and argv2[argv2.index("--output-format") + 1] == "stream-json"
    assert "--input-format" not in argv2
    assert "--prompt-interactive" not in argv2 and "-i" not in argv2

    # TF-3: Scout vs edit
    ns3 = parse_args(["--model", "gemini-2.5", "--name", "job3", "--scout", "--", "plan job"])
    argv3 = build_agy_argv(ns3)
    assert "--mode" in argv3 and argv3[argv3.index("--mode") + 1] == "plan"
    assert "--dangerously-skip-permissions" not in argv3

    # Fail-closed helper for rejected skip-permissions
    st_fc = empty_state({"jobName": "fc", "runId": "r", "runDir": "/tmp", "timeoutMs": None})
    st_fc["lifecycle"] = "running"
    check_skip_permissions_fail_closed(st_fc, 1, "unknown flag: --dangerously-skip-permissions")
    assert st_fc["lifecycle"] == "failed"
    assert "google.antigravity" not in sys.modules

    # TF-5: Optional mappings
    # timeout: 2s -> 2s
    ns_t1 = parse_args(["--model", "m", "--name", "n", "--timeout", "2"])
    argv_t1 = build_agy_argv(ns_t1)
    assert argv_t1[argv_t1.index("--print-timeout") + 1] == "2s"

    # timeout ms ceiled to whole seconds, minimum 1s
    ns_t2 = parse_args(["--model", "m", "--name", "n", "--timeout", "500ms"])
    argv_t2 = build_agy_argv(ns_t2)
    assert argv_t2[argv_t2.index("--print-timeout") + 1] == "1s"

    ns_t3 = parse_args(["--model", "m", "--name", "n", "--timeout", "2100ms"])
    argv_t3 = build_agy_argv(ns_t3)
    assert argv_t3[argv_t3.index("--print-timeout") + 1] == "3s"

    # omitted timeout -> no --print-timeout
    ns_t4 = parse_args(["--model", "m", "--name", "n"])
    argv_t4 = build_agy_argv(ns_t4)
    assert "--print-timeout" not in argv_t4

    # effort
    ns_eff = parse_args(["--model", "m", "--name", "n", "--effort", "high"])
    argv_eff = build_agy_argv(ns_eff)
    assert argv_eff[argv_eff.index("--effort") + 1] == "high"

    # conversation-id -> --conversation
    ns_c = parse_args(["--model", "m", "--name", "n", "--conversation-id", "conv-xyz"])
    argv_c = build_agy_argv(ns_c)
    assert argv_c[argv_c.index("--conversation") + 1] == "conv-xyz"
    assert "--conversation-id" not in argv_c

    # vertex parsed but not forwarded
    ns_v = parse_args(["--model", "m", "--name", "n", "--vertex"])
    argv_v = build_agy_argv(ns_v)
    assert "--vertex" not in argv_v
    assert "--project" not in argv_v

    # Non-zero child exit -> lifecycle=failed even if stdout has STATUS: ok
    st_failed = empty_state({"jobName": "test", "runId": "r", "runDir": "/tmp", "timeoutMs": None})
    st_failed["lifecycle"] = "failed"
    st_failed["exitCode"] = 1
    rep_failed = build_report(st_failed, {"stdoutText": "STATUS: ok"})
    assert rep_failed["lifecycle"] == "failed"
    assert rep_failed["workerStatus"] == "ok"
    assert rep_failed["reportValid"] is True
    assert rep_failed["backend"] == "agy-cli"

    # Stream-json reconstruction: result.response wins
    with tempfile.NamedTemporaryFile("w+", delete=False, suffix=".jsonl") as f:
        f.write(json.dumps({"event": "init"}) + "\n")
        f.write(json.dumps({"event": "step_update", "step_type": "agent_response", "text_delta": "STATUS: stuck"}) + "\n")
        f.write(json.dumps({"event": "result", "result": {"response": "All done!\nSTATUS: ok"}}) + "\n")
        f.flush()
        tmp1 = Path(f.name)
    try:
        rec1 = reconstruct_assistant_text(tmp1)
        assert rec1 == "All done!\nSTATUS: ok"
        assert parse_worker_status(rec1) == "ok"
    finally:
        tmp1.unlink()

    # Stream-json reconstruction: deltas only
    with tempfile.NamedTemporaryFile("w+", delete=False, suffix=".jsonl") as f:
        f.write(json.dumps({"event": "init"}) + "\n")
        f.write(json.dumps({"event": "step_update", "step_type": "agent_response", "text_delta": "Working...\nSTATUS: "}) + "\n")
        f.write(json.dumps({"event": "step_update", "step_type": "agent_response", "text_delta": "ok\nDone."}) + "\n")
        f.flush()
        tmp2 = Path(f.name)
    try:
        rec2 = reconstruct_assistant_text(tmp2)
        assert parse_worker_status(rec2) == "ok"
    finally:
        tmp2.unlink()

    # Stream-json reconstruction: malformed lines ignored
    with tempfile.NamedTemporaryFile("w+", delete=False, suffix=".jsonl") as f:
        f.write("{invalid json\n")
        f.write(json.dumps({"event": "step_update", "step_type": "agent_response", "text_delta": "STATUS: ok"}) + "\n")
        f.write("corrupt trailing line\n")
        f.flush()
        tmp3 = Path(f.name)
    try:
        rec3 = reconstruct_assistant_text(tmp3)
        assert parse_worker_status(rec3) == "ok"
    finally:
        tmp3.unlink()

    print("SELFTEST: ok")
    return 0


def main(argv: list[str] | None = None) -> int:
    ns = parse_args(sys.argv[1:] if argv is None else argv)
    if ns.self_test:
        return self_test()
    return run_job(ns)


if __name__ == "__main__":
    raise SystemExit(main())
