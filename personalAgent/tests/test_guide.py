"""Interactive enroll and card-create front. No network and no live board."""

from pathlib import Path

import pytest

import hermes_kanban.runtime as runtime
from hermes_kanban.guide import card_text, run_guide
from hermes_kanban.onboard import OnboardRequest, OnboardResult


def answers(*values: str):
    remaining = iter(values)

    def _input(prompt: str) -> str:
        del prompt
        try:
            return next(remaining)
        except StopIteration as exc:
            raise AssertionError("guide asked for another answer") from exc

    return _input


def write_config(path: Path, location: Path) -> None:
    path.write_text(
        "\n".join(
            [
                "workspace:",
                f"  root: {location.parent}",
                "projects:",
                "  - id: demo",
                "    name: owner/demo",
                "    repository: owner/demo",
                "    location: " + str(location),
                "    default_branch: main",
                "    kanban_project_ids:",
                "      - p_demo",
                "",
            ]
        ),
        encoding="utf-8",
    )


def test_card_text_sets_path_and_skill_for_a_job():
    text = card_text(
        title="Write the PRD",
        priority="P2",
        problem="No product doc yet",
        expected_result="PRD.md exists",
        path="job",
        skill="prd-writer",
    )
    assert "## Path\njob\n" in text
    assert "## Skill\nprd-writer\n" in text
    assert "## Priority\nP2\n" in text


def test_enroll_dry_run_uses_existing_onboard(tmp_path: Path):
    seen: dict[str, object] = {}

    def onboard(request: OnboardRequest, config_path: Path) -> OnboardResult:
        seen["request"] = request
        seen["config"] = config_path
        return OnboardResult(
            project_id="app",
            repository=request.repository,
            native_id="p_app",
            location=tmp_path / "app",
            default_branch=request.branch,
            cloned=False,
            scaffolded=(),
            already_enrolled=False,
        )

    code = run_guide(
        tmp_path / "config.yaml",
        input_fn=answers("1", "owner/app", "", "2"),
        output_fn=lambda line: None,
        onboard=onboard,
    )
    assert code == 0
    request = seen["request"]
    assert isinstance(request, OnboardRequest)
    assert request.repository == "owner/app"
    assert request.branch == "main"
    assert request.dry_run is True


def test_add_card_creates_a_feature_with_the_native_id(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
):
    config = tmp_path / "config.yaml"
    write_config(config, tmp_path / "demo")
    created: list[list[str]] = []

    code = run_guide(
        config,
        input_fn=answers(
            "2",
            "9",
            "1",
            "3",
            "Ship search",
            "",
            "People cannot find notes",
            "Search returns matches",
        ),
        output_fn=print,
        card_creator=created.append,
    )
    assert code == 0
    args = created[0]
    assert args[0] == "Ship search"
    assert args[args.index("--project") + 1] == "p_demo"
    assert args[args.index("--priority") + 1] == "2"
    body = args[args.index("--body") + 1]
    assert "## Path\nfeature\n" in body
    assert "## Skill" not in body
    assert "card: Ship search" in capsys.readouterr().out


def test_add_card_without_a_project_stops(tmp_path: Path, capsys: pytest.CaptureFixture[str]):
    config = tmp_path / "config.yaml"
    config.write_text("workspace:\n  root: /tmp\nprojects: []\n", encoding="utf-8")
    code = run_guide(
        config,
        input_fn=answers("2"),
        output_fn=lambda line: None,
        card_creator=lambda args: pytest.fail(str(args)),
    )
    assert code == 1
    assert "enroll one first" in capsys.readouterr().err


def test_eof_stops(tmp_path: Path, capsys: pytest.CaptureFixture[str]):
    def _input(prompt: str) -> str:
        del prompt
        raise EOFError

    code = run_guide(tmp_path / "config.yaml", input_fn=_input, output_fn=lambda line: None)
    assert code == 1
    assert capsys.readouterr().err.strip() == "stopped"


class _Stdin:
    def __init__(self, tty: bool) -> None:
        self._tty = tty

    def isatty(self) -> bool:
        return self._tty


def test_bare_config_on_a_tty_starts_the_guide(monkeypatch: pytest.MonkeyPatch, tmp_path: Path):
    monkeypatch.setattr(runtime.sys, "stdin", _Stdin(True))
    seen: dict[str, Path] = {}

    def fake(config: Path) -> int:
        seen["config"] = config
        return 0

    monkeypatch.setattr("hermes_kanban.guide.run_guide", fake)
    config = tmp_path / "config.yaml"
    assert runtime.main(["--config", str(config)]) == 0
    assert seen["config"] == config


def test_bare_config_without_a_tty_still_requires_a_selector(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
):
    monkeypatch.setattr(runtime.sys, "stdin", _Stdin(False))

    def fake(config: Path) -> int:
        del config
        raise AssertionError("guide should not start")

    monkeypatch.setattr("hermes_kanban.guide.run_guide", fake)
    assert runtime.main(["--config", "config.yaml"]) == 2
    assert "choose exactly one" in capsys.readouterr().err


def test_claimed_worker_does_not_start_the_guide(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
):
    monkeypatch.setenv("HERMES_KANBAN_TASK", "task-1")
    monkeypatch.setattr(runtime.sys, "stdin", _Stdin(True))

    def fake(config: Path) -> int:
        del config
        raise AssertionError("guide should not start")

    monkeypatch.setattr("hermes_kanban.guide.run_guide", fake)
    assert runtime.main(["--config", str(tmp_path / "missing.yaml")]) == 1
