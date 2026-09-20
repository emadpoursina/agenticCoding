"""Configuration-backed project enrollment and in-place project context loading."""

from __future__ import annotations

import os
import re
from dataclasses import dataclass
from pathlib import Path


class ProjectRegistryError(Exception):
    """Base error for project registry failures."""


class InvalidProjectConfigError(ProjectRegistryError):
    """Raised when the managed project configuration is invalid."""


class UnknownProjectError(ProjectRegistryError):
    """Raised when a project identity is not enrolled."""


class DisabledProjectError(ProjectRegistryError):
    """Raised when an enrolled project is disabled."""


class InvalidProjectLocationError(ProjectRegistryError):
    """Raised when an enrolled project location cannot be used."""


class MissingProjectConfigurationError(ProjectRegistryError):
    """Raised when required project-side configuration is unavailable."""


class MalformedManifestError(ProjectRegistryError):
    """Raised when a project manifest is outside the supported subset."""


class UnsafePathError(ProjectRegistryError):
    """Raised when a project-relative path leaves the project root."""


@dataclass(frozen=True)
class ProjectRecord:
    """Operational identity for one explicitly enrolled project."""

    id: str
    name: str
    repository: str
    location: Path
    default_branch: str
    enabled: bool
    settings: dict[str, str]
    manifest: str | None
    kanban_project_ids: tuple[str, ...] = ()


@dataclass(frozen=True)
class ProjectManifest:
    """Project-side structured declarations."""

    name: str
    description: str | None
    repository: str
    default_branch: str
    workflow: str | None
    validation_commands: tuple[str, ...]
    development_commands: tuple[str, ...] | None
    ai_context: tuple[str, ...]


@dataclass(frozen=True)
class ContextFile:
    """One project-relative AI context file and its unmodified text."""

    path: str
    text: str


@dataclass(frozen=True)
class ProjectContext:
    """In-memory project identity and project-side context bundle."""

    id: str
    name: str
    repository: str
    declared_repository: str
    default_branch: str
    location: Path
    workflow: str | None
    validation_commands: tuple[str, ...]
    development_commands: tuple[str, ...] | None
    settings: dict[str, str]
    overview: str | None
    agent_instructions: str | None
    contributing: str | None
    architecture: str | None
    ai_context_files: tuple[ContextFile, ...]
    tooling_paths: tuple[str, ...]


class _SubsetYamlError(ValueError):
    """Internal error for the deliberately small YAML subset."""


@dataclass(frozen=True)
class _YamlLine:
    indent: int
    content: str


_KEY = re.compile(r"^([A-Za-z_][\w-]*):(?:\s*(.*))?$")
_DRIVE_PATH = re.compile(r"^[A-Za-z]:([/\\]|$)")


def _remove_comment(line: str) -> str:
    """Remove comments that begin outside the scalar value."""
    if line.lstrip().startswith("#"):
        return ""
    match = re.search(r"\s+#", line)
    return line[: match.start()] if match else line


def _tokenize(text: str) -> list[_YamlLine]:
    lines: list[_YamlLine] = []
    for raw in text.splitlines():
        if "\t" in raw:
            raise _SubsetYamlError("tabs are not supported")
        uncommented = _remove_comment(raw).rstrip()
        if not uncommented.strip():
            continue
        indent = len(uncommented) - len(uncommented.lstrip(" "))
        if indent % 2:
            raise _SubsetYamlError("indentation must use two spaces")
        lines.append(_YamlLine(indent, uncommented[indent:]))
    return lines


def _scalar(raw: str) -> object:
    value = raw.strip()
    if value == "[]":
        return []
    if value == "{}":
        return {}
    if value.startswith(("[", "{")) or value.endswith(("]", "}")):
        raise _SubsetYamlError("unsupported flow value")
    if value == "true":
        return True
    if value == "false":
        return False
    if value.startswith(("&", "*", "!")) or value in {"|", ">", "|-", ">-"}:
        raise _SubsetYamlError("aliases, tags, and multiline scalars are unsupported")
    if value.startswith(("'", '"')):
        if len(value) < 2 or value[-1] != value[0]:
            raise _SubsetYamlError("unterminated quoted scalar")
        return value[1:-1]
    return value


def _mapping_key(content: str) -> tuple[str, str] | None:
    match = _KEY.fullmatch(content)
    return (match.group(1), match.group(2) or "") if match else None


