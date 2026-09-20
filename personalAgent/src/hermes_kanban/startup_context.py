"""Exact-path startup context loading and safe diagnostics."""

from __future__ import annotations

import hashlib
import json
import os
from collections.abc import Mapping
from dataclasses import dataclass, field
from pathlib import Path
from typing import Literal

from .projects import _parse_document, _SubsetYamlError

ContextRole = Literal["hermes_instructions", "system", "user"]
ContextPrecedenceLayer = Literal[
    "platform_safety",
    "hermes_instructions",
    "runtime_configuration",
    "system",
    "project_instructions",
    "user",
    "current_task",
]
PRECEDENCE_ORDER: tuple[str, ...] = (
    "platform_safety",
    "hermes_instructions",
    "runtime_configuration",
    "system",
    "project_instructions",
    "user",
    "current_task",
)
CONTEXT_ROLES: tuple[ContextRole, ...] = ("hermes_instructions", "system", "user")


class StartupContextError(RuntimeError):
    """Raised when the exact startup context cannot be loaded safely."""

    def __init__(self, role: str, configured_path: str, reason: str) -> None:
        self.role = role
        self.configured_path = configured_path
        self.reason = reason
        super().__init__(f"startup context {role} at {configured_path}: {reason}")


StartupContextLoadError = StartupContextError


@dataclass(frozen=True)
class StartupContextRegistration:
    """Metadata-only identity for one source file loaded at startup."""

    role: ContextRole
    configured_path: Path
    resolved_path: Path
    revision: str

    @property
    def path(self) -> Path:
        """Return the exact configured path used for diagnostics."""
        return self.configured_path


@dataclass(frozen=True)
class LoadedStartupContext:
    """One context file body retained only for the current Hermes process."""

    role: ContextRole
    text: str


@dataclass(frozen=True)
class StartupContextSnapshot:
    """The process-local context text and its separate metadata view."""

    files: Mapping[ContextRole, str]
    registrations: tuple[StartupContextRegistration, ...]

    def text_for(self, role: ContextRole) -> str:
        """Return one loaded body for Hermes-only startup/planning use."""
        return self.files[role]

    @property
    def texts(self) -> Mapping[ContextRole, str]:
        """Return the in-memory text mapping without registration metadata."""
        return self.files


@dataclass(frozen=True)
class StartupDiagnostic:
    """Secret-safe startup locations, identities, and context revisions."""

    ainative_root: Path
    available_agents: tuple[str, ...]
    configured_projects: tuple[str, ...]
    workspace_root: Path
    active_harness: str
    persistent_state_path: Path
    context_registrations: tuple[StartupContextRegistration, ...]
    project_kanban_ids: Mapping[str, tuple[str, ...]] = field(default_factory=dict)

    def to_dict(self) -> dict[str, object]:
        """Return only safe diagnostic metadata suitable for JSON output."""
        return {
            "ainative_root": str(self.ainative_root),
            "available_agents": list(self.available_agents),
            "configured_projects": list(self.configured_projects),
            "workspace_root": str(self.workspace_root),
            "active_harness": self.active_harness,
            "persistent_state_path": str(self.persistent_state_path),
            "project_kanban_ids": {
                project: list(aliases) for project, aliases in self.project_kanban_ids.items()
            },
            "context_registrations": [
                {
                    "role": registration.role,
                    "path": str(registration.configured_path),
                    "revision": registration.revision,
                }
                for registration in self.context_registrations
            ],
        }

    def render(self) -> str:
        """Render the safe diagnostic without any registered file body."""
        return json.dumps(self.to_dict(), indent=2, sort_keys=True)


def _context_error(role: str, path: Path, reason: str) -> StartupContextError:
    return StartupContextError(role, str(path), reason)


def _configured_context_paths(config_path: Path) -> dict[ContextRole, Path]:
    """Parse and validate the exact closed set of configured context roles."""
    try:
        document = _parse_document(config_path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, _SubsetYamlError) as exc:
        raise StartupContextError("configuration", str(config_path), "cannot read config") from exc
    raw_context = document.get("context")
    if not isinstance(raw_context, dict):
        raise StartupContextError("configuration", str(config_path), "context is required")
    actual_roles = set(raw_context)
    expected_roles = set(CONTEXT_ROLES)
    if actual_roles != expected_roles:
        missing = sorted(expected_roles - actual_roles)
        extra = sorted(actual_roles - expected_roles)
        details = []
        if missing:
            details.append(f"missing roles: {', '.join(missing)}")
        if extra:
            details.append(f"unexpected roles: {', '.join(extra)}")
        raise StartupContextError("configuration", str(config_path), "; ".join(details))

    paths: dict[ContextRole, Path] = {}
    for role in CONTEXT_ROLES:
        raw_path = raw_context[role]
        if not isinstance(raw_path, str) or not raw_path.strip():
            raise StartupContextError(role, str(raw_path), "path is empty")
        value = raw_path.strip()
        path = Path(value)
        if not path.is_absolute():
            raise _context_error(role, path, "path is not absolute")
        if value.startswith(("/Users/", "/Volumes/")):
            raise _context_error(role, path, "host-only path")
        paths[role] = path
    return paths


def _read_context_file(role: ContextRole, configured_path: Path) -> tuple[Path, bytes, str]:
    """Read one exact path and return its resolved path, bytes, and UTF-8 text."""
    resolved = configured_path.resolve(strict=False)
    if not configured_path.exists():
        raise _context_error(role, configured_path, "missing")
    if not configured_path.is_file():
        raise _context_error(role, configured_path, "directory or not a regular file")
    try:
        mode = configured_path.stat().st_mode
    except OSError as exc:
        raise _context_error(role, configured_path, "not readable") from exc
    if not os.access(configured_path, os.R_OK) or mode & 0o444 == 0:
        raise _context_error(role, configured_path, "not readable")
    try:
        data = configured_path.read_bytes()
    except OSError as exc:
        raise _context_error(role, configured_path, "not readable") from exc
    try:
        text = data.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise _context_error(role, configured_path, "invalid UTF-8") from exc
    if not text.strip():
        raise _context_error(role, configured_path, "empty")
    return resolved, data, text


def load_startup_context(config_path: Path) -> StartupContextSnapshot:
    """Load all three registered files once from their exact configured paths."""
    paths = _configured_context_paths(config_path)
    registrations: list[StartupContextRegistration] = []
    texts: dict[ContextRole, str] = {}
    resolved_roles: dict[Path, ContextRole] = {}
    for role in CONTEXT_ROLES:
        configured_path = paths[role]
        resolved, data, text = _read_context_file(role, configured_path)
        previous_role = resolved_roles.get(resolved)
        if previous_role is not None:
            raise _context_error(
                role, configured_path, f"duplicate registration with {previous_role}"
            )
        resolved_roles[resolved] = role
        texts[role] = text
        registrations.append(
            StartupContextRegistration(
                role=role,
                configured_path=configured_path,
                resolved_path=resolved,
                revision=hashlib.sha256(data).hexdigest(),
            )
        )
    return StartupContextSnapshot(files=texts, registrations=tuple(registrations))


def resolve_precedence[CandidateT](candidates: Mapping[str, CandidateT]) -> CandidateT | None:
    """Return the first non-None candidate in the fixed authority order."""
    for layer in PRECEDENCE_ORDER:
        candidate = candidates.get(layer)
        if candidate is not None:
            return candidate
    return None


def resolve_context_precedence[CandidateT](
    candidates: Mapping[str, CandidateT],
) -> CandidateT | None:
    """Compatibility name for the pure context precedence resolver."""
    return resolve_precedence(candidates)
