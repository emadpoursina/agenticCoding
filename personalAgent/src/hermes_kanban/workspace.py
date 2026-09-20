"""Isolated git worktrees for one enrolled project and one task."""

from __future__ import annotations

import os
import re
import subprocess
import uuid
from dataclasses import dataclass
from pathlib import Path

from .projects import ProjectRegistry, _path_like_id


class WorkspaceError(Exception):
    """Base error for workspace manager failures."""


class InvalidWorkspaceRootError(WorkspaceError):
    """Raised when the configured workspace root cannot be used."""


class InvalidTaskIdError(WorkspaceError):
    """Raised when a task identity is empty or path-like."""


class InvalidProjectRepositoryError(WorkspaceError):
    """Raised when an enrolled location is not a git work tree."""


class MissingDefaultBranchError(WorkspaceError):
    """Raised when the project's default branch is not a ref."""


class ProtectedBranchError(WorkspaceError):
    """Raised when a work or publish branch is a protected name."""


class DirtyWorkspaceError(WorkspaceError):
    """Raised when an existing task copy has uncommitted changes."""


class InvalidWorkspaceError(WorkspaceError):
    """Raised when a working copy is missing, mismatched, or already shared."""


class GitRefreshError(WorkspaceError):
    """Raised when a remote exists and fetch (or its default ref) fails."""


@dataclass(frozen=True)
class PreparedWorkspace:
    """Isolated working copy for one project and one task."""

    path: Path
    branch: str
    project_id: str
    task_id: str
    workspace_id: str
    execution_id: str
    worker_id: str | None
    remote: str | None


@dataclass(frozen=True)
class WorkspaceInspection:
    """Point-in-time branch and dirty status for a working copy."""

    path: Path
    branch: str
    dirty: bool
    changes: tuple[str, ...]


@dataclass(frozen=True)
class CorrelationIdentity:
    """Which run happened where. Not a transcript."""

    task_id: str
    execution_id: str
    project_id: str
    workspace_id: str
    worker_id: str | None


def _readable_directory(path: Path) -> bool:
    if not path.is_dir() or not os.access(path, os.R_OK | os.X_OK):
        return False
    try:
        with os.scandir(path):
            return True
    except OSError:
        return False


# ponytail: line-oriented YAML subset for workspace.root only; no nested YAML.
# Upgrade: owner-approved PyYAML if the workspace: block grows.
def load_workspace_root(config_path: Path) -> Path:
    """Load and validate workspace.root from a caller-supplied YAML path."""
    try:
        lines = config_path.read_text(encoding="utf-8").splitlines()
    except (OSError, UnicodeError) as exc:
        raise InvalidWorkspaceRootError(f"cannot read config: {config_path}") from exc

    values: dict[str, str] = {}
    in_block = False
    for line in lines:
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        if not line[0].isspace():
            if in_block:
                break
            in_block = bool(re.fullmatch(r"workspace\s*:", stripped))
            continue
        if not in_block:
            continue
        match = re.fullmatch(r"\s*([A-Za-z_][\w-]*)\s*:\s*(.*?)\s*", line)
        if match and match.group(1) == "root":
            values["root"] = match.group(2)

    raw = values.get("root", "").strip()
    if not raw:
        raise InvalidWorkspaceRootError("workspace.root is missing or empty")
    root = Path(raw)
    if not _readable_directory(root):
        raise InvalidWorkspaceRootError(f"invalid workspace root: {root}")
    return root


def _git(repo: Path, *args: str) -> str:
    result = subprocess.run(
        ["git", "-C", str(repo), *args],
        check=True,
        capture_output=True,
        text=True,
    )
    return result.stdout.strip()


def _is_git_work_tree(path: Path) -> bool:
    try:
        return _git(path, "rev-parse", "--is-inside-work-tree") == "true"
    except (OSError, subprocess.CalledProcessError):
        return False


def _has_ref(repo: Path, ref: str) -> bool:
    try:
        _git(repo, "show-ref", "--verify", "--quiet", ref)
        return True
    except (OSError, subprocess.CalledProcessError):
        return False


def _resolved_git_path(repo: Path, raw: str) -> Path:
    path = Path(raw)
    if not path.is_absolute():
        path = repo / path
    return path.resolve()


def _git_common_dir(repo: Path) -> Path:
    return _resolved_git_path(repo, _git(repo, "rev-parse", "--git-common-dir"))


def _same_repository(left: Path, right: Path) -> bool:
    try:
        return _git_common_dir(left) == _git_common_dir(right)
    except (OSError, subprocess.CalledProcessError):
        return False


def _porcelain(repo: Path) -> tuple[str, ...]:
    output = _git(repo, "status", "--porcelain")
    return tuple(line for line in output.splitlines() if line)


def _validated_task_id(task_id: str) -> str:
    if not isinstance(task_id, str) or _path_like_id(task_id):
        raise InvalidTaskIdError(f"invalid task id: {task_id}")
    return task_id


