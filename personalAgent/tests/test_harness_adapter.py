"""Step-request and Pi adapter trust-boundary checks."""

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
    HarnessValidationError,
    StepStartRequest,
    coerce_timeout_seconds,
    load_harness_config,
    load_harness_runtime,
    parse_step_report,
    step_skill_path,
    validate_harness_result,
    validate_step_request,
)
from hermes_kanban.pi import PiHarnessAdapter, PiRunResponse
from test_piv_orchestrator import _runtime_class


def request(workspace: Path, step_id: str = "specify") -> StepStartRequest:
    return StepStartRequest(
        step_id=step_id,
        flow_id="flow-fixture",
        skill_path=(
            f"docs/agents/{step_id}/"
            if step_id in {"ready", "critic", "tester", "pr-review"}
            else step_skill_path(step_id)
        ),
        workspace_path=workspace,
        workspace_branch="feature/task-123",
        model_profile="default",
        timeout_seconds=30,
        inputs={"task_id": "123", "task_problem": "Build the fixture"},
    )


def test_request_and_result_are_provider_neutral(tmp_path: Path) -> None:
    workspace = tmp_path / "worktree"
    workspace.mkdir()
    current = request(workspace)
    validate_step_request(current)
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
        step_id="specify",
    )
    assert result.artifacts[0].relative_path == "spec.md"
    assert "Pi" not in repr(current)
    assert "SDK" not in repr(result)


def test_artifact_coercion_accepts_model_shapes(tmp_path: Path) -> None:
    from hermes_kanban.pi import _coerce_artifacts

    assert _coerce_artifacts(["spec.md", {"kind": "plan", "relative_path": "plan.md"}]) == (
        HarnessArtifact("file", "spec.md"),
        HarnessArtifact("plan", "plan.md"),
    )
    assert _coerce_artifacts({"specification": "spec.md"}) == (
        HarnessArtifact("specification", "spec.md"),
    )
    assert _coerce_artifacts(None) == ()


@pytest.mark.parametrize(
    "raw",
    [
        42,
        True,
        "",
        "  ",
        [{"kind": 3, "relative_path": "x"}],
        [object()],
        [{"relative_path": " "}],
    ],
)
def test_artifact_coercion_still_fails_closed(raw: object) -> None:
    from hermes_kanban.pi import _coerce_artifacts

    with pytest.raises(HarnessValidationError):
        _coerce_artifacts(raw)


@pytest.mark.parametrize(
    "change",
    [
        {"timeout_seconds": 0},
        {"workspace_branch": "main"},
        {"model_profile": "provider/model"},
        {"flow_id": ""},
        {"skill_path": "../escape/SKILL.md"},
        {"inputs": {}},
        {"operator_flags": ("merge",)},
    ],
)
def test_unsafe_requests_fail_before_adapter_start(
    tmp_path: Path, change: dict[str, object]
) -> None:
    workspace = tmp_path / "worktree"
    workspace.mkdir()
    with pytest.raises(HarnessValidationError):
        validate_step_request(replace(request(workspace), **change))


@pytest.mark.parametrize(
    "step_id",
    ["speckit-orchestrate", "confirm", "uat", "publish", "unknown-step", "", "../specify"],
)
def test_whole_playbook_and_non_agent_requests_are_refused(
    tmp_path: Path, step_id: str
) -> None:
    workspace = tmp_path / "worktree"
    workspace.mkdir()
    with pytest.raises(HarnessValidationError):
        validate_step_request(request(workspace, step_id))


def test_compact_reports_are_strict_per_state(tmp_path: Path) -> None:
    report = parse_step_report(
        "ready",
        {
            "READY": "ok",
            "FLOW_ID": "flow",
            "BRANCH": "feature/task-123",
            "CHECKS": "ok",
            "FIXES": "none",
        },
    )
    assert report.fields["READY"] == "ok"
    with pytest.raises(HarnessValidationError):
        parse_step_report("ready", {"READY": "ok"})
    with pytest.raises(HarnessValidationError):
        parse_step_report(
            "ready",
            {
                "READY": "ok",
                "FLOW_ID": "flow",
                "BRANCH": "b",
                "CHECKS": "c",
                "FIXES": "f",
                "EXTRA": "x",
            },
        )
    with pytest.raises(HarnessValidationError):
        parse_step_report(
            "plan", {"FLOW_ID": "f", "ARTIFACTS": "a", "STATUS": "ok", "SUMMARY": "s"}
        )
    plan = parse_step_report(
        "plan",
        {
            "FLOW_ID": "f",
            "ARTIFACTS": "plan.md",
            "STATUS": "ok",
            "SUMMARY": "s",
            "ANALYZE": "yes",
        },
    )
    assert plan.fields["ANALYZE"] == "yes"
    with pytest.raises(HarnessValidationError):
        parse_step_report(
            "converge",
            {
                "CONVERGE_OUTCOME": "converged",
                "FINDINGS": "f",
                "FINGERPRINT": "fp",
                "TASKS_APPENDED": "no",
                "SUMMARY": "s",
                "EXTRA": "x",
            },
        )
    with pytest.raises(HarnessValidationError):
        parse_step_report("critic", {"VERDICT": "MAYBE", "SUMMARY": "s"})


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
            step_id="specify",
        )
    with pytest.raises(HarnessValidationError):
        validate_harness_result(
            HarnessResult("unknown", "bad", harness_id="pi"),  # type: ignore[arg-type]
            workspace_path=workspace,
            adapter_id="pi",
            step_id="specify",
        )


