import shutil
from pathlib import Path

import pytest

from hermes_kanban.projects import (
    DisabledProjectError,
    InvalidProjectConfigError,
    InvalidProjectLocationError,
    MalformedManifestError,
    MissingProjectConfigurationError,
    ProjectContext,
    ProjectRecord,
    ProjectRegistry,
    UnknownProjectError,
    UnsafePathError,
)

FIXTURE_ROOT = Path(__file__).parent / "fixtures" / "projects" / "standard"
PACKAGE_ROOT = Path(__file__).resolve().parents[1]
_SKIP_CONTROL_PLANE = {
    ".git",
    ".hermes",
    ".pytest_cache",
    ".ruff_cache",
    ".venv",
    "__pycache__",
    "workspaces",
}


def copy_fixture(tmp_path: Path) -> Path:
    project = tmp_path / "standard"
    shutil.copytree(FIXTURE_ROOT, project)
    return project


def write_config(tmp_path: Path, entries: str) -> Path:
    config = tmp_path / "config.yaml"
    config.write_text(f"projects:\n{entries}", encoding="utf-8")
    return config


def entry(
    location: Path,
    *,
    project_id: str = "fixture",
    repository: str = "github.com/example/fixture",
    extra: str = "",
) -> str:
    return (
        f"  - id: {project_id}\n"
        f"    name: Fixture\n"
        f"    repository: {repository}\n"
        f"    location: {location}\n"
        f"{extra}"
    )


def registry_for(tmp_path: Path, *, extra: str = "") -> tuple[ProjectRegistry, Path]:
    project = copy_fixture(tmp_path)
    config = write_config(tmp_path, entry(project, extra=extra))
    return ProjectRegistry.from_config(config), project


def test_list_and_get_return_operational_records_only(tmp_path: Path):
    registry, project = registry_for(
        tmp_path,
        extra="    default_branch: develop\n    settings:\n      retries: 2\n",
    )

    projects = registry.list_projects()

    assert len(projects) == 1
    assert projects[0] == ProjectRecord(
        id="fixture",
        name="Fixture",
        repository="github.com/example/fixture",
        location=project,
        default_branch="develop",
        enabled=True,
        settings={"retries": "2"},
        manifest=None,
    )
    assert registry.get_project("fixture") == projects[0]
    assert not hasattr(projects[0], "overview")


def test_disabled_projects_are_listed_but_not_eligible(tmp_path: Path):
    project = copy_fixture(tmp_path)
    config = write_config(tmp_path, entry(project, extra="    enabled: false\n"))
    registry = ProjectRegistry.from_config(config)

    assert registry.list_projects()[0].enabled is False
    with pytest.raises(DisabledProjectError):
        registry.resolve_eligible_project("fixture")
    with pytest.raises(DisabledProjectError):
        registry.load_project_context("fixture")


@pytest.mark.parametrize("project_id", ["missing", "../fixture", "/fixture", r"a\b", "a/b"])
def test_unknown_and_path_like_ids_are_rejected(tmp_path: Path, project_id: str):
    registry, _ = registry_for(tmp_path)

    with pytest.raises(UnknownProjectError):
        registry.get_project(project_id)


def test_empty_config_does_not_discover_directories(tmp_path: Path):
    (tmp_path / "unlisted").mkdir()
    registry = ProjectRegistry.from_config(write_config(tmp_path, ""))

    assert registry.list_projects() == []
    with pytest.raises(UnknownProjectError):
        registry.get_project("unlisted")


@pytest.mark.parametrize("location_factory", ["missing", "file"])
def test_invalid_locations_never_fall_back(tmp_path: Path, location_factory: str):
    location = tmp_path / "not-there"
    if location_factory == "file":
        location.write_text("not a project", encoding="utf-8")
    registry = ProjectRegistry.from_config(write_config(tmp_path, entry(location)))

    with pytest.raises(InvalidProjectLocationError):
        registry.resolve_eligible_project("fixture")