def _optional_worker(worker_id: str | None) -> str | None:
    return worker_id if worker_id else None


def _work_branch(task_id: str) -> str:
    return f"feature/task-{task_id}"


def _workspace_id(project_id: str, task_id: str) -> str:
    return f"ws-{project_id}-{task_id}"


def _remote_identity(repo: Path) -> tuple[str | None, str | None]:
    try:
        remotes = [line for line in _git(repo, "remote").splitlines() if line]
    except (OSError, subprocess.CalledProcessError):
        return None, None
    if not remotes:
        return None, None
    name = "origin" if "origin" in remotes else remotes[0]
    try:
        url = _git(repo, "remote", "get-url", name) or None
    except (OSError, subprocess.CalledProcessError):
        url = None
    return name, url


def _branch_checked_out_elsewhere(repo: Path, branch: str, *, except_path: Path | None) -> bool:
    try:
        listing = _git(repo, "worktree", "list", "--porcelain")
    except (OSError, subprocess.CalledProcessError):
        return False
    current: Path | None = None
    want = f"refs/heads/{branch}"
    except_resolved = except_path.resolve() if except_path is not None else None
    for line in listing.splitlines():
        if line.startswith("worktree "):
            current = Path(line.removeprefix("worktree "))
            continue
        if current is None or not line.startswith("branch "):
            continue
        if line.removeprefix("branch ") == want:
            if except_resolved is None or current.resolve() != except_resolved:
                return True
    return False


