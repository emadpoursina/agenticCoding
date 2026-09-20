import shutil
import subprocess
from dataclasses import fields
from pathlib import Path

import pytest

from hermes_kanban.projects import (
    DisabledProjectError,
    InvalidProjectLocationError,
    UnknownProjectError,
)
from hermes_kanban.workspace import (
    CorrelationIdentity,
    GitRefreshError,
    InvalidProjectRepositoryError,
    InvalidTaskIdError,
    InvalidWorkspaceError,
    InvalidWorkspaceRootError,
    MissingDefaultBranchError,
    PreparedWorkspace,
    ProtectedBranchError,
    WorkspaceError,
    WorkspaceInspection,
    WorkspaceManager,
    load_workspace_root,
)

FIXTURE_ROOT = Path(__file__).parent / "fixtures" / "projects" / "standard"
PACKAGE_ROOT = Path(__file__).resolve().parents[1]


def git(*args: str, cwd: Path) -> str:
    result = subprocess.run(
        ["git", *args], cwd=cwd, check=True, capture_output=True, text=True
    )
    return result.stdout.strip()


def copy_fixture(tmp_path: Path, name: str = "enrolled") -> Path:
    project = tmp_path / name
    shutil.copytree(FIXTURE_ROOT, project)
    return project


def git_init_commit(project: Path, *, branch: str = "main") -> None:
    git("init", "-b", branch, cwd=project)
    git("config", "user.email", "tests@example.com", cwd=project)
    git("config", "user.name", "Tests", cwd=project)
    git("add", ".", cwd=project)
    git("commit", "-m", "fixture", cwd=project)


def write_config(
    tmp_path: Path,
    workspace_root: Path,
    location: Path,
    *,
    extra: str = "",
    project_id: str = "fixture",
) -> Path:
    config = tmp_path / "config.yaml"
    config.write_text(
        "workspace:\n"
        f"  root: {workspace_root}\n"
        "projects:\n"
        f"  - id: {project_id}\n"
        "    name: Fixture\n"
        "    repository: github.com/example/fixture\n"
        f"    location: {location}\n"
        f"{extra}",
        encoding="utf-8",
    )
    return config


def make_env(
    tmp_path: Path,
    *,
    extra: str = "",
    init_git: bool = True,
    branch: str = "main",
) -> tuple[WorkspaceManager, Path, Path]:
    workspace_root = tmp_path / "ws"
    workspace_root.mkdir()
    project = copy_fixture(tmp_path)
    if init_git:
        git_init_commit(project, branch=branch)
    write_config(tmp_path, workspace_root, project, extra=extra)
    return WorkspaceManager.from_config(tmp_path / "config.yaml"), project, workspace_root


def test_default_config_keeps_configured_managed_set_and_root():
    text = (PACKAGE_ROOT / "config" / "default.yaml").read_text(encoding="utf-8")
    assert "workspace:" in text
    assert "root: /workspaces" in text
    assert "overlay_dir: /var/lib/hermes-kanban" in text
    assert "max_concurrent_tasks: 1" in text
    assert "id: ich-mag-dich" in text
    assert "name: emadpoursina/ich-mag-dich" in text
    assert "location: /workspaces/ich-mag-dich" in text
    assert "id: sandbox" not in text
    assert "hermes-v0-sandbox" not in text
    assert "$HOME" not in text
    assert "WORKSPACE_ROOT" not in text


def test_boot_script_gives_overlay_dir_to_hermes():
    text = (
        PACKAGE_ROOT / "docker" / "cont-init.d" / "90-ssh-agent-access.sh"
    ).read_text(encoding="utf-8")
    assert "mkdir -p /var/lib/hermes-kanban" in text
    assert "chown -R hermes:hermes /var/lib/hermes-kanban" in text
    assert 'PI_STORE_DIR="${PI_CODING_AGENT_DIR:-/opt/data/pi-agent}"' in text
    assert 'chown -R hermes:hermes "$PI_STORE_DIR"' in text


