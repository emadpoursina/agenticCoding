"""Contract and Pi adapter trust-boundary checks."""

from __future__ import annotations

import json
from dataclasses import replace
from pathlib import Path

import pytest

from hermes_kanban.external_framework import (
    HarnessArtifact,
    HarnessConfigurationError,
    HarnessResult,
    HarnessRuntimeError,
    HarnessStartRequest,
    HarnessValidationError,
    RepositoryContext,
    SafetyLimits,
    TaskContext,
    coerce_timeout_seconds,
    load_harness_config,
    load_harness_runtime,
    validate_harness_request,
    validate_harness_result,
)
from hermes_kanban.pi import PiHarnessAdapter, PiRunResponse
from test_piv_orchestrator import _runtime_class


def request(workspace: Path) -> HarnessStartRequest:
    return HarnessStartRequest(
        project_id="fixture",
        task_id="123",
        task_context=TaskContext(
            title="Fixture",
            description="Build the fixture",
            expected_result="A result",
            acceptance_criteria="The result exists",
            priority="P1",
        ),
        repository_context=RepositoryContext("github.com/example/fixture", "main"),
        workspace_path=workspace,
        workspace_branch="feature/task-123",
        playbook_id="speckit-orchestrate",
        model_profile="default",
        timeout_seconds=30,
        safety_limits=SafetyLimits(),
    )


def test_request_and_result_are_provider_neutral(tmp_path: Path) -> None:
    workspace = tmp_path / "worktree"
    workspace.mkdir()
    current = request(workspace)
    validate_harness_request(current)
    artifact = workspace / "spec.md"
    artifact.write_text("safe", encoding="utf-8")
    result = validate_harness_result(
        HarnessResult(
            "completed",
            "done",
            artifacts=(HarnessArtifact("specification", "spec.md"),),
            harness_id="pi",
        ),
        workspace_path=workspace,
        adapter_id="pi",
    )
    assert result.artifacts[0].relative_path == "spec.md"
    assert "Pi" not in repr(current)
    assert "SDK" not in repr(result)


@pytest.mark.parametrize(
    "change",
    [
        {"timeout_seconds": 0},
        {"playbook_id": "plan"},
        {"workspace_branch": "main"},
        {"model_profile": "provider/model"},
    ],
)
def test_unsafe_requests_fail_before_adapter_start(
    tmp_path: Path, change: dict[str, object]
) -> None:
    workspace = tmp_path / "worktree"
    workspace.mkdir()
    with pytest.raises(HarnessValidationError):
        validate_harness_request(replace(request(workspace), **change))


def test_paths_secrets_and_unknown_status_fail_closed(tmp_path: Path) -> None:
    workspace = tmp_path / "worktree"
    workspace.mkdir()
    outside = tmp_path / "outside.md"
    outside.write_text("safe", encoding="utf-8")
    with pytest.raises(HarnessValidationError):
        validate_harness_result(
            HarnessResult(
                "completed",
                "done",
                artifacts=(HarnessArtifact("plan", str(outside)),),
                harness_id="pi",
            ),
            workspace_path=workspace,
            adapter_id="pi",
        )
    with pytest.raises(HarnessValidationError):
        validate_harness_result(
            HarnessResult("unknown", "bad", harness_id="pi"),  # type: ignore[arg-type]
            workspace_path=workspace,
            adapter_id="pi",
        )


def test_pi_adapter_maps_runtime_failure_and_unavailable_runtime(tmp_path: Path) -> None:
    workspace = tmp_path / "worktree"
    workspace.mkdir()
    runtime = _runtime_class()(timeout=True)
    result = PiHarnessAdapter(runtime).start(request(workspace))
    assert result.status == "failed"
    unavailable = PiHarnessAdapter().start(request(workspace))
    assert unavailable.status == "failed"


def test_pi_fixture_skips_analyze_when_plan_does_not_require_it(tmp_path: Path) -> None:
    workspace = tmp_path / "worktree"
    workspace.mkdir()
    runtime = _runtime_class()(needs_analysis=False)

    result = PiHarnessAdapter(runtime).start(request(workspace))

    assert result.status == "completed"
    assert runtime.order == [
        "specify",
        "clarify/continue",
        "plan",
        "tasks",
        "implement",
        "converge",
    ]


def test_pi_fixture_repeats_implement_and_converge_until_agreement(
    tmp_path: Path,
) -> None:
    workspace = tmp_path / "worktree"
    workspace.mkdir()
    runtime = _runtime_class()(repeat_convergence=True)

    result = PiHarnessAdapter(runtime).start(request(workspace))

    assert result.status == "completed"
    assert runtime.order[-4:] == ["implement", "converge", "implement", "converge"]


def test_harness_config_pins_one_pi_runtime_and_named_profile(tmp_path: Path) -> None:
    runtime = tmp_path / "runtime"
    runtime.mkdir()
    (runtime / "manifest.json").write_text(
        '{"adapter_id":"pi","version":"1.0.0","revision":"fixture"}',
        encoding="utf-8",
    )
    config = tmp_path / "config.yaml"
    config.write_text(
        """harness:
  adapters:
    - id: pi
      active: true
      runtime_path_env: HERMES_PI_RUNTIME
  playbook: speckit-orchestrate
  model_profile: default
  timeout_seconds: 1800
""",
        encoding="utf-8",
    )
    executable = runtime / "pi"
    executable.write_text("#!/bin/sh\nexit 0\n", encoding="utf-8")
    executable.chmod(executable.stat().st_mode | 0o111)
    (runtime / "manifest.json").write_text(
        '{"adapter_id":"pi","version":"1.0.0","revision":"fixture","executable":"pi"}',
        encoding="utf-8",
    )

    loaded = load_harness_config(
        config,
        environ={"HERMES_PI_RUNTIME": str(runtime)},
    )

    assert loaded.adapter_id == "pi"
    assert loaded.model_profile == "default"
    assert loaded.runtime.revision == "fixture"
    assert loaded.timeout_seconds == 1800.0


