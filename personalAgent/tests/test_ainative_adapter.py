import os
import shutil
import subprocess
from pathlib import Path

import pytest

from hermes_kanban.ainative import (
    AgentDefinition,
    AiNativeAdapter,
    AiNativeAdapterError,
    AiNativeSettings,
    IncompleteAgentError,
    InvalidMethodologyError,
    ReadOnlyError,
    RevisionError,
    UnknownAgentError,
    UnresolvedDependencyError,
    load_ainative_settings,
)

FIXTURE_ROOT = Path(__file__).parent / "fixtures" / "ainative-full"


def git(*args: str, cwd: Path) -> None:
    subprocess.run(["git", *args], cwd=cwd, check=True, capture_output=True, text=True)


def copy_fixture(tmp_path: Path) -> Path:
    methodology = tmp_path / "ainative"
    shutil.copytree(FIXTURE_ROOT, methodology)
    git("init", cwd=methodology)
    git("config", "user.email", "tests@example.com", cwd=methodology)
    git("config", "user.name", "Tests", cwd=methodology)
    git("add", ".", cwd=methodology)
    git("commit", "-m", "fixture", cwd=methodology)
    return methodology


def settings_for(methodology: Path) -> AiNativeSettings:
    return AiNativeSettings(path=methodology, read_only=True)


def make_config(tmp_path: Path, path: str, read_only: str = "true") -> Path:
    config = tmp_path / "config.yaml"
    config.write_text(f"ainative:\n  path: {path}\n  read_only: {read_only}\n")
    return config


def adapter_for(tmp_path: Path) -> AiNativeAdapter:
    return AiNativeAdapter(settings_for(copy_fixture(tmp_path)))


def test_settings_parser_reads_only_ainative_block(tmp_path: Path):
    config = make_config(tmp_path, "/methodology")
    config.write_text(
        "workspace:\n  root: /ignored\n"
        "ainative:\n  path: /methodology\n  read_only: true\n"
        "github:\n  allow_push: false\n"
    )

    settings = load_ainative_settings(config)

    assert settings == AiNativeSettings(Path("/methodology"), True)


def test_construction_rejects_invalid_settings(tmp_path: Path):
    methodology = copy_fixture(tmp_path)
    missing_agents = tmp_path / "missing-agents"
    missing_agents.mkdir()
    file_path = tmp_path / "methodology.txt"
    file_path.write_text("not a directory")

    invalid_configs = [
        make_config(tmp_path, str(tmp_path / "missing")),
        make_config(tmp_path, ""),
        make_config(tmp_path, str(file_path)),
        make_config(tmp_path, str(missing_agents)),
        make_config(tmp_path, str(methodology), "false"),
        tmp_path,
    ]

    for config_path in invalid_configs:
        with pytest.raises(InvalidMethodologyError):
            AiNativeAdapter.from_config(config_path)


def test_constructor_rejects_invalid_direct_settings(tmp_path: Path):
    with pytest.raises(InvalidMethodologyError):
        AiNativeAdapter(AiNativeSettings(tmp_path / "missing", True))


@pytest.mark.parametrize("root", [Path("docs/8-agents"), Path("agents")])
def test_constructor_rejects_retired_agent_roots(
    tmp_path: Path, root: Path
):
    methodology = tmp_path / "retired-layout"
    (methodology / root / "scout").mkdir(parents=True)
    (methodology / root / "scout" / "SKILL.md").write_text("retired")

    with pytest.raises(InvalidMethodologyError):
        AiNativeAdapter(AiNativeSettings(methodology, True))


def test_empty_path_does_not_bind_to_cwd_with_agents(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
):
    cwd = tmp_path / "cwd"
    (cwd / "docs" / "8-agents").mkdir(parents=True)
    monkeypatch.chdir(cwd)
    for path_value in ("", "   "):
        with pytest.raises(InvalidMethodologyError):
            AiNativeAdapter.from_config(make_config(tmp_path, path_value))


def test_list_agents_discovers_sorted_non_reserved_directories(tmp_path: Path):
    adapter = adapter_for(tmp_path)

    assert adapter.list_agents() == [
        "broken-deps",
        "builder",
        "critic",
        "empty-agent",
        "scout",
        "specs-planner",
        "tester",
    ]


def test_get_agent_preserves_separate_raw_instruction_fields(tmp_path: Path):
    methodology = copy_fixture(tmp_path)
    adapter = AiNativeAdapter(settings_for(methodology))

    agent = adapter.get_agent("scout")

    assert isinstance(agent, AgentDefinition)
    assert agent.name == "scout"
    assert agent.purpose == (FIXTURE_ROOT / "docs/agents/scout/AGENTS.md").read_text()
    assert agent.howto == (FIXTURE_ROOT / "docs/agents/scout/SKILL.md").read_text()
    assert agent.constraints == (FIXTURE_ROOT / "docs/agents/scout/rule.md").read_text()
    assert agent.purpose_path == methodology / "docs/agents/scout/AGENTS.md"
    assert agent.howto_path == methodology / "docs/agents/scout/SKILL.md"
    assert agent.constraints_path == methodology / "docs/agents/scout/rule.md"
    assert not hasattr(agent, "instructions")