def test_load_workspace_root_reads_only_workspace_block(tmp_path: Path):
    root = tmp_path / "only-root"
    root.mkdir()
    config = tmp_path / "config.yaml"
    config.write_text(
        f"ainative:\n  path: /ignored\nworkspace:\n  root: {root}\nprojects: []\n",
        encoding="utf-8",
    )
    assert load_workspace_root(config) == root


@pytest.mark.parametrize("kind", ["missing", "empty", "file", "absent-key"])
def test_invalid_workspace_root_has_no_substitute(tmp_path: Path, kind: str):
    config = tmp_path / "config.yaml"
    if kind == "missing":
        target = tmp_path / "no-such-config.yaml"
    elif kind == "empty":
        config.write_text("workspace:\n  root: \nprojects: []\n", encoding="utf-8")
        target = config
    elif kind == "file":
        not_dir = tmp_path / "not-a-dir"
        not_dir.write_text("x", encoding="utf-8")
        config.write_text(f"workspace:\n  root: {not_dir}\nprojects: []\n", encoding="utf-8")
        target = config
    else:
        config.write_text("projects: []\n", encoding="utf-8")
        target = config

    with pytest.raises(InvalidWorkspaceRootError):
        load_workspace_root(target)
    with pytest.raises(InvalidWorkspaceRootError):
        WorkspaceManager.from_config(target)


def test_prepare_creates_isolated_worktree_without_moving_enrolled(tmp_path: Path):
    manager, project, workspace_root = make_env(tmp_path)
    enrolled_before = git("rev-parse", "--abbrev-ref", "HEAD", cwd=project)

    prepared = manager.prepare_workspace("fixture", "123")

    assert prepared.path == (workspace_root / "fixture" / "123").resolve()
    assert prepared.path.is_dir()
    assert prepared.branch == "feature/task-123"
    assert prepared.project_id == "fixture"
    assert prepared.task_id == "123"
    assert prepared.workspace_id == "ws-fixture-123"
    assert prepared.execution_id
    assert prepared.worker_id is None
    assert prepared.remote is None
    assert git("rev-parse", "--abbrev-ref", "HEAD", cwd=prepared.path) == "feature/task-123"
    assert git("rev-parse", "--abbrev-ref", "HEAD", cwd=project) == enrolled_before == "main"
    assert git("rev-parse", "--is-inside-work-tree", cwd=prepared.path) == "true"


def test_two_tasks_get_different_paths(tmp_path: Path):
    manager, _project, workspace_root = make_env(tmp_path)
    first = manager.prepare_workspace("fixture", "123")
    second = manager.prepare_workspace("fixture", "456")
    assert first.path != second.path
    assert first.path == (workspace_root / "fixture" / "123").resolve()
    assert second.path == (workspace_root / "fixture" / "456").resolve()


@pytest.mark.parametrize("task_id", ["", "/", "\\", "..", "../x", "a/b", r"a\b"])
def test_path_like_task_id_is_rejected_before_join(tmp_path: Path, task_id: str):
    manager, _project, workspace_root = make_env(tmp_path)
    with pytest.raises(InvalidTaskIdError):
        manager.prepare_workspace("fixture", task_id)
    assert list(workspace_root.iterdir()) == []


def test_registry_errors_propagate(tmp_path: Path):
    manager, project, _root = make_env(tmp_path)
    with pytest.raises(UnknownProjectError):
        manager.prepare_workspace("missing", "123")

    write_config(
        tmp_path,
        tmp_path / "ws",
        project,
        extra="    enabled: false\n",
    )
    disabled = WorkspaceManager.from_config(tmp_path / "config.yaml")
    with pytest.raises(DisabledProjectError):
        disabled.prepare_workspace("fixture", "123")

    missing_location = tmp_path / "gone"
    write_config(tmp_path, tmp_path / "ws", missing_location)
    with pytest.raises(InvalidProjectLocationError):
        WorkspaceManager.from_config(tmp_path / "config.yaml").prepare_workspace("fixture", "123")


