#!/usr/bin/env python3
"""Deterministic offline Pi playbook stand-in and RPC process fixture."""

from __future__ import annotations

import json
import os
import sys
import time
from pathlib import Path

from hermes_kanban.external_framework import HarnessArtifact, ResumeContext
from hermes_kanban.pi import PiRunRequest, PiRunResponse


class PiFixtureRuntime:
    """Record Pi-owned playbook order without contacting a model or GitHub."""

    def __init__(
        self,
        *,
        needs_analysis: bool = True,
        question: bool = False,
        implementation_question: bool = False,
        second_question: bool = False,
        repeat_convergence: bool = False,
        stuck: bool = False,
        timeout: bool = False,
    ) -> None:
        self.needs_analysis = needs_analysis
        self.question = question
        self.implementation_question = implementation_question
        self.second_question = second_question
        self.repeat_convergence = repeat_convergence
        self.second_question_returned = False
        self.stuck = stuck
        self.timeout = timeout
        self.calls: list[PiRunRequest] = []
        self.order: list[str] = []

    def run(self, request: PiRunRequest) -> PiRunResponse:
        self.calls.append(request)
        if self.timeout:
            return PiRunResponse("timeout", "fixture timeout")
        if self.stuck:
            self.order.append("implement")
            return PiRunResponse(
                "stuck",
                "fixture stuck at convergence",
                next_action="retry the whole harness run",
                retryable=True,
            )
        feature = request.workspace_path / "specs" / request.task_id
        feature.mkdir(parents=True, exist_ok=True)
        if self.question and not request.resume_context:
            self.order.extend(("specify", "clarify"))
            (feature / "spec.md").write_text("# Fixture specification\n", encoding="utf-8")
            return PiRunResponse(
                "needs_human",
                "fixture clarification is required",
                next_action="answer the clarification",
                questions=("Choose the fixture scope.",),
                resume_context=ResumeContext(),
            )
        if (
            self.second_question
            and request.resume_context is not None
            and request.resume_context.continue_confirmed
            and not self.second_question_returned
        ):
            self.second_question_returned = True
            self.order.extend(("specify", "clarify/continue", "plan", "tasks"))
            return PiRunResponse(
                "needs_human",
                "fixture implementation mode is required",
                next_action="answer the implementation mode question",
                questions=("Choose the fixture implementation mode.",),
                resume_context=ResumeContext(continue_confirmed=True),
            )
        self.order.extend(("specify", "clarify/continue", "plan", "tasks"))
        if self.needs_analysis:
            self.order.append("analyze")
        if self.implementation_question and request.resume_context is None:
            self.order.append("implement")
            return PiRunResponse(
                "needs_human",
                "fixture implementation question",
                next_action="answer the implementation question",
                questions=("Keep the fixture change?",),
                resume_context=ResumeContext(continue_confirmed=True),
            )
        self.order.extend(("implement", "converge"))
        if self.repeat_convergence:
            self.order.extend(("implement", "converge"))
        (feature / "spec.md").write_text("# Fixture specification\n", encoding="utf-8")
        (feature / "plan.md").write_text("# Fixture plan\n", encoding="utf-8")
        (feature / "tasks.md").write_text("# Fixture tasks\n", encoding="utf-8")
        changed = request.workspace_path / "fixture-output.txt"
        changed.write_text("done\n", encoding="utf-8")
        return PiRunResponse(
            "completed",
            "fixture playbook completed",
            artifacts=(
                HarnessArtifact("specification", f"specs/{request.task_id}/spec.md"),
                HarnessArtifact("plan", f"specs/{request.task_id}/plan.md"),
                HarnessArtifact("tasks", f"specs/{request.task_id}/tasks.md"),
            ),
            changes=("fixture-output.txt",),
        )


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
            "next_action": "retry the harness",
            "retryable": True,
        }
    if mode in {"completed", "still-running-after-result", "extra-output"}:
        return {"status": "completed", "reason": "fixture process completed"}
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
        prefix = "The task document is:\n"
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