def _parse_block(lines: list[_YamlLine], index: int, indent: int) -> tuple[object, int]:
    if index >= len(lines) or lines[index].indent != indent:
        raise _SubsetYamlError("unexpected indentation")
    is_list = lines[index].content == "-" or lines[index].content.startswith("- ")
    if is_list:
        result: list[object] = []
        while index < len(lines) and lines[index].indent == indent:
            content = lines[index].content
            if content != "-" and not content.startswith("- "):
                break
            rest = content[1:].strip()
            index += 1
            if not rest:
                if index < len(lines) and lines[index].indent > indent:
                    value, index = _parse_block(lines, index, lines[index].indent)
                else:
                    value = None
                result.append(value)
                continue
            first = _mapping_key(rest)
            if first is None:
                result.append(_scalar(rest))
                if index < len(lines) and lines[index].indent > indent:
                    raise _SubsetYamlError("scalar list item cannot have children")
                continue
            key, raw_value = first
            item: dict[str, object] = {key: _scalar(raw_value) if raw_value else None}
            if index < len(lines) and lines[index].indent > indent:
                child_indent = lines[index].indent
                if child_indent != indent + 2:
                    raise _SubsetYamlError("nested indentation must increase by two")
                extra, index = _parse_block(lines, index, child_indent)
                if not isinstance(extra, dict):
                    raise _SubsetYamlError("mapping list item has non-mapping children")
                if key in extra:
                    raise _SubsetYamlError("duplicate mapping key")
                item.update(extra)
            result.append(item)
        return result, index

    result_map: dict[str, object] = {}
    while index < len(lines) and lines[index].indent == indent:
        pair = _mapping_key(lines[index].content)
        if pair is None:
            raise _SubsetYamlError("expected mapping entry")
        key, raw_value = pair
        if key in result_map:
            raise _SubsetYamlError(f"duplicate key: {key}")
        index += 1
        if raw_value:
            result_map[key] = _scalar(raw_value)
            if index < len(lines) and lines[index].indent > indent:
                raise _SubsetYamlError("scalar mapping entry cannot have children")
        elif index < len(lines) and lines[index].indent > indent:
            child_indent = lines[index].indent
            if child_indent != indent + 2:
                raise _SubsetYamlError("nested indentation must increase by two")
            result_map[key], index = _parse_block(lines, index, child_indent)
        else:
            result_map[key] = None
    if index < len(lines) and lines[index].indent < indent:
        return result_map, index
    return result_map, index


def _parse_document(text: str) -> dict[str, object]:
    lines = _tokenize(text)
    if not lines:
        return {}
    if lines[0].indent != 0:
        raise _SubsetYamlError("document must start at column zero")
    document, index = _parse_block(lines, 0, 0)
    if not isinstance(document, dict) or index != len(lines):
        raise _SubsetYamlError("document must be a mapping")
    return document


# ponytail: this is not YAML; upgrade to owner-approved PyYAML if the shapes grow.
def _projects_document(text: str) -> object:
    """Parse only the top-level projects block; unrelated config may be ignored."""
    raw_lines = text.splitlines()
    start: int | None = None
    inline: str | None = None
    for number, raw in enumerate(raw_lines):
        candidate = _remove_comment(raw).strip()
        if not candidate:
            continue
        if len(raw) - len(raw.lstrip(" ")) != 0:
            continue
        pair = _mapping_key(candidate)
        if pair and pair[0] == "projects":
            start = number
            inline = pair[1]
            break
    if start is None:
        return []
    if inline:
        return _scalar(inline)
    selected = ["projects:"]
    for raw in raw_lines[start + 1 :]:
        candidate = _remove_comment(raw).rstrip()
        if candidate.strip() and not candidate.startswith(" "):
            break
        selected.append(candidate)
    document = _parse_document("\n".join(selected))
    return document.get("projects")