def test_enrolled_non_git_is_not_initialized(tmp_path: Path):
    manager, project, _root = make_env(tmp_path, init_git=False)
    with pytest.raises(InvalidProjectRepositoryError):
        manager.prepare_workspace("fixture", "123")
    assert not (project / ".git").exists()


def test_missing_default_branch_ref_is_refused(tmp_path: Path):
    manager, _project, _root = make_env(tmp_path, extra="    default_branch: develop\n")
    with pytest.raises(MissingDefaultBranchError):
        manager.prepare_workspace("fixture", "123")


def test_dirty_enrolled_location_still_allows_new_worktree(tmp_path: Path):
    manager, project, _root = make_env(tmp_path)
    (project / "dirty-enrolled.txt").write_text("enrolled dirt", encoding="utf-8")
    prepared = manager.prepare_workspace("fixture", "123")
    assert prepared.path.is_dir()
    assert git("rev-parse", "--abbrev-ref", "HEAD", cwd=project) == "main"


def test_protected_work_and_publish_branches_are_refused(tmp_path: Path):
    manager, project, _root = make_env(
        tmp_path,
        extra="    default_branch: feature/task-123\n",
        branch="feature/task-123",
    )
    enrolled_before = git("rev-parse", "--abbrev-ref", "HEAD", cwd=project)
    with pytest.raises(ProtectedBranchError):
        manager.prepare_workspace("fixture", "123")
    assert git("rev-parse", "--abbrev-ref", "HEAD", cwd=project) == enrolled_before

    with pytest.raises(ProtectedBranchError):
        manager.assert_publish_allowed("main", default_branch="develop")
    with pytest.raises(ProtectedBranchError):
        manager.assert_publish_allowed("master", default_branch="main")
    with pytest.raises(ProtectedBranchError):
        manager.assert_publish_allowed("develop", default_branch="develop")
    with pytest.raises(ProtectedBranchError):
        manager.assert_publish_allowed("", default_branch="main")
    with pytest.raises(ProtectedBranchError):
        manager.assert_publish_allowed("feature/task-123", default_branch="")
    manager.assert_publish_allowed("feature/task-123", default_branch="main")


def test_dirty_same_task_reuse_keeps_files_and_siblings(tmp_path: Path):
    manager, _project, workspace_root = make_env(tmp_path)
    first = manager.prepare_workspace("fixture", "123")
    sibling = manager.prepare_workspace("fixture", "456")
    dirty_file = first.path / "local-change.txt"
    dirty_file.write_text("keep me", encoding="utf-8")

    reused = manager.prepare_workspace("fixture", "123")

    assert reused.path == first.path
    assert dirty_file.read_text(encoding="utf-8") == "keep me"
    assert sibling.path.is_dir()
    assert (workspace_root / "fixture" / "456").is_dir()


def test_feature_branch_checked_out_elsewhere_is_not_shared(tmp_path: Path):
    manager, project, workspace_root = make_env(tmp_path)
    other = tmp_path / "other-copy"
    git("worktree", "add", "-b", "feature/task-123", str(other), "main", cwd=project)
    with pytest.raises(InvalidWorkspaceError):
        manager.prepare_workspace("fixture", "123")
    assert not (workspace_root / "fixture" / "123").exists()


def test_inspect_reports_clean_and_dirty(tmp_path: Path):
    manager, _project, _root = make_env(tmp_path)
    prepared = manager.prepare_workspace("fixture", "123")

    clean = manager.inspect_workspace("fixture", "123")
    assert isinstance(clean, WorkspaceInspection)
    assert clean.path == prepared.path
    assert clean.branch == "feature/task-123"
    assert clean.dirty is False
    assert clean.changes == ()

    (prepared.path / "edited.txt").write_text("change", encoding="utf-8")
    dirty = manager.inspect_workspace("fixture", "123")
    assert dirty.dirty is True
    assert dirty.changes
    assert any("edited.txt" in line for line in dirty.changes)


