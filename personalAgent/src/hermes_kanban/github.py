"""Orchestrator-owned GitHub publish seam (simulated host + live git/gh)."""

from __future__ import annotations

import json
import os
import re
import subprocess
from dataclasses import dataclass, field
from pathlib import Path
from typing import Protocol
from urllib.parse import urlparse

from .orchestrator import OrchestratorError
from .workspace import WorkspaceManager, _git, _porcelain

PR_SECTION_LABELS = (
    "Summary",
    "Changes",
    "Validation performed",
    "Known limitations",
    "Task reference",
)

_FORBIDDEN_ACTIONS = frozenset({"merge", "approve", "deploy", "protected-push"})
_FORBIDDEN_GIT_FLAGS = ("--force", "--force-with-lease", "--amend")
_GITHUB_SSH = re.compile(r"^git@github\.com:[^/\s]+/[^/\s]+(?:\.git)?$")
_GITHUB_SSH_URI = re.compile(r"^ssh://git@github\.com/[^/\s]+/[^/\s]+(?:\.git)?$")


class ForbiddenGitHubActionError(OrchestratorError):
    """Merge, approve-as-human, deploy, protected-push, amend, or force-push."""


class PublishError(OrchestratorError):
    """GitHub publish failed with a closed-set class (TRANSIENT | NON_RETRYABLE)."""

    def __init__(self, message: str, *, failure_class: str) -> None:
        super().__init__(message)
        self.failure_class = failure_class


@dataclass(frozen=True)
class PullRequestIdentity:
    number: int
    html_url: str


class GitHost(Protocol):
    def assert_remote_allowed(self, remote_url: str | None) -> None: ...

    def ensure_commit(
        self, copy: Path, branch: str, default_branch: str, task_id: str
    ) -> None: ...

    def push_feature_branch(
        self, copy: Path, branch: str, remote_url: str | None
    ) -> None: ...

    def upsert_pull_request(
        self,
        *,
        copy: Path,
        head: str,
        base: str,
        title: str,
        body: str,
    ) -> PullRequestIdentity: ...

    def forbidden(self, action: str) -> None: ...


def assert_github_ssh_url(remote_url: str | None) -> None:
    """Refuse HTTPS, GHES, GitLab, and any host that is not github.com SSH. Do not rewrite."""
    url = (remote_url or "").strip()
    if _GITHUB_SSH.fullmatch(url) or _GITHUB_SSH_URI.fullmatch(url):
        return
    raise PublishError(
        f"remote is not github.com SSH: {url or '(missing)'}",
        failure_class="NON_RETRYABLE",
    )


def forbidden(action: str) -> None:
    name = (action or "").strip().lower()
    if name not in _FORBIDDEN_ACTIONS:
        name = action or "unknown"
    raise ForbiddenGitHubActionError(f"forbidden GitHub action: {name}")


def assert_pr_body(body: str) -> None:
    missing = [label for label in PR_SECTION_LABELS if f"## {label}" not in body]
    if missing:
        raise PublishError(
            f"pull request body missing sections: {', '.join(missing)}",
            failure_class="NON_RETRYABLE",
        )


def build_pull_request(
    *,
    task_id: str,
    title_source: str,
    summary: str,
    changes: str,
    validation: str,
    limitations: str,
    branch: str,
) -> tuple[str, str]:
    title = f"{title_source} ({task_id})".strip()
    body = (
        f"## Summary\n{summary}\n\n"
        f"## Changes\n{changes}\n\n"
        f"## Validation performed\n{validation}\n\n"
        f"## Known limitations\n{limitations}\n\n"
        f"## Task reference\n{task_id}\n"
        f"Branch `{branch}`.\n"
    )
    assert_pr_body(body)
    return title, body


def _reject_forbidden_git(args: tuple[str, ...]) -> None:
    for flag in _FORBIDDEN_GIT_FLAGS:
        if flag in args or any(part.startswith("--force") for part in args):
            raise ForbiddenGitHubActionError(f"forbidden git flag: {args}")


def _git_safe(copy: Path, *args: str, argv_log: list[tuple[str, ...]] | None = None) -> str:
    _reject_forbidden_git(args)
    if argv_log is not None:
        argv_log.append(args)
    return _git(copy, *args)


def ensure_commit(
    copy: Path,
    branch: str,
    default_branch: str,
    task_id: str,
    *,
    argv_log: list[tuple[str, ...]] | None = None,
) -> None:
    """At most one new commit. Never amend. Empty or dirty-no-intent fails visibly."""
    WorkspaceManager.assert_publish_allowed(
        None,  # type: ignore[arg-type]
        branch,
        default_branch=default_branch,
    )
    head = _git_safe(copy, "rev-parse", "--abbrev-ref", "HEAD", argv_log=argv_log)
    if head != branch:
        raise PublishError(
            f"HEAD is {head}, expected {branch}",
            failure_class="NON_RETRYABLE",
        )
    ahead = int(
        _git_safe(
            copy,
            "rev-list",
            "--count",
            f"{default_branch}..HEAD",
            argv_log=argv_log,
        )
        or "0"
    )
    dirty = _porcelain(copy)
    if ahead == 0 and not dirty:
        raise PublishError("nothing to publish", failure_class="NON_RETRYABLE")
    if not dirty:
        return
    _git_safe(copy, "add", "-A", argv_log=argv_log)
    cached = subprocess.run(
        ["git", "-C", str(copy), "diff", "--cached", "--quiet"],
        capture_output=True,
        check=False,
    )
    if cached.returncode == 0:
        raise PublishError("dirty tree has no reviewable intent", failure_class="NON_RETRYABLE")
    _git_safe(copy, "commit", "-m", f"task {task_id}", argv_log=argv_log)