@pytest.mark.parametrize(
    "entries",
    [
        (
            "  - id: fixture\n    name: One\n    repository: one\n    location: /one\n"
            "  - id: fixture\n    name: Two\n    repository: two\n    location: /two\n"
        ),
        (
            "  - id: fixture\n    name: One\n    repository: same\n    location: /one\n"
            "  - id: other\n    name: Two\n    repository: same\n    location: /two\n"
        ),
        (
            "  - id: fixture\n    name: One\n    repository: one\n    location: /same/\n"
            "  - id: other\n    name: Two\n    repository: two\n    location: /same\n"
        ),
        "  - id: ../fixture\n    name: Fixture\n    repository: repo\n    location: /fixture\n",
        (
            "  - id: fixture\n    name: Fixture\n    repository: repo\n    location: /fixture\n"
            "    settings:\n      nested: {}\n"
        ),
        (
            "  - id: fixture\n    name: Fixture\n    repository: repo\n    location: /fixture\n"
            "    manifest: ../project.yaml\n"
        ),
        (
            "  - id: fixture\n    name: One\n    repository: one\n    location: /one\n"
            "    kanban_project_ids:\n      - p_x\n"
            "  - id: other\n    name: Two\n    repository: two\n    location: /two\n"
            "    kanban_project_ids:\n      - p_x\n"
        ),
        (
            "  - id: fixture\n    name: One\n    repository: one\n    location: /one\n"
            "    kanban_project_ids:\n      - fixture\n"
        ),
        (
            "  - id: fixture\n    name: One\n    repository: one\n    location: /one\n"
            "    kanban_project_ids:\n      - other\n"
            "  - id: other\n    name: Two\n    repository: two\n    location: /two\n"
        ),
        (
            "  - id: fixture\n    name: Fixture\n    repository: repo\n    location: /fixture\n"
            "    kanban_project_ids:\n      - p_x\n      - p_x\n"
        ),
        (
            "  - id: fixture\n    name: Fixture\n    repository: repo\n    location: /fixture\n"
            "    kanban_project_ids:\n      - a/b\n"
        ),
        (
            "  - id: fixture\n    name: Fixture\n    repository: repo\n    location: /fixture\n"
            "    kanban_project_ids:\n      - ''\n"
        ),
    ],
)
def test_invalid_managed_set_fails_at_construction(tmp_path: Path, entries: str):
    with pytest.raises(InvalidProjectConfigError):
        ProjectRegistry.from_config(write_config(tmp_path, entries))


@pytest.mark.parametrize("field", ["id", "name", "repository", "location"])
def test_required_operational_fields_are_required(tmp_path: Path, field: str):
    values = {
        "id": "fixture",
        "name": "Fixture",
        "repository": "repo",
        "location": "/fixture",
    }
    del values[field]
    lines = "".join(f"    {key}: {value}\n" for key, value in values.items())

    with pytest.raises(InvalidProjectConfigError):
        ProjectRegistry.from_config(write_config(tmp_path, f"  -\n{lines}"))


def test_context_loads_project_truth_and_closed_tooling_paths(tmp_path: Path):
    registry, project = registry_for(tmp_path)

    context = registry.load_project_context("fixture")

    assert isinstance(context, ProjectContext)
    assert context.id == "fixture"
    assert context.repository == "github.com/example/fixture"
    assert context.declared_repository == "github.com/example/fixture"
    assert context.name == "fixture-project"
    assert context.default_branch == "main"
    assert context.validation_commands == ("uv run pytest",)
    assert context.workflow == "piv"
    assert context.overview == (project / "README.md").read_text()
    assert context.agent_instructions == (project / "AGENTS.md").read_text()
    assert context.tooling_paths == ("pyproject.toml",)
    assert "uv run pytest" not in context.overview


@pytest.mark.parametrize("manifest_change", ["remove", "empty-validation"])
def test_missing_manifest_configuration_does_not_invent_commands(
    tmp_path: Path, manifest_change: str
):
    registry, project = registry_for(tmp_path)
    manifest = project / ".ainative" / "project.yaml"
    if manifest_change == "remove":
        manifest.unlink()
    else:
        manifest.write_text(
            "name: project\nrepository: repo\ndefault_branch: main\nvalidation:\n  commands: []\n",
            encoding="utf-8",
        )

    with pytest.raises(MissingProjectConfigurationError):
        registry.load_project_context("fixture")


def test_named_manifest_is_the_only_manifest_source(tmp_path: Path):
    project = copy_fixture(tmp_path)
    (project / ".ainative" / "project.yaml").unlink()
    custom = project / "config" / "project.yaml"
    custom.parent.mkdir()
    custom.write_text(
        "name: custom\nrepository: custom/repo\ndefault_branch: master\n"
        "validation:\n  commands:\n    - make check\n",
        encoding="utf-8",
    )
    config = write_config(tmp_path, entry(project, extra="    manifest: config/project.yaml\n"))

    context = ProjectRegistry.from_config(config).load_project_context("fixture")

    assert context.name == "custom"
    assert context.default_branch == "master"
    assert context.validation_commands == ("make check",)
    assert context.declared_repository == "custom/repo"


def test_named_missing_manifest_does_not_fall_back(tmp_path: Path):
    project = copy_fixture(tmp_path)
    config = write_config(tmp_path, entry(project, extra="    manifest: missing.yaml\n"))

    with pytest.raises(MissingProjectConfigurationError):
        ProjectRegistry.from_config(config).load_project_context("fixture")


def test_project_branch_overrides_operational_branch(tmp_path: Path):
    registry, _ = registry_for(tmp_path, extra="    default_branch: main\n")
    assert registry.load_project_context("fixture").default_branch == "main"

    project = registry.get_project("fixture").location
    (project / ".ainative" / "project.yaml").write_text(
        "name: fixture\nrepository: repo\ndefault_branch: master\n"
        "validation:\n  commands:\n    - check\n",
        encoding="utf-8",
    )
    assert registry.load_project_context("fixture").default_branch == "master"