def test_pi_adapter_maps_runtime_failure_and_unavailable_runtime(tmp_path: Path) -> None:
    workspace = tmp_path / "worktree"
    workspace.mkdir()
    runtime = _runtime_class()(timeout=True)
    result = PiHarnessAdapter(runtime).start(request(workspace))
    assert result.status == "failed"
    unavailable = PiHarnessAdapter().start(request(workspace))
    assert unavailable.status == "failed"


def test_pi_fixture_runs_exactly_one_step_per_start(tmp_path: Path) -> None:
    workspace = tmp_path / "worktree"
    workspace.mkdir()

    ready = PiHarnessAdapter(_runtime_class()()).start(request(workspace, "ready"))
    assert ready.status == "completed"
    assert ready.report is not None
    assert ready.report.fields["READY"] == "ok"
    assert ready.report.step_id == "ready"

    runtime = _runtime_class()(repeat_convergence=True)
    adapter = PiHarnessAdapter(runtime)
    first = adapter.start(request(workspace, "converge"))
    assert first.status == "completed"
    assert first.report is not None
    assert first.report.fields["CONVERGE_OUTCOME"] == "tasks_appended"
    second = adapter.start(request(workspace, "converge"))
    assert second.status == "completed"
    assert second.report.fields["CONVERGE_OUTCOME"] == "converged"
    assert runtime.order == ["converge", "converge"]
    assert len(set(runtime.sessions)) == len(runtime.sessions)


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
  model_profile: default
  step_profiles:
    ready: ready
    critic: critic
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
    assert loaded.step_profiles == {"ready": "ready", "critic": "critic"}
    assert loaded.models == {}
    assert loaded.runtime.revision == "fixture"
    assert loaded.timeout_seconds == 1800.0


def test_harness_models_map_a_named_profile(tmp_path: Path) -> None:
    runtime = tmp_path / "runtime"
    runtime.mkdir()
    executable = runtime / "pi"
    executable.write_text("#!/bin/sh\nexit 0\n", encoding="utf-8")
    executable.chmod(executable.stat().st_mode | 0o111)
    (runtime / "manifest.json").write_text(
        '{"adapter_id":"pi","version":"1.0.0","revision":"fixture","executable":"pi"}',
        encoding="utf-8",
    )
    config = tmp_path / "config.yaml"
    config.write_text(
        """harness:
  adapters:
    - id: pi
      active: true
      runtime_path_env: HERMES_PI_RUNTIME
  model_profile: default
  models:
    DeepSeekFlash:
      provider: custom
      model: DeepSeekFlash
  timeout_seconds: 1800
""",
        encoding="utf-8",
    )

    loaded = load_harness_config(config, environ={"HERMES_PI_RUNTIME": str(runtime)})

    assert loaded.models == {"DeepSeekFlash": ("custom", "DeepSeekFlash")}


def test_harness_models_reject_a_path(tmp_path: Path) -> None:
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
  model_profile: default
  models:
    default:
      provider: ../escaped
      model: DeepSeekFlash
  timeout_seconds: 1800
""",
        encoding="utf-8",
    )

    with pytest.raises(HarnessConfigurationError):
        load_harness_config(config, environ={"HERMES_PI_RUNTIME": str(runtime)})


def test_unknown_step_profile_fails_closed_at_startup(tmp_path: Path) -> None:
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
  model_profile: default
  step_profiles:
    confirm: confirm
  timeout_seconds: 1800
""",
        encoding="utf-8",
    )

    with pytest.raises(HarnessConfigurationError):
        load_harness_config(config, environ={"HERMES_PI_RUNTIME": str(runtime)})


def test_retired_playbook_config_line_fails_closed(tmp_path: Path) -> None:
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

    with pytest.raises(HarnessConfigurationError):
        load_harness_config(config, environ={"HERMES_PI_RUNTIME": str(runtime)})