def test_inspect_rejects_missing_and_invalid_copies(tmp_path: Path):
    manager, _project, workspace_root = make_env(tmp_path)
    with pytest.raises(InvalidWorkspaceError):
        manager.inspect_workspace("fixture", "123")

    bogus = workspace_root / "fixture" / "123"
    bogus.mkdir(parents=True)
    (bogus / "not-git.txt").write_text("no", encoding="utf-8")
    with pytest.raises(InvalidWorkspaceError):
        manager.inspect_workspace("fixture", "123")
    assert (bogus / "not-git.txt").exists()


def test_fetch_failure_is_git_refresh_error(tmp_path: Path):
    manager, project, _root = make_env(tmp_path)
    empty = tmp_path / "empty-origin"
    empty.mkdir()
    git("init", "--bare", "-b", "main", cwd=empty)
    git("remote", "add", "origin", str(empty), cwd=project)
    with pytest.raises(GitRefreshError):
        manager.prepare_workspace("fixture", "123")


def test_identity_fields_and_clean_reuse(tmp_path: Path):
    manager, _project, _root = make_env(tmp_path)
    first = manager.prepare_workspace("fixture", "123")
    other = manager.prepare_workspace("fixture", "456", worker_id="worker-a")
    reused = manager.prepare_workspace("fixture", "123", worker_id="")
    named = manager.prepare_workspace("fixture", "456", worker_id="worker-a")

    assert first.task_id and first.execution_id and first.project_id and first.workspace_id
    assert first.workspace_id != other.workspace_id
    assert first.execution_id != other.execution_id
    assert reused.path == first.path
    assert reused.workspace_id == first.workspace_id == "ws-fixture-123"
    assert reused.execution_id != first.execution_id
    assert reused.worker_id is None
    assert other.worker_id == "worker-a"
    assert named.worker_id == "worker-a"
    assert named.workspace_id == other.workspace_id
    assert named.execution_id != other.execution_id

    identity_names = {item.name for item in fields(PreparedWorkspace)}
    inspect_names = {item.name for item in fields(WorkspaceInspection)}
    corr_names = {item.name for item in fields(CorrelationIdentity)}
    forbidden = {"reasoning", "transcript", "chain_of_thought", "diff", "instructions"}
    assert not identity_names & forbidden
    assert not inspect_names & forbidden
    assert not corr_names & forbidden
    assert issubclass(InvalidTaskIdError, WorkspaceError)


def test_prepare_records_origin_after_successful_fetch(tmp_path: Path):
    manager, project, _root = make_env(tmp_path)
    bare = tmp_path / "origin.git"
    bare.mkdir()
    git("init", "--bare", "-b", "main", cwd=bare)
    git("remote", "add", "origin", str(bare), cwd=project)
    git("push", "-u", "origin", "main", cwd=project)
    prepared = manager.prepare_workspace("fixture", "123")
    assert prepared.remote == str(bare)
    assert git("rev-parse", "--abbrev-ref", "HEAD", cwd=project) == "main"


def test_prepare_does_not_copy_repo_into_control_plane(tmp_path: Path):
    manager, _project, _root = make_env(tmp_path)
    prepared = manager.prepare_workspace("fixture", "123")
    assert prepared.path.is_relative_to(tmp_path)
    src = PACKAGE_ROOT / "src"
    assert not any(src.rglob(".git"))
    assert not (PACKAGE_ROOT / "kanban.db").exists()
    assert not (PACKAGE_ROOT / "projects.db").exists()


def test_source_never_invokes_forbidden_git():
    source = (PACKAGE_ROOT / "src" / "hermes_kanban" / "workspace.py").read_text(encoding="utf-8")
    for needle in (
        '"push"',
        "'push'",
        '"clone"',
        "'clone'",
        '"init"',
        "'init'",
        '"clean"',
        "'clean'",
        "reset --hard",
        '"reset"',
        "'reset'",
        "worktree remove",
        '"checkout"',
        "'checkout'",
    ):
        assert needle not in source