def _non_empty_text(value: object, field: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise InvalidProjectConfigError(f"{field} must be a non-empty scalar")
    return value


def _path_like_id(project_id: str) -> bool:
    return (
        not project_id
        or "/" in project_id
        or "\\" in project_id
        or project_id in {".", ".."}
        or any(part in {".", ".."} for part in re.split(r"[/\\]", project_id))
    )


def _normalized_location(location: str) -> str:
    normalized = location.replace("\\", "/").rstrip("/")
    return normalized or "/"


def _validate_manifest_name(value: object) -> str:
    if not isinstance(value, str) or not value:
        raise InvalidProjectConfigError("manifest must be a non-empty relative path")
    normalized = value.replace("\\", "/")
    if normalized.startswith("/") or _DRIVE_PATH.match(normalized):
        raise InvalidProjectConfigError("manifest must be relative")
    depth = 0
    for part in normalized.split("/"):
        if part in {"", "."}:
            continue
        if part == "..":
            depth -= 1
            if depth < 0:
                raise InvalidProjectConfigError("manifest escapes its project root")
        else:
            depth += 1
    return value


def _alias_tuple(value: object) -> tuple[str, ...]:
    """Parse one optional native-id alias declaration into validated ids."""
    if value is None:
        return ()
    if isinstance(value, str):
        items: list[object] = [value]
    elif isinstance(value, list):
        items = value
    else:
        raise InvalidProjectConfigError("kanban_project_ids must be a scalar or a sequence")
    aliases: list[str] = []
    for item in items:
        if not isinstance(item, str) or not item.strip():
            raise InvalidProjectConfigError("kanban_project_ids entries must be non-empty strings")
        alias = item.strip()
        if _path_like_id(alias):
            raise InvalidProjectConfigError(f"invalid kanban project id: {alias}")
        if alias in aliases:
            raise InvalidProjectConfigError(f"duplicate kanban project id: {alias}")
        aliases.append(alias)
    return tuple(aliases)


def _validate_records(projects: list[ProjectRecord]) -> list[ProjectRecord]:
    seen_ids: set[str] = set()
    seen_repositories: set[str] = set()
    seen_locations: set[str] = set()
    validated: list[ProjectRecord] = []
    for project in projects:
        if not isinstance(project, ProjectRecord):
            raise InvalidProjectConfigError("projects must contain ProjectRecord values")
        if _path_like_id(project.id):
            raise InvalidProjectConfigError(f"invalid project id: {project.id}")
        if not isinstance(project.name, str) or not project.name.strip():
            raise InvalidProjectConfigError("name must be a non-empty string")
        if not isinstance(project.repository, str) or not project.repository.strip():
            raise InvalidProjectConfigError("repository must be a non-empty string")
        if not isinstance(project.location, Path) or not str(project.location):
            raise InvalidProjectConfigError("location must be a non-empty path")
        if not isinstance(project.default_branch, str) or not project.default_branch:
            raise InvalidProjectConfigError("default_branch must be a string")
        if not isinstance(project.enabled, bool):
            raise InvalidProjectConfigError("enabled must be boolean")
        if not isinstance(project.settings, dict) or any(
            not isinstance(key, str) or not isinstance(value, str)
            for key, value in project.settings.items()
        ):
            raise InvalidProjectConfigError("settings values must be scalar strings")
        if project.manifest is not None:
            _validate_manifest_name(project.manifest)
        location_key = _normalized_location(str(project.location))
        if (
            project.id in seen_ids
            or project.repository in seen_repositories
            or location_key in seen_locations
        ):
            raise InvalidProjectConfigError("project id, repository, and location must be unique")
        seen_ids.add(project.id)
        seen_repositories.add(project.repository)
        seen_locations.add(location_key)
        validated.append(project)
    operational_ids = {project.id for project in validated}
    seen_aliases: set[str] = set()
    for project in validated:
        for alias in project.kanban_project_ids:
            if alias in operational_ids or alias in seen_aliases:
                raise InvalidProjectConfigError(
                    "kanban project ids must be unique and must not shadow a project id"
                )
            seen_aliases.add(alias)
    return validated


def load_project_entries(config_path: Path) -> list[ProjectRecord]:
    """Load and validate the explicit managed project set."""
    try:
        text = config_path.read_text(encoding="utf-8")
        raw_projects = _projects_document(text)
    except (OSError, UnicodeError, _SubsetYamlError) as exc:
        raise InvalidProjectConfigError(f"cannot read project config: {config_path}") from exc
    if raw_projects is None:
        raw_projects = []
    if not isinstance(raw_projects, list):
        raise InvalidProjectConfigError("projects must be a sequence")

    projects: list[ProjectRecord] = []
    for raw_project in raw_projects:
        if not isinstance(raw_project, dict):
            raise InvalidProjectConfigError("each project must be a mapping")
        required = {
            field: _non_empty_text(raw_project.get(field), field)
            for field in ("id", "name", "repository", "location")
        }
        project_id = required["id"]
        if _path_like_id(project_id):
            raise InvalidProjectConfigError(f"invalid project id: {project_id}")
        raw_branch = raw_project.get("default_branch")
        if raw_branch is None or raw_branch == "":
            default_branch = "main"
        else:
            default_branch = _non_empty_text(raw_branch, "default_branch")
        enabled = raw_project.get("enabled", True)
        if not isinstance(enabled, bool):
            raise InvalidProjectConfigError("enabled must be boolean")
        raw_settings = raw_project.get("settings", {})
        if raw_settings is None:
            raw_settings = {}
        if not isinstance(raw_settings, dict):
            raise InvalidProjectConfigError("settings must be a mapping")
        settings: dict[str, str] = {}
        for key, value in raw_settings.items():
            if not isinstance(key, str) or not isinstance(value, (str, bool, int, float)):
                raise InvalidProjectConfigError("settings values must be scalar")
            settings[key] = str(value).lower() if isinstance(value, bool) else str(value)
        manifest = None
        if "manifest" in raw_project:
            manifest = _validate_manifest_name(raw_project["manifest"])
        projects.append(
            ProjectRecord(
                id=project_id,
                name=required["name"],
                repository=required["repository"],
                location=Path(required["location"]),
                default_branch=default_branch,
                enabled=enabled,
                settings=settings,
                manifest=manifest,
                kanban_project_ids=_alias_tuple(raw_project.get("kanban_project_ids")),
            )
        )
    return _validate_records(projects)


def _readable_directory(path: Path) -> bool:
    if not path.is_dir() or not os.access(path, os.R_OK | os.X_OK):
        return False
    try:
        with os.scandir(path):
            return True
    except OSError:
        return False


def _safe_path(root: Path, relative: str) -> Path:
    normalized = relative.replace("\\", "/")
    if not normalized or normalized.startswith("/") or _DRIVE_PATH.match(normalized):
        raise UnsafePathError(f"path is not project-relative: {relative}")
    candidate = (root / Path(normalized)).resolve()
    try:
        candidate.relative_to(root)
    except ValueError as exc:
        raise UnsafePathError(f"path escapes project root: {relative}") from exc
    return candidate


def _read_utf8(path: Path) -> str:
    return path.read_bytes().decode("utf-8")


def _manifest_from_file(path: Path) -> ProjectManifest:
    try:
        raw = _parse_document(_read_utf8(path))
    except _SubsetYamlError as exc:
        raise MalformedManifestError(f"cannot parse manifest: {path}") from exc
    except (OSError, UnicodeError) as exc:
        raise MissingProjectConfigurationError(f"cannot read manifest: {path}") from exc

    def required(field: str) -> str:
        value = raw.get(field)
        if not isinstance(value, str) or not value.strip():
            raise MissingProjectConfigurationError(f"manifest requires {field}")
        return value

    validation = raw.get("validation")
    if not isinstance(validation, dict):
        raise MissingProjectConfigurationError("manifest requires validation.commands")
    commands = validation.get("commands")
    if (
        not isinstance(commands, list)
        or not commands
        or any(not isinstance(command, str) or not command for command in commands)
    ):
        raise MissingProjectConfigurationError("manifest requires validation.commands")

    workflow = raw.get("workflow")
    if workflow is not None and not isinstance(workflow, dict):
        raise MalformedManifestError("workflow must be a mapping")
    workflow_default = workflow.get("default") if workflow else None
    if workflow_default is not None and not isinstance(workflow_default, str):
        raise MalformedManifestError("workflow.default must be a scalar")

    development = raw.get("development")
    if development is not None and not isinstance(development, dict):
        raise MalformedManifestError("development must be a mapping")
    development_commands: tuple[str, ...] | None = None
    if development is not None and "commands" in development:
        values = development["commands"]
        if not isinstance(values, list) or any(not isinstance(value, str) for value in values):
            raise MalformedManifestError("development.commands must be a list")
        development_commands = tuple(values)

    ai = raw.get("ai")
    if ai is not None and not isinstance(ai, dict):
        raise MalformedManifestError("ai must be a mapping")
    ai_context: tuple[str, ...] = ()
    if ai is not None and "context" in ai:
        values = ai["context"]
        if not isinstance(values, list) or any(not isinstance(value, str) for value in values):
            raise MalformedManifestError("ai.context must be a list")
        ai_context = tuple(values)

    description = raw.get("description")
    if description is not None and not isinstance(description, str):
        raise MalformedManifestError("description must be a scalar")
    return ProjectManifest(
        name=required("name"),
        description=description,
        repository=required("repository"),
        default_branch=required("default_branch"),
        workflow=workflow_default,
        validation_commands=tuple(commands),
        development_commands=development_commands,
        ai_context=ai_context,
    )


def _optional_slot(root: Path, candidates: tuple[str, ...]) -> str | None:
    for relative in candidates:
        path = root / relative
        try:
            if not path.is_file():
                continue
            return _read_utf8(path)
        except (OSError, UnicodeError):
            continue
    return None


class ProjectRegistry:
    """Read-only in-process registry of explicitly enrolled projects."""

    def __init__(self, projects: list[ProjectRecord]) -> None:
        self._projects = tuple(_validate_records(list(projects)))
        self._by_id = {project.id: project for project in self._projects}
        self._by_kanban_id = {
            alias: project
            for project in self._projects
            for alias in project.kanban_project_ids
        }

    @classmethod
    def from_config(cls, config_path: Path) -> ProjectRegistry:
        """Construct a registry from caller-supplied operational YAML."""
        return cls(load_project_entries(config_path))

    def list_projects(self) -> list[ProjectRecord]:
        """Return configured records in config order without reading project trees."""
        return list(self._projects)

    def canonical_id(self, project_id: str) -> str:
        """Map an operational id or declared native id to the operational id."""
        if not isinstance(project_id, str) or _path_like_id(project_id):
            raise UnknownProjectError(f"unknown project: {project_id}")
        if project_id in self._by_id:
            return project_id
        try:
            return self._by_kanban_id[project_id].id
        except KeyError as exc:
            raise UnknownProjectError(f"unknown project: {project_id}") from exc

    def get_project(self, project_id: str) -> ProjectRecord:
        """Return one exact operational identity for an enrolled id or alias."""
        try:
            return self._by_id[self.canonical_id(project_id)]
        except KeyError as exc:
            raise UnknownProjectError(f"unknown project: {project_id}") from exc

    def resolve_eligible_project(self, project_id: str) -> ProjectRecord:
        """Apply enabled and readable-directory gates to an enrolled project."""
        project = self.get_project(project_id)
        if not project.enabled:
            raise DisabledProjectError(f"project is disabled: {project.id}")
        if not _readable_directory(project.location):
            raise InvalidProjectLocationError(f"invalid project location: {project.location}")
        return project

    def load_project_context(self, project_id: str) -> ProjectContext:
        """Load project-side declarations and closed-set context files in place."""
        project = self.resolve_eligible_project(project_id)
        root = project.location.resolve()
        manifest_name = project.manifest or ".ainative/project.yaml"
        manifest_path = _safe_path(root, manifest_name)
        try:
            if not manifest_path.is_file():
                raise OSError(f"not a file: {manifest_path}")
        except OSError as exc:
            raise MissingProjectConfigurationError(
                f"missing project manifest: {manifest_name}"
            ) from exc
        manifest = _manifest_from_file(manifest_path)

        ai_context_files: list[ContextFile] = []
        for relative in manifest.ai_context:
            path = _safe_path(root, relative)
            try:
                text = _read_utf8(path)
            except (OSError, UnicodeError) as exc:
                raise MissingProjectConfigurationError(
                    f"cannot read AI context file: {relative}"
                ) from exc
            ai_context_files.append(ContextFile(relative, text))

        tooling_names = (
            "pyproject.toml",
            "package.json",
            "go.mod",
            "Cargo.toml",
            "Makefile",
            "pytest.ini",
            "tsconfig.json",
        )
        tooling_paths = tuple(name for name in tooling_names if (root / name).is_file())
        return ProjectContext(
            id=project.id,
            name=manifest.name,
            repository=project.repository,
            declared_repository=manifest.repository,
            default_branch=manifest.default_branch or project.default_branch or "main",
            location=project.location,
            workflow=manifest.workflow,
            validation_commands=manifest.validation_commands,
            development_commands=manifest.development_commands,
            settings=project.settings,
            overview=_optional_slot(root, ("README.md", "README")),
            agent_instructions=_optional_slot(root, ("AGENTS.md", "CLAUDE.md")),
            contributing=_optional_slot(root, ("CONTRIBUTING.md",)),
            architecture=_optional_slot(root, ("docs/architecture.md", "ARCHITECTURE.md")),
            ai_context_files=tuple(ai_context_files),
            tooling_paths=tooling_paths,
        )