def test_pi_adapter_rejects_malformed_runtime_output(tmp_path: Path) -> None:
    workspace = tmp_path / "worktree"
    workspace.mkdir()

    class Malformed:
        def run(self, _request):
            return PiRunResponse("completed", "done", artifacts=("missing.md",))

    result = PiHarnessAdapter(Malformed()).start(request(workspace))
    assert result.status == "failed"


def test_marker_only_runtime_is_unavailable(tmp_path: Path) -> None:
    runtime = tmp_path / "runtime"
    runtime.mkdir()
    (runtime / "manifest.json").write_text(
        '{"adapter_id":"pi","version":"1.0.0","revision":"fixture"}',
        encoding="utf-8",
    )
    config = tmp_path / "config.yaml"
    config.write_text(
        """harness:
  adapters:
    - id: pi
      active: true
      runtime_path_env: HERMES_PI_RUNTIME
  playbook: speckit-orchestrate
  model_profile: default
  timeout_seconds: 1800
""",
        encoding="utf-8",
    )

    with pytest.raises(HarnessRuntimeError):
        load_harness_config(config, environ={"HERMES_PI_RUNTIME": str(runtime)})


def test_checked_in_default_config_loads_with_fixture_runtime() -> None:
    config = Path(__file__).parents[1] / "config" / "default.yaml"
    runtime = Path(__file__).parent / "fixtures" / "pi-runtime"

    loaded = load_harness_config(
        config,
        environ={"HERMES_PI_RUNTIME": str(runtime)},
    )

    assert loaded.timeout_seconds == 1800.0
    assert loaded.runtime.executable == (runtime / "runtime.py").resolve()


@pytest.mark.parametrize("value", [None, "", " ", True, False, 0, -1, "0", "nope", "inf"])
def test_timeout_coercion_rejects_invalid_values(value: object) -> None:
    with pytest.raises(HarnessConfigurationError):
        coerce_timeout_seconds(value)


@pytest.mark.parametrize("value", [1, 1.5, "1", " 1.5 "])
def test_timeout_coercion_accepts_positive_finite_values(value: object) -> None:
    assert coerce_timeout_seconds(value) > 0


def test_process_adapter_sends_one_job_and_stops_after_one_result(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    workspace = tmp_path / "worktree"
    workspace.mkdir()
    runtime_path = Path(__file__).parent / "fixtures" / "pi-runtime"
    record_path = tmp_path / "process-record.json"
    monkeypatch.setenv("PI_FIXTURE_RECORD", str(record_path))
    monkeypatch.setenv("PI_FIXTURE_MODE", "still-running-after-result")
    marker = load_harness_runtime(
        adapter_id="pi",
        path_env="HERMES_PI_RUNTIME",
        environ={"HERMES_PI_RUNTIME": str(runtime_path)},
    )

    result = PiHarnessAdapter.from_runtime(marker).start(request(workspace))

    assert result.status == "completed"
    details = json.loads(record_path.read_text(encoding="utf-8"))
    assert details["argv"] == ["--mode", "rpc"]
    assert details["cwd"] == str(workspace)
    assert details["input_count"] == 1
    assert details["command"]["type"] == "prompt"
    assert details["job"]["playbook"] == "speckit-orchestrate"
    assert details["job"]["worktree"]["root"] == "."


@pytest.mark.parametrize(
    ("mode", "status"),
    [
        ("completed", "completed"),
        ("failed", "failed"),
        ("needs-human", "needs_human"),
        ("stuck", "stuck"),
        ("question", "needs_human"),
        ("error", "failed"),
        ("blocked", "failed"),
    ],
)
def test_process_adapter_maps_closed_statuses(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    mode: str,
    status: str,
) -> None:
    workspace = tmp_path / "worktree"
    workspace.mkdir()
    runtime_path = Path(__file__).parent / "fixtures" / "pi-runtime"
    monkeypatch.setenv("PI_FIXTURE_MODE", mode)
    marker = load_harness_runtime(
        adapter_id="pi",
        path_env="HERMES_PI_RUNTIME",
        environ={"HERMES_PI_RUNTIME": str(runtime_path)},
    )

    result = PiHarnessAdapter.from_runtime(marker).start(request(workspace))

    assert result.status == status


@pytest.mark.parametrize(
    "mode", ["malformed", "extra-output", "early-exit", "prompt-rejected", "timeout"]
)
def test_process_adapter_fails_closed_and_cleans_up(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, mode: str
) -> None:
    workspace = tmp_path / "worktree"
    workspace.mkdir()
    runtime_path = Path(__file__).parent / "fixtures" / "pi-runtime"
    monkeypatch.setenv("PI_FIXTURE_MODE", mode)
    marker = load_harness_runtime(
        adapter_id="pi",
        path_env="HERMES_PI_RUNTIME",
        environ={"HERMES_PI_RUNTIME": str(runtime_path)},
    )

    result = PiHarnessAdapter.from_runtime(marker).start(
        replace(request(workspace), timeout_seconds=0.1)
    )

    assert result.status == "failed"