def test_get_agent_omits_missing_instruction_files(tmp_path: Path):
    adapter = adapter_for(tmp_path)

    agent = adapter.get_agent("broken-deps")

    assert agent.purpose is None
    assert agent.purpose_path is None
    assert agent.constraints is None
    assert agent.constraints_path is None
    assert agent.howto is not None


@pytest.mark.parametrize("name", ["template", "_skills", "../x", "a/b", r"a\b"])
def test_reserved_and_path_like_names_are_unknown(tmp_path: Path, name: str):
    adapter = adapter_for(tmp_path)

    with pytest.raises(UnknownAgentError):
        adapter.get_agent(name)
    with pytest.raises(UnknownAgentError):
        adapter.resolve_agent_dependencies(name)


def test_empty_agent_is_incomplete(tmp_path: Path):
    with pytest.raises(IncompleteAgentError):
        adapter_for(tmp_path).get_agent("empty-agent")


def test_resolve_dependencies_includes_rule_and_unique_skills(tmp_path: Path):
    adapter = adapter_for(tmp_path)

    dependencies = adapter.resolve_agent_dependencies("scout")

    assert [(item.kind, item.name) for item in dependencies] == [
        ("rule", "scout"),
        ("skill", "research-first"),
    ]
    assert dependencies[0].path == adapter.get_agent("scout").constraints_path
    assert dependencies[1].text == (
        FIXTURE_ROOT / "docs/agents/_skills/research-first/SKILL.md"
    ).read_text()


def test_missing_dependency_fails_without_partial_result(tmp_path: Path):
    adapter = adapter_for(tmp_path)

    with pytest.raises(UnresolvedDependencyError):
        adapter.resolve_agent_dependencies("broken-deps")


def test_capture_revision_reports_clean_and_dirty_worktree(tmp_path: Path):
    methodology = copy_fixture(tmp_path)
    adapter = AiNativeAdapter(settings_for(methodology))

    clean = adapter.capture_revision(methodology)
    (methodology / "docs/agents/scout/AGENTS.md").write_text("changed")
    dirty = adapter.capture_revision(methodology)

    assert clean.sha
    assert clean.repository == str(methodology)
    assert clean.branch
    assert clean.dirty is False
    assert dirty.sha == clean.sha
    assert dirty.dirty is True


def test_capture_revision_rejects_non_git_directory(tmp_path: Path):
    methodology = tmp_path / "not-git"
    methodology.mkdir()

    with pytest.raises(RevisionError):
        adapter_for(tmp_path).capture_revision(methodology)


def test_build_execution_context_contains_only_methodology_identity(tmp_path: Path):
    adapter = adapter_for(tmp_path)
    agent = adapter.get_agent("scout")

    context = adapter.build_execution_context(agent, workflow_phase="review")

    assert context.methodology_path == adapter.settings.path
    assert context.revision.sha
    assert context.agent is agent
    assert context.workflow_phase == "review"
    assert not hasattr(context, "task")
    assert not hasattr(context, "project")
    assert not hasattr(context, "workspace")


def test_refused_writes_leave_methodology_unchanged(tmp_path: Path):
    methodology = copy_fixture(tmp_path)
    adapter = AiNativeAdapter(settings_for(methodology))
    before = sorted(
        (path.relative_to(methodology), path.read_bytes())
        for path in methodology.rglob("*")
        if path.is_file()
    )

    with pytest.raises(ReadOnlyError):
        adapter.write_file("new.txt", "must not write")
    with pytest.raises(ReadOnlyError):
        adapter.copy_tree(tmp_path / "copy")

    after = sorted(
        (path.relative_to(methodology), path.read_bytes())
        for path in methodology.rglob("*")
        if path.is_file()
    )
    assert before == after
    assert not (tmp_path / "copy").exists()


def test_optional_live_mount_roster_is_real(tmp_path: Path):
    path = Path(os.environ.get("AINATIVE_PATH", "/ainative"))
    if not (path.is_dir() and (path / "docs/agents").is_dir()):
        pytest.skip("no live AiNative mount configured")

    adapter = AiNativeAdapter(AiNativeSettings(path, True))
    real_names = {
        child.name for child in (path / "docs/agents").iterdir() if child.is_dir()
    }
    assert set(adapter.list_agents()) <= real_names


def test_public_error_hierarchy():
    assert issubclass(InvalidMethodologyError, AiNativeAdapterError)