def test_malformed_manifest_is_distinct_from_missing_configuration(tmp_path: Path):
    registry, project = registry_for(tmp_path)
    (project / ".ainative" / "project.yaml").write_text("name: [broken\n", encoding="utf-8")

    with pytest.raises(MalformedManifestError):
        registry.load_project_context("fixture")


@pytest.mark.parametrize("manifest", ["/tmp/project.yaml", "a/../../project.yaml"])
def test_manifest_escape_is_rejected(tmp_path: Path, manifest: str):
    project = copy_fixture(tmp_path)
    config = write_config(tmp_path, entry(project, extra=f"    manifest: {manifest}\n"))

    with pytest.raises((InvalidProjectConfigError, UnsafePathError)):
        ProjectRegistry.from_config(config).load_project_context("fixture")


def test_ai_context_pointer_is_required_and_must_stay_in_root(tmp_path: Path):
    project = copy_fixture(tmp_path)
    manifest = project / ".ainative" / "project.yaml"
    manifest.write_text(
        "name: fixture\nrepository: repo\ndefault_branch: main\n"
        "validation:\n  commands:\n    - check\n"
        "ai:\n  context:\n    - docs/context.md\n",
        encoding="utf-8",
    )
    registry = ProjectRegistry.from_config(write_config(tmp_path, entry(project)))
    with pytest.raises(MissingProjectConfigurationError):
        registry.load_project_context("fixture")

    manifest.write_text(
        "name: fixture\nrepository: repo\ndefault_branch: main\n"
        "validation:\n  commands:\n    - check\n"
        "ai:\n  context:\n    - ../outside.md\n",
        encoding="utf-8",
    )
    with pytest.raises(UnsafePathError):
        registry.load_project_context("fixture")


def _control_plane_files() -> list[Path]:
    tests = Path(__file__).parent
    files: list[Path] = []
    for path in PACKAGE_ROOT.rglob("*"):
        if not path.is_file() or any(part in _SKIP_CONTROL_PLANE for part in path.parts):
            continue
        if path.is_relative_to(tests):
            continue
        files.append(path)
    return files


def test_load_does_not_copy_project_knowledge_into_control_plane(tmp_path: Path):
    registry, _project = registry_for(tmp_path)
    registry.list_projects()
    registry.resolve_eligible_project("fixture")
    context = registry.load_project_context("fixture")
    markers = [
        text
        for text in (
            context.overview,
            context.agent_instructions,
            context.architecture,
            context.contributing,
        )
        if text
    ]

    leaked = [
        path
        for path in _control_plane_files()
        if any(marker in path.read_text(encoding="utf-8", errors="ignore") for marker in markers)
    ]
    assert leaked == []


def test_conventional_slot_continues_when_candidate_is_not_a_file(tmp_path: Path):
    registry, project = registry_for(tmp_path)
    (project / "README.md").unlink()
    (project / "README.md").mkdir()
    (project / "README").write_text("fallback overview", encoding="utf-8")
    (project / "AGENTS.md").unlink()
    (project / "AGENTS.md").mkdir()
    (project / "CLAUDE.md").write_text("fallback agent", encoding="utf-8")
    (project / "docs").mkdir()
    (project / "docs" / "architecture.md").mkdir()
    (project / "ARCHITECTURE.md").write_text("fallback architecture", encoding="utf-8")

    context = registry.load_project_context("fixture")

    assert context.overview == "fallback overview"
    assert context.agent_instructions == "fallback agent"
    assert context.architecture == "fallback architecture"


def test_declared_native_ids_resolve_to_the_operational_id(tmp_path: Path):
    registry, _ = registry_for(tmp_path, extra="    kanban_project_ids:\n      - p_fixture\n")

    assert registry.canonical_id("fixture") == "fixture"
    assert registry.canonical_id("p_fixture") == "fixture"
    assert registry.get_project("p_fixture").id == "fixture"
    assert registry.resolve_eligible_project("p_fixture").id == "fixture"
    assert registry.load_project_context("p_fixture").id == "fixture"


def test_scalar_alias_is_normalized(tmp_path: Path):
    registry, _ = registry_for(tmp_path, extra="    kanban_project_ids: p_fixture\n")

    assert registry.get_project("fixture").kanban_project_ids == ("p_fixture",)
    assert registry.canonical_id("p_fixture") == "fixture"


@pytest.mark.parametrize("candidate", ["p_fixtur", "fixtur", "Fixture", "", "p_fixture/x"])
def test_near_miss_and_unknown_aliases_do_not_resolve(tmp_path: Path, candidate: str):
    registry, _ = registry_for(tmp_path, extra="    kanban_project_ids:\n      - p_fixture\n")

    with pytest.raises(UnknownProjectError):
        registry.canonical_id(candidate)
    with pytest.raises(UnknownProjectError):
        registry.get_project(candidate)