def test_drifted_advisory_paths_are_dropped_not_rejected(tmp_path: Path) -> None:
    workspace = tmp_path / "worktree"
    workspace.mkdir()
    kept = workspace / "spec.md"
    kept.write_text("safe", encoding="utf-8")

    class Drifted:
        def run(self, _request):
            return PiRunResponse(
                "completed",
                "done",
                artifacts=("missing.md", "spec.md"),
                changes=("../escape.md", "spec.md"),
                output_reference="commit 3c15ebd",
                report={"FLOW_ID": "f", "ARTIFACTS": "spec.md", "STATUS": "ok", "SUMMARY": "s"},
            )

    result = PiHarnessAdapter(Drifted()).start(request(workspace))

    assert result.status == "completed"
    assert result.artifacts == (HarnessArtifact("file", "spec.md"),)
    assert result.changes == ("spec.md",)
    assert result.output_reference is None


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


def test_process_adapter_sends_one_step_job_and_stops_after_one_result(
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
    assert details["argv"][:2] == ["--mode", "rpc"]
    assert details["argv"][2:4] == ["--append-system-prompt", details["launch"]["contract"]]
    assert Path(details["launch"]["contract"]).is_file()
    assert "provider" not in details["launch"]
    assert "model" not in details["launch"]
    assert "tools" not in details["launch"]
    assert details["cwd"] == str(workspace)
    assert details["input_count"] == 1
    assert details["command"]["type"] == "prompt"
    assert details["job"]["step_id"] == "specify"
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


def test_review_steps_are_read_only_and_leave_a_run_record(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    workspace = tmp_path / "worktree"
    workspace.mkdir()
    runtime_path = Path(__file__).parent / "fixtures" / "pi-runtime"
    record_path = tmp_path / "process-record.json"
    monkeypatch.setenv("PI_FIXTURE_RECORD", str(record_path))
    marker = load_harness_runtime(
        adapter_id="pi",
        path_env="HERMES_PI_RUNTIME",
        environ={"HERMES_PI_RUNTIME": str(runtime_path)},
    )

    adapter = PiHarnessAdapter.from_runtime(marker, run_root=tmp_path / "runs")
    result = adapter.start(request(workspace, "critic"))

    assert result.status == "completed"
    details = json.loads(record_path.read_text(encoding="utf-8"))
    assert details["launch"]["tools"] == "read,grep,find,ls"
    assert adapter.last_run_dir is not None
    assert adapter.last_run_dir.is_relative_to(tmp_path / "runs")
    status = json.loads((adapter.last_run_dir / "status.json").read_text(encoding="utf-8"))
    assert status["lifecycle"] == "completed"
    assert not any(workspace.iterdir())


def test_configured_model_is_passed_on_the_pi_process(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    workspace = tmp_path / "worktree"
    workspace.mkdir()
    runtime_path = Path(__file__).parent / "fixtures" / "pi-runtime"
    record_path = tmp_path / "process-record.json"
    monkeypatch.setenv("PI_FIXTURE_RECORD", str(record_path))
    marker = load_harness_runtime(
        adapter_id="pi",
        path_env="HERMES_PI_RUNTIME",
        environ={"HERMES_PI_RUNTIME": str(runtime_path)},
    )

    result = PiHarnessAdapter.from_runtime(
        marker,
        model_selections={"DeepSeekFlash": ("custom", "DeepSeekFlash")},
    ).start(replace(request(workspace), model_profile="DeepSeekFlash"))

    assert result.status == "completed"
    details = json.loads(record_path.read_text(encoding="utf-8"))
    assert details["launch"]["provider"] == "custom"
    assert details["launch"]["model"] == "DeepSeekFlash"
    assert "tools" not in details["launch"]


def test_timeout_keeps_stderr_outside_the_worktree(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    workspace = tmp_path / "worktree"
    workspace.mkdir()
    runtime_path = Path(__file__).parent / "fixtures" / "pi-runtime"
    monkeypatch.setenv("PI_FIXTURE_MODE", "timeout")
    monkeypatch.setenv("PI_FIXTURE_STDERR", "fixture stderr still running")
    marker = load_harness_runtime(
        adapter_id="pi",
        path_env="HERMES_PI_RUNTIME",
        environ={"HERMES_PI_RUNTIME": str(runtime_path)},
    )

    adapter = PiHarnessAdapter.from_runtime(marker, run_root=tmp_path / "runs")
    result = adapter.start(replace(request(workspace), timeout_seconds=0.5))

    assert result.status == "failed"
    assert adapter.last_run_dir is not None
    assert f"run_dir={adapter.last_run_dir}" in result.reason
    assert "fixture stderr still running" in (adapter.last_run_dir / "stderr.log").read_text(
        encoding="utf-8"
    )
    status = json.loads((adapter.last_run_dir / "status.json").read_text(encoding="utf-8"))
    assert status["lifecycle"] == "failed"
    assert status["processAlive"] is False