class WorkspaceManager:
    """Prepare and inspect isolated git worktrees under a configured root."""

    def __init__(self, workspace_root: Path, registry: ProjectRegistry) -> None:
        if not _readable_directory(workspace_root):
            raise InvalidWorkspaceRootError(f"invalid workspace root: {workspace_root}")
        self.workspace_root = workspace_root
        self.registry = registry

    @classmethod
    def from_config(
        cls,
        config_path: Path,
        registry: ProjectRegistry | None = None,
    ) -> WorkspaceManager:
        root = load_workspace_root(config_path)
        return cls(root, registry or ProjectRegistry.from_config(config_path))

    def assert_publish_allowed(self, branch: str, *, default_branch: str) -> None:
        """Refuse protected branch names. Does not publish."""
        protected = not branch or not default_branch or branch in {"main", "master"}
        if protected or branch == default_branch:
            raise ProtectedBranchError(f"protected branch: {branch}")

    def inspect_workspace(self, project_id: str, task_id: str) -> WorkspaceInspection:
        """Report branch and dirty status. Does not repair or publish."""
        copy = self._existing_copy(project_id, task_id)
        branch = _git(copy, "rev-parse", "--abbrev-ref", "HEAD")
        changes = _porcelain(copy)
        return WorkspaceInspection(copy, branch, bool(changes), changes)

    def prepare_workspace(
        self,
        project_id: str,
        task_id: str,
        *,
        worker_id: str | None = None,
    ) -> PreparedWorkspace:
        """Create or reuse an isolated worktree for one eligible project and task."""
        task_id = _validated_task_id(task_id)
        project = self.registry.resolve_eligible_project(project_id)
        repo = project.location
        if not _is_git_work_tree(repo):
            raise InvalidProjectRepositoryError(f"not a git work tree: {repo}")
        if not _has_ref(repo, f"refs/heads/{project.default_branch}"):
            raise MissingDefaultBranchError(
                f"missing default branch: {project.default_branch}"
            )

        remote_name, remote_url = _remote_identity(repo)
        branch = _work_branch(task_id)
        self.assert_publish_allowed(branch, default_branch=project.default_branch)
        copy = self.workspace_root / project.id / task_id
        if copy.exists():
            return self._reuse_or_refuse(
                copy, repo, project.id, task_id, branch, worker_id, remote_url
            )
        if remote_name is not None:
            try:
                _git(repo, "fetch", remote_name)
            except (OSError, subprocess.CalledProcessError) as exc:
                raise GitRefreshError(f"git fetch failed: {remote_name}") from exc
            tracking = f"refs/remotes/{remote_name}/{project.default_branch}"
            if not _has_ref(repo, tracking):
                missing = f"{remote_name}/{project.default_branch}"
                raise GitRefreshError(f"missing remote default: {missing}")
            base = f"{remote_name}/{project.default_branch}"
        else:
            base = project.default_branch
        if _branch_checked_out_elsewhere(repo, branch, except_path=None):
            raise InvalidWorkspaceError(f"branch already checked out: {branch}")
        copy.parent.mkdir(parents=True, exist_ok=True)
        try:
            if _has_ref(repo, f"refs/heads/{branch}"):
                _git(repo, "worktree", "add", str(copy), branch)
            else:
                _git(repo, "worktree", "add", "-b", branch, str(copy), base)
        except (OSError, subprocess.CalledProcessError) as exc:
            raise InvalidWorkspaceError(f"cannot add worktree: {copy}") from exc
        return self._result(copy, branch, project.id, task_id, worker_id, remote_url)

    def recover_workspace(
        self,
        project_id: str,
        task_id: str,
        *,
        workspace_id: str,
        execution_id: str,
        branch: str,
    ) -> PreparedWorkspace:
        """Recover this task's copy or recreate it from a local feature branch."""
        task_id = _validated_task_id(task_id)
        if not isinstance(workspace_id, str) or not workspace_id.strip():
            raise InvalidWorkspaceError("missing workspace identity")
        if not isinstance(execution_id, str) or not execution_id.strip():
            raise InvalidWorkspaceError("missing execution identity")
        project = self.registry.resolve_eligible_project(project_id)
        repo = project.location
        if not _is_git_work_tree(repo):
            raise InvalidProjectRepositoryError(f"not a git work tree: {repo}")
        if not _has_ref(repo, f"refs/heads/{project.default_branch}"):
            raise MissingDefaultBranchError(
                f"missing default branch: {project.default_branch}"
            )
        expected_branch = _work_branch(task_id)
        if branch != expected_branch:
            raise InvalidWorkspaceError(f"workspace branch mismatch: {branch}")
        self.assert_publish_allowed(branch, default_branch=project.default_branch)

        _, remote_url = _remote_identity(repo)
        copy = self.workspace_root / project.id / task_id
        resolved = copy.resolve(strict=False)
        if not resolved.is_relative_to(self.workspace_root.resolve()):
            raise InvalidWorkspaceError(f"invalid workspace: {resolved}")
        if copy.exists():
            if (
                not _is_git_work_tree(resolved)
                or not _same_repository(repo, resolved)
                or _git(resolved, "rev-parse", "--abbrev-ref", "HEAD") != branch
            ):
                raise InvalidWorkspaceError(f"invalid workspace: {resolved}")
            return PreparedWorkspace(
                path=resolved,
                branch=branch,
                project_id=project.id,
                task_id=task_id,
                workspace_id=workspace_id,
                execution_id=execution_id,
                worker_id=None,
                remote=remote_url,
            )

        if not _has_ref(repo, f"refs/heads/{branch}"):
            raise InvalidWorkspaceError(f"missing local feature branch: {branch}")
        if _branch_checked_out_elsewhere(repo, branch, except_path=None):
            raise InvalidWorkspaceError(f"branch already checked out: {branch}")
        try:
            copy.parent.mkdir(parents=True, exist_ok=True)
            _git(repo, "worktree", "add", str(copy), branch)
        except (OSError, subprocess.CalledProcessError) as exc:
            raise InvalidWorkspaceError(f"cannot recover worktree: {copy}") from exc
        return PreparedWorkspace(
            path=copy.resolve(),
            branch=branch,
            project_id=project.id,
            task_id=task_id,
            workspace_id=workspace_id,
            execution_id=execution_id,
            worker_id=None,
            remote=remote_url,
        )

    def _existing_copy(self, project_id: str, task_id: str) -> Path:
        task_id = _validated_task_id(task_id)
        project = self.registry.resolve_eligible_project(project_id)
        copy = (self.workspace_root / project.id / task_id).resolve()
        valid = copy.exists() and _is_git_work_tree(copy)
        if not valid or not _same_repository(project.location, copy):
            raise InvalidWorkspaceError(f"invalid workspace: {copy}")
        return copy

    def _reuse_or_refuse(
        self,
        copy: Path,
        repo: Path,
        project_id: str,
        task_id: str,
        branch: str,
        worker_id: str | None,
        remote_url: str | None,
    ) -> PreparedWorkspace:
        resolved = copy.resolve()
        expected = (self.workspace_root / project_id / task_id).resolve(strict=False)
        if (
            resolved != expected
            or not resolved.is_relative_to(self.workspace_root.resolve())
            or not _is_git_work_tree(resolved)
            or not _same_repository(repo, resolved)
        ):
            raise InvalidWorkspaceError(f"invalid workspace: {resolved}")
        current = _git(resolved, "rev-parse", "--abbrev-ref", "HEAD")
        if current != branch:
            raise InvalidWorkspaceError(f"workspace branch mismatch: {current}")
        return self._result(resolved, branch, project_id, task_id, worker_id, remote_url)

    def _result(
        self,
        copy: Path,
        branch: str,
        project_id: str,
        task_id: str,
        worker_id: str | None,
        remote_url: str | None,
    ) -> PreparedWorkspace:
        return PreparedWorkspace(
            path=copy.resolve(),
            branch=branch,
            project_id=project_id,
            task_id=task_id,
            workspace_id=_workspace_id(project_id, task_id),
            execution_id=uuid.uuid4().hex,
            worker_id=_optional_worker(worker_id),
            remote=remote_url,
        )
