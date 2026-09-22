#!/usr/bin/env python3
"""Deterministic offline Pi step stand-in and RPC process fixture.

Every ``run`` call is exactly one agent-state session: the request names one
step, the fixture executes that step only, and returns a per-state compact
report. No model, GitHub, or Telegram is contacted.
"""

from __future__ import annotations

import json
import os
import sys
import time
import uuid
from pathlib import Path

from hermes_kanban.pi import PiRunRequest, PiRunResponse


def _report(**fields: object) -> dict[str, object]:
    return fields


class PiFixtureRuntime:
    """Record one Pi session per agent state without contacting a model."""

    def __init__(
        self,
        *,
        needs_analysis: bool = True,
        question: bool = False,
        ready_blocked: bool = False,
        repeat_convergence: bool = False,
        converge_stuck: bool = False,
        converge_blocked: bool = False,
        critic_retryable_fail: bool = False,
        tester_fail: bool = False,
        pr_review_fail: bool = False,
        stuck: bool = False,
        timeout: bool = False,
        missing_artifact: bool = False,
    ) -> None:
        self.needs_analysis = needs_analysis
        self.question = question
        self.ready_blocked = ready_blocked
        self.repeat_convergence = repeat_convergence
        self.converge_stuck = converge_stuck
        self.converge_blocked = converge_blocked
        self.critic_retryable_fail = critic_retryable_fail
        self.tester_fail = tester_fail
        self.pr_review_fail = pr_review_fail
        self.stuck = stuck
        self.timeout = timeout
        self.missing_artifact = missing_artifact
        self.calls: list[PiRunRequest] = []
        self.order: list[str] = []
        self.sessions: list[str] = []
        self.validation_command_observes: list[object] = []

    def run(self, request: PiRunRequest) -> PiRunResponse:
        self.calls.append(request)
        step = request.step_id
        self.order.append(step)
        self.sessions.append(uuid.uuid4().hex)
        if self.timeout:
            return PiRunResponse("timeout", "fixture timeout")
        if self.stuck:
            return PiRunResponse(
                "stuck",
                "fixture step is stuck",
                next_action="retry the step",
                retryable=True,
            )
        feature = request.workspace_path / "specs" / request.task_id
        flow_id = request.flow_id
        if step == "ready":
            if self.ready_blocked:
                return PiRunResponse(
                    "completed",
                    "fixture ready preflight blocked",
                    report=_report(
                        READY="blocked",
                        FLOW_ID=flow_id,
                        BRANCH=request.workspace_branch,
                        CHECKS="spec-kit layout missing",
                        FIXES="restore the Spec Kit skills",
                    ),
                )
            return PiRunResponse(
                "completed",
                "fixture ready preflight ok",
                report=_report(
                    READY="ok",
                    FLOW_ID=flow_id,
                    BRANCH=request.workspace_branch,
                    CHECKS="git and Spec Kit layout ok",
                    FIXES="none",
                ),
            )
        if step == "specify":
            if not self.missing_artifact:
                feature.mkdir(parents=True, exist_ok=True)
                (feature / "spec.md").write_text("# Fixture specification\n", encoding="utf-8")
            return PiRunResponse(
                "completed",
                "fixture specify ok",
                report=_report(
                    FLOW_ID=flow_id,
                    ARTIFACTS="spec.md",
                    STATUS="ok",
                    SUMMARY="fixture specification written",
                ),
            )
        if step == "clarify":
            if "skip" in request.operator_flags:
                return PiRunResponse(
                    "completed",
                    "fixture clarify self-answered under skip",
                    report=_report(
                        FLOW_ID=flow_id,
                        ARTIFACTS="spec.md",
                        STATUS="ok",
                        SUMMARY="assumptions recorded",
                    ),
                )
            if (
                self.question
                and request.resume_context is not None
                and request.resume_context.answers
            ):
                # The encode-answers session: answers arrive via resume context.
                return PiRunResponse(
                    "completed",
                    "fixture answers encoded",
                    report=_report(
                        FLOW_ID=flow_id,
                        ARTIFACTS="spec.md updated",
                        STATUS="ok",
                        SUMMARY="operator answers encoded",
                    ),
                )
            if self.question:
                return PiRunResponse(
                    "needs_human",
                    "fixture clarification is required",
                    next_action="answer the clarification",
                    questions=("Choose the fixture scope.",),
                    report=_report(
                        FLOW_ID=flow_id,
                        ARTIFACTS="questions raised",
                        STATUS="blocked",
                        SUMMARY="fixture clarification required",
                        questions=["Choose the fixture scope."],
                    ),
                )
            return PiRunResponse(
                "completed",
                "fixture clarify ok",
                report=_report(
                    FLOW_ID=flow_id,
                    ARTIFACTS="spec.md",
                    STATUS="ok",
                    SUMMARY="no open questions",
                ),
            )
        if step == "plan":
            if not self.missing_artifact:
                feature.mkdir(parents=True, exist_ok=True)
                (feature / "plan.md").write_text("# Fixture plan\n", encoding="utf-8")
            return PiRunResponse(
                "completed",
                "fixture plan written",
                report=_report(
                    FLOW_ID=flow_id,
                    ARTIFACTS="plan.md",
                    STATUS="ok",
                    SUMMARY="fixture plan written",
                    ANALYZE="yes" if self.needs_analysis else "no",
                ),
            )
        if step == "tasks":
            if not self.missing_artifact:
                feature.mkdir(parents=True, exist_ok=True)
                (feature / "tasks.md").write_text("# Fixture tasks\n", encoding="utf-8")
            return PiRunResponse(
                "completed",
                "fixture tasks written",
                report=_report(
                    FLOW_ID=flow_id,
                    ARTIFACTS="tasks.md",
                    STATUS="ok",
                    SUMMARY="fixture tasks written",
                ),
            )
        if step == "analyze":
            return PiRunResponse(
                "completed",
                "fixture analyze clean",
                report=_report(
                    FLOW_ID=flow_id,
                    ARTIFACTS="none",
                    STATUS="ok",
                    SUMMARY="no critical findings",
                ),
            )
        if step == "implement":
            changed = request.workspace_path / "fixture-output.txt"
            changed.write_text("done\n", encoding="utf-8")
            return PiRunResponse(
                "completed",
                "fixture implementation pass finished",
                changes=("fixture-output.txt",),
                report=_report(
                    IMPLEMENT_STATUS="ok",
                    TASKS_DONE="all",
                    TASKS_OPEN="none",
                    BLOCKER="none",
                    SUMMARY="fixture tasks implemented",
                ),
            )
        if step == "converge":
            count = self.order.count("converge")
            if self.converge_stuck:
                # Same fingerprint every pass: the loop is stuck.
                fingerprint = "fixture-fingerprint-stuck"
            else:
                fingerprint = f"fixture-fingerprint-{count}"
            if self.converge_blocked:
                return PiRunResponse(
                    "completed",
                    "fixture convergence blocked",
                    report=_report(
                        CONVERGE_OUTCOME="blocked",
                        FINDINGS="fixture findings",
                        FINGERPRINT=fingerprint,
                        TASKS_APPENDED="no",
                        SUMMARY="fixture convergence blocked",
                    ),
                )
            if self.converge_stuck:
                outcome = "tasks_appended"
                appended = "yes"
            elif self.repeat_convergence and count == 1:
                outcome = "tasks_appended"
                appended = "yes"
            else:
                outcome = "converged"
                appended = "no"
            return PiRunResponse(
                "completed",
                "fixture convergence checked",
                report=_report(
                    CONVERGE_OUTCOME=outcome,
                    FINDINGS="fixture findings",
                    FINGERPRINT=fingerprint,
                    TASKS_APPENDED=appended,
                    SUMMARY="fixture convergence report",
                ),
            )
        if step == "critic":
            verdict = "FAIL" if self.critic_retryable_fail else "PASS"
            return PiRunResponse(
                "completed",
                f"fixture critic verdict {verdict}",
                retryable=verdict == "FAIL",
                report=_report(
                    VERDICT=verdict,
                    SUMMARY="fixture critic findings" if verdict == "FAIL" else "no findings",
                ),
            )
        if step == "tester":
            self.validation_command_observes.append(request.inputs.get("validation_commands"))
            verdict = "FAIL" if self.tester_fail else "PASS"
            return PiRunResponse(
                "completed",
                f"fixture tester verdict {verdict}",
                report=_report(
                    VERDICT=verdict,
                    SUMMARY="fixture tester report",
                ),
            )
        if step == "pr-review":
            verdict = "FAIL" if self.pr_review_fail else "PASS"
            return PiRunResponse(
                "completed",
                f"fixture pr-review verdict {verdict}",
                report=_report(
                    VERDICT=verdict,
                    SUMMARY="fixture pr-review report",
                ),
            )
        return PiRunResponse("failed", f"fixture does not implement step: {step}")