@dataclass
class MemoryGitHost:
    """In-process pushes/PRs. MUST NOT contact github.com. Skips live URL enforcement."""

    pushes: list[tuple[Path, str, str | None]] = field(default_factory=list)
    upserts: list[tuple[str, str, str]] = field(default_factory=list)
    pull_requests: dict[str, PullRequestIdentity] = field(default_factory=dict)
    titles: dict[str, str] = field(default_factory=dict)
    bodies: dict[str, str] = field(default_factory=dict)
    git_argv: list[tuple[str, ...]] = field(default_factory=list)
    push_errors: list[BaseException] = field(default_factory=list)
    _next_number: int = 1

    def assert_remote_allowed(self, remote_url: str | None) -> None:
        return

    def ensure_commit(
        self, copy: Path, branch: str, default_branch: str, task_id: str
    ) -> None:
        ensure_commit(copy, branch, default_branch, task_id, argv_log=self.git_argv)

    def push_feature_branch(
        self, copy: Path, branch: str, remote_url: str | None
    ) -> None:
        if self.push_errors:
            raise self.push_errors.pop(0)
        WorkspaceManager.assert_publish_allowed(
            None,  # type: ignore[arg-type]
            branch,
            default_branch="main",
        )
        self.pushes.append((copy, branch, remote_url))

    def upsert_pull_request(
        self,
        *,
        copy: Path,
        head: str,
        base: str,
        title: str,
        body: str,
    ) -> PullRequestIdentity:
        assert_pr_body(body)
        self.upserts.append((head, title, body))
        existing = self.pull_requests.get(head)
        if existing is None:
            identity = PullRequestIdentity(
                self._next_number,
                f"https://github.com/example/fixture/pull/{self._next_number}",
            )
            self._next_number += 1
            self.pull_requests[head] = identity
        else:
            identity = existing
        self.titles[head] = title
        self.bodies[head] = body
        return identity

    def forbidden(self, action: str) -> None:
        forbidden(action)


class LiveGitHost:
    """git push of the feature ref + gh pr create/edit/list. Auth from agent or env."""

    def __init__(self) -> None:
        self.git_argv: list[tuple[str, ...]] = []

    def assert_remote_allowed(self, remote_url: str | None) -> None:
        assert_github_ssh_url(remote_url)

    def ensure_commit(
        self, copy: Path, branch: str, default_branch: str, task_id: str
    ) -> None:
        ensure_commit(copy, branch, default_branch, task_id, argv_log=self.git_argv)

    def push_feature_branch(
        self, copy: Path, branch: str, remote_url: str | None
    ) -> None:
        url = remote_url or _origin_url(copy)
        self.assert_remote_allowed(url)
        WorkspaceManager.assert_publish_allowed(
            None,  # type: ignore[arg-type]
            branch,
            default_branch="main",
        )
        remote = _origin_name(copy)
        self._git(copy, "push", remote, f"HEAD:refs/heads/{branch}")

    def upsert_pull_request(
        self,
        *,
        copy: Path,
        head: str,
        base: str,
        title: str,
        body: str,
    ) -> PullRequestIdentity:
        assert_pr_body(body)
        listed = self._gh(
            copy,
            "pr",
            "list",
            "--head",
            head,
            "--base",
            base,
            "--json",
            "number,url",
        )
        rows = json.loads(listed or "[]")
        if rows:
            number = int(rows[0]["number"])
            self._gh(
                copy,
                "pr",
                "edit",
                str(number),
                "--title",
                title,
                "--body",
                body,
            )
            html_url = str(rows[0].get("url") or "")
            if not html_url:
                viewed = json.loads(
                    self._gh(copy, "pr", "view", str(number), "--json", "number,url") or "{}"
                )
                html_url = str(viewed.get("url") or "")
            return PullRequestIdentity(number, html_url)
        created = self._gh(
            copy,
            "pr",
            "create",
            "--title",
            title,
            "--body",
            body,
            "--base",
            base,
            "--head",
            head,
        )
        html_url = created.strip().splitlines()[-1] if created.strip() else ""
        number = _pr_number_from_url(html_url)
        return PullRequestIdentity(number, html_url)

    def forbidden(self, action: str) -> None:
        forbidden(action)

    def _git(self, copy: Path, *args: str) -> str:
        return _git_safe(copy, *args, argv_log=self.git_argv)

    def _gh(self, copy: Path, *args: str) -> str:
        # GH_TOKEN / GH_HOST stay env-only (agent or mounted secret). Do not persist them into Git.
        env = os.environ.copy()
        result = subprocess.run(
            ["gh", *args],
            cwd=copy,
            check=True,
            capture_output=True,
            text=True,
            env=env,
        )
        return result.stdout.strip()


def _origin_name(copy: Path) -> str:
    remotes = [line for line in _git(copy, "remote").splitlines() if line]
    if not remotes:
        raise PublishError("no git remote", failure_class="NON_RETRYABLE")
    return "origin" if "origin" in remotes else remotes[0]


def _origin_url(copy: Path) -> str | None:
    try:
        return _git(copy, "remote", "get-url", _origin_name(copy)) or None
    except (OSError, subprocess.CalledProcessError, PublishError):
        return None


def _pr_number_from_url(html_url: str) -> int:
    parsed = urlparse(html_url)
    match = re.search(r"/pull/(\d+)", parsed.path or html_url)
    if not match:
        raise PublishError("incomplete pull request identity", failure_class="NON_RETRYABLE")
    return int(match.group(1))