def _process_result(mode: str) -> dict[str, object] | None:
    if mode in {"failed", "error", "blocked"}:
        return {"status": mode, "reason": "fixture process failed"}
    if mode in {"needs-human", "question"}:
        return {
            "status": "question" if mode == "question" else "needs_human",
            "reason": "fixture process needs a person",
            "next_action": "answer the fixture question",
            "questions": ["Choose the fixture action."],
        }
    if mode == "stuck":
        return {
            "status": "stuck",
            "reason": "fixture process is stuck",
            "next_action": "retry the step",
            "retryable": True,
        }
    if mode in {"completed", "still-running-after-result", "extra-output"}:
        return {
            "status": "completed",
            "reason": "fixture process completed",
            "report": {
                "FLOW_ID": "flow-fixture",
                "ARTIFACTS": "spec.md",
                "STATUS": "ok",
                "SUMMARY": "fixture step completed",
            },
        }
    return None


def _run_rpc_process() -> int:
    if sys.argv[1:] != ["--mode", "rpc"]:
        return 2
    raw_input = sys.stdin.readline()
    input_count = 1 if raw_input.strip() else 0
    try:
        command = json.loads(raw_input)
    except json.JSONDecodeError:
        command = None
    payload = None
    if isinstance(command, dict) and command.get("type") == "prompt":
        message = command.get("message", "")
        prefix = "The step document is:\n"
        if isinstance(message, str) and prefix in message:
            try:
                payload = json.loads(message.rsplit(prefix, 1)[1])
            except json.JSONDecodeError:
                payload = None
    record_path = os.environ.get("PI_FIXTURE_RECORD", "").strip()
    if record_path:
        Path(record_path).write_text(
            json.dumps(
                {
                    "argv": sys.argv[1:],
                    "cwd": os.getcwd(),
                    "input_count": input_count,
                    "command": command,
                    "job": payload,
                }
            ),
            encoding="utf-8",
        )
    mode = os.environ.get("PI_FIXTURE_MODE", "completed").strip()
    if mode == "timeout":
        time.sleep(3600)
    if mode == "early-exit":
        return 3
    if mode == "prompt-rejected":
        print(
            json.dumps(
                {
                    "type": "response",
                    "command": "prompt",
                    "success": False,
                    "error": "No API key found",
                }
            ),
            flush=True,
        )
        return 0
    if mode == "malformed":
        print(json.dumps({"type": "response", "command": "prompt", "success": True}), flush=True)
        print(
            json.dumps(
                {
                    "type": "message_end",
                    "message": {
                        "role": "assistant",
                        "content": [{"type": "text", "text": "{not-json"}],
                    },
                }
            ),
            flush=True,
        )
        print(json.dumps({"type": "agent_settled"}), flush=True)
        return 0
    result = _process_result(mode)
    if result is None:
        return 4
    print(
        json.dumps(
            {
                "id": command.get("id") if isinstance(command, dict) else None,
                "type": "response",
                "command": "prompt",
                "success": True,
            }
        ),
        flush=True,
    )
    result_event = {
        "type": "message_end",
        "message": {
            "role": "assistant",
            "content": [{"type": "text", "text": json.dumps(result)}],
        },
    }
    print(json.dumps(result_event), flush=True)
    if mode == "extra-output":
        print(json.dumps(result_event), flush=True)
    print(json.dumps({"type": "agent_settled"}), flush=True)
    if mode == "still-running-after-result":
        time.sleep(3600)
    return 0


if __name__ == "__main__":
    raise SystemExit(_run_rpc_process())
