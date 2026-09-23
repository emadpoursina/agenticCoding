"""Operator onboarding for one managed project plus PRD card drafts."""

from __future__ import annotations

import errno
import os
import re
import sqlite3
import subprocess
import tempfile
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

from .projects import (
    ProjectRegistryError,
    _manifest_from_file,
    _parse_document,
    _path_like_id,
    _records_from_text,
    _SubsetYamlError,
    _validate_records,
    load_project_entries,
)
from .workspace import InvalidWorkspaceRootError, load_workspace_root

CloneFn = Callable[[str, Path, str], None]
CardCreateFn = Callable[[list[str]], None]


class OnboardError(Exception):
    """Base error for fail-closed onboarding failures."""


class UnknownNativeProjectError(OnboardError):
    """Raised when the native Hermes project for a repository is absent."""


class PrdDraftError(OnboardError):
    """Raised when a PRD cannot be turned into valid card drafts."""


_PRIORITIES = ("P0", "P1", "P2", "P3")
_PRIORITY_FLAGS = {"P0": "0", "P1": "1", "P2": "2", "P3": "3"}
_OWNER_NAME = re.compile(r"^[^/\s]+/[^/\s]+$")
_H2_HEADING = re.compile(r"^##\s+(.+?)\s*$")
_PRIORITY_LINE = re.compile(r"^priority\s*:\s*(\S+)\s*$", re.IGNORECASE)
_EXPECTED_LINE = re.compile(r"^expected(?:\s+result)?\s*:\s*(.+?)\s*$", re.IGNORECASE)
_SLUG_NOISE = re.compile(r"[^a-z0-9]+")
_READ_ONLY_CONFIG_ERRNOS = {errno.EROFS, errno.EACCES, errno.EPERM}


@dataclass(frozen=True)
class OnboardRequest:
    """Operator-supplied onboarding inputs for one repository."""

    repository: str
    branch: str = "main"
    project_id: str | None = None
    prd: Path | None = None
    drafts_out: Path | None = None
    default_priority: str = "P2"
    dry_run: bool = False
    create_cards: bool = False
    allow_todo: bool = False
    push_scaffold: bool = False


@dataclass(frozen=True)
class ImportPrdRequest:
    """Operator-supplied PRD import inputs for one enrolled repository."""

    repository: str
    prd: Path
    drafts_out: Path | None = None
    default_priority: str = "P2"
    dry_run: bool = False
    create_cards: bool = False
    allow_todo: bool = False


@dataclass(frozen=True)
class OnboardResult:
    """Outcome of one onboarding run for reporting."""

    project_id: str
    repository: str
    native_id: str
    location: Path
    default_branch: str
    cloned: bool
    scaffolded: tuple[str, ...]
    already_enrolled: bool
    drafts: tuple[Path, ...] = ()
    incomplete_drafts: int = 0
    created_cards: tuple[str, ...] = ()
    triaged_cards: int = 0
    pushed: bool = False


def resolve_projects_db() -> Path:
    """Resolve the native Hermes projects database from environment overrides."""
    override = os.environ.get("HERMES_PROJECTS_DB", "").strip()
    if override:
        return Path(override)
    hermes_home = os.environ.get("HERMES_HOME", "").strip()
    if not hermes_home:
        raise OnboardError(
            "onboarding requires HERMES_HOME or HERMES_PROJECTS_DB in the environment"
        )
    return Path(hermes_home) / "projects.db"


def _slug_key(value: str) -> str:
    """Normalize one slug or repository name for comparison."""
    return value.strip().lower().replace("\\", "/").replace(" ", "-")


def _slug_candidates(repository: str) -> tuple[str, ...]:
    owner, _, name = repository.partition("/")
    return tuple(
        dict.fromkeys(
            key
            for key in (
                _slug_key(repository),
                _slug_key(repository.replace("/", "-")),
                _slug_key(name),
            )
            if key
        )
    )


def native_project_id(projects_db: Path, repository: str) -> str:
    """Return the single native projects.db id whose slug matches the repository."""
    if not projects_db.is_file():
        raise OnboardError(f"native projects database is missing: {projects_db}")
    candidates = _slug_candidates(repository)
    try:
        connection = sqlite3.connect(f"{projects_db.resolve().as_uri()}?mode=ro", uri=True)
    except sqlite3.Error as exc:
        raise OnboardError(f"cannot open projects database: {projects_db}") from exc
    try:
        rows = connection.execute("select id, slug from projects").fetchall()
    except sqlite3.Error as exc:
        raise OnboardError(f"cannot read projects database: {projects_db}") from exc
    finally:
        connection.close()
    matches: dict[str, str] = {}
    for native_id, slug in rows:
        if not isinstance(native_id, str) or not isinstance(slug, str):
            continue
        if not native_id.strip() or _path_like_id(native_id.strip()):
            continue
        if _slug_key(slug) in candidates:
            matches[native_id.strip()] = _slug_key(slug)
    if not matches:
        raise UnknownNativeProjectError(
            f"no native Hermes project matches {repository}; create it in Hermes first"
        )
    if len(matches) > 1:
        raise OnboardError(
            f"native projects database matches {repository} ambiguously: "
            + ", ".join(sorted(matches))
        )
    return next(iter(matches))


def _run_hermes(args: list[str]) -> None:
    """Run one upstream Hermes CLI command and fail closed on a nonzero exit."""
    try:
        result = subprocess.run(
            ["hermes", *args], capture_output=True, text=True, check=False
        )
    except OSError as exc:
        raise OnboardError(f"cannot run the hermes CLI: {exc}") from exc
    if result.returncode != 0:
        raise OnboardError(
            f"hermes {' '.join(args[:2])} failed: {result.stderr.strip() or result.stdout.strip()}"
        )


def live_create_native_project(repository: str) -> None:
    """Create the native Hermes project for one repository via the Hermes CLI."""
    slug = _slug_key(repository.replace("/", "-"))
    _run_hermes(["project", "create", slug, "--slug", slug])


def live_create_card(args: list[str]) -> None:
    """Create one native Kanban card via the Hermes CLI."""
    _run_hermes(["kanban", "create", *args])


def priority_flag(priority: str) -> str:
    """Map one P0–P3 priority string to the integer string the CLI flag needs."""
    try:
        return _PRIORITY_FLAGS[priority.strip().upper()]
    except KeyError:
        raise OnboardError(f"invalid priority: {priority or '(empty)'}") from None


def _draft_card_args(text: str) -> tuple[str, str]:
    """Extract the card title and priority from one validated draft."""
    title = ""
    priority = ""
    current = ""
    for line in text.splitlines():
        heading = _H2_HEADING.match(line)
        if heading:
            current = heading.group(1).strip()
            continue
        if not title and line.startswith("# "):
            title = line[2:].strip()
        elif current == "Priority" and not priority and line.strip():
            priority = line.strip().upper()
    return title, priority


def create_cards_from_drafts(
    drafts: tuple[Path, ...],
    native_id: str,
    *,
    allow_todo: bool = False,
    creator: CardCreateFn = live_create_card,
) -> tuple[tuple[str, ...], int]:
    """Create native cards from validated drafts; incomplete drafts triage or fail."""
    created: list[str] = []
    triaged = 0
    for path in drafts:
        try:
            text = path.read_text(encoding="utf-8")
        except (OSError, UnicodeError) as exc:
            raise PrdDraftError(f"cannot read card draft: {path}") from exc
        validate_card_draft(text)
        title, priority = _draft_card_args(text)
        todo = "TODO:" in text
        if todo and not allow_todo:
            raise PrdDraftError(
                f"card draft '{title}' still has TODO sections; complete it or pass --allow-todo"
            )
        args = [
            title,
            "--project", native_id,
            "--priority", priority_flag(priority),
            "--body", text,
            "--idempotency-key", _slugify(title),
        ]
        if todo:
            args.append("--triage")
            triaged += 1
        creator(args)
        created.append(title)
    return tuple(created), triaged


def _entry_lines(
    project_id: str,
    repository: str,
    location: Path,
    branch: str,
    native_id: str,
) -> list[str]:
    """Render the YAML lines for one new project entry."""
    lines = [
        f"  - id: {project_id}",
        f"    name: {repository}",
        f"    repository: {repository}",
        f"    location: {location}",
        f"    default_branch: {branch}",
    ]
    if native_id:
        lines.append("    kanban_project_ids:")
        lines.append(f"      - {native_id}")
    return lines


def _discard_temp(path: Path) -> None:
    """Remove a temporary file, tolerating a second failure."""
    try:
        path.unlink(missing_ok=True)
    except OSError:
        pass


def append_project_entry(config_path: Path, entry_lines: list[str]) -> None:
    """Append one project entry to the projects list and revalidate the file."""
    try:
        original = config_path.read_text(encoding="utf-8")
    except (OSError, UnicodeError) as exc:
        raise OnboardError(f"cannot read config: {config_path}") from exc
    lines = original.splitlines()
    start = None
    for index, raw in enumerate(lines):
        if re.fullmatch(r"projects\s*:", raw.strip()):
            start = index
            break
    if start is None:
        updated = lines + ["projects:"] + entry_lines
    else:
        end = start + 1
        while end < len(lines) and lines[end].strip() and lines[end][:1] in {" ", "\t"}:
            end += 1
        while end > start + 1 and not lines[end - 1].strip():
            end -= 1
        updated = lines[:end] + entry_lines + lines[end:]
    trailing = "\n" if original.endswith("\n") or not original else ""
    candidate = "\n".join(updated) + trailing
    temp_path = config_path.with_name(config_path.name + ".onboard-tmp")
    try:
        temp_path.write_text(candidate, encoding="utf-8")
    except OSError as exc:
        if exc.errno not in _READ_ONLY_CONFIG_ERRNOS:
            _discard_temp(temp_path)
            raise OnboardError(f"cannot write config: {config_path}") from exc
        _append_overlay_entry(config_path, original, entry_lines)
        return
    try:
        load_project_entries(temp_path)
    except (OSError, ProjectRegistryError) as exc:
        _discard_temp(temp_path)
        raise OnboardError(f"onboarding would produce an invalid config: {exc}") from exc
    try:
        temp_path.replace(config_path)
    except OSError as exc:
        _discard_temp(temp_path)
        raise OnboardError(f"cannot write config: {config_path}") from exc


def _overlay_enrolment_path(config_path: Path, config_text: str) -> Path:
    """Resolve enrolled-projects.yaml under execution.overlay_dir from the config."""
    try:
        document = _parse_document(config_text)
    except _SubsetYamlError as exc:
        raise OnboardError(f"cannot read config: {config_path}") from exc
    execution = document.get("execution")
    raw_directory = execution.get("overlay_dir") if isinstance(execution, dict) else None
    if not isinstance(raw_directory, str) or not raw_directory.strip():
        raise OnboardError(
            f"cannot write config {config_path}: no execution.overlay_dir fallback"
        )
    return Path(raw_directory.strip()) / "enrolled-projects.yaml"


def _append_overlay_entry(
    config_path: Path, config_text: str, entry_lines: list[str]
) -> None:
    """Append only the new entry to the overlay file when the config is read-only."""
    overlay_path = _overlay_enrolment_path(config_path, config_text)
    if not overlay_path.parent.is_dir():
        overlay_path.parent.mkdir(parents=True, exist_ok=True)
    existing = ""
    if overlay_path.is_file():
        try:
            existing = overlay_path.read_text(encoding="utf-8")
        except (OSError, UnicodeError) as exc:
            raise OnboardError(f"cannot read project overlay: {overlay_path}") from exc
    base_records = _records_from_text(config_text, config_path)
    if not existing.strip():
        candidate = "projects:\n" + "\n".join(entry_lines) + "\n"
    else:
        candidate_lines = existing.splitlines()
        start = None
        for index, raw in enumerate(candidate_lines):
            if re.fullmatch(r"projects\s*:", raw.strip()):
                start = index
                break
        if start is None:
            candidate_lines = candidate_lines + ["projects:"] + entry_lines
        else:
            end = start + 1
            while (
                end < len(candidate_lines)
                and candidate_lines[end].strip()
                and candidate_lines[end][:1] in {" ", "\t"}
            ):
                end += 1
            while end > start + 1 and not candidate_lines[end - 1].strip():
                end -= 1
            candidate_lines = candidate_lines[:end] + entry_lines + candidate_lines[end:]
        trailing = "\n" if existing.endswith("\n") or not existing else ""
        candidate = "\n".join(candidate_lines) + trailing
    merged = _records_from_text(candidate, overlay_path)
    _validate_records(base_records + merged)
    temp_path = overlay_path.with_name(overlay_path.name + ".onboard-tmp")
    try:
        temp_path.write_text(candidate, encoding="utf-8")
        temp_path.replace(overlay_path)
    except OSError as exc:
        try:
            temp_path.unlink(missing_ok=True)
        except OSError:
            pass
        raise OnboardError(f"cannot write project overlay: {overlay_path}") from exc


def live_clone(url: str, location: Path, branch: str) -> None:
    """Clone one repository over the configured SSH transport."""
    result = subprocess.run(
        ["git", "clone", "--branch", branch, url, str(location)],
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        raise OnboardError(f"git clone failed: {result.stderr.strip()}")


def _remote_matches_owner(location: Path, repository: str) -> bool:
    try:
        result = subprocess.run(
            ["git", "-C", str(location), "remote", "get-url", "origin"],
            capture_output=True,
            text=True,
            check=True,
        )
    except (OSError, subprocess.CalledProcessError):
        return False
    return repository in result.stdout


_AGENTS_SECTION_SUFFIX = "## Hermes control plane"


def _control_plane_section(project_id: str, repository: str, branch: str) -> str:
    return "\n".join(
        (
            "## Hermes control plane",
            "",
            "This repository is enrolled with the Hermes personal-agent"
            f" control plane (project id `{project_id}`, repository"
            f" `{repository}`, default branch `{branch}`).",
            "",
            "- Pi owns implementation; the control plane publishes feature branches only.",
            "- Publish runs only after critic PASS and tester PASS, on the feature branch.",
            "- Keep validation commands in `.ainative/project.yaml` current.",
            "- Never commit secrets or push protected branches.",
        )
    )


def _compose_agents_text(
    existing: str, project_id: str, repository: str, branch: str
) -> str:
    """Append the control-plane section to an existing project AGENTS.md."""
    if _AGENTS_SECTION_SUFFIX in existing:
        return existing
    if existing.endswith("\n\n"):
        separator = ""
    elif existing.endswith("\n"):
        separator = "\n"
    else:
        separator = "\n\n"
    return existing + separator + _control_plane_section(project_id, repository, branch) + "\n"


def _readme_text(project_id: str, repository: str, branch: str) -> str:
    return (
        f"# {project_id}\n"
        "\n"
        "Managed by the Hermes personal-agent control plane.\n"
        "\n"
        f"- Repository: {repository}\n"
        f"- Default branch: {branch}\n"
        "\n"
        "Enrolled via `python -m hermes_kanban --onboard`. Hermes reads this\n"
        "file for project context only; edit freely.\n"
    )


def _agents_text(project_id: str, repository: str, branch: str) -> str:
    return (
        f"# Project rules — {project_id}\n"
        "\n"
        f"- Repository {repository}, default branch `{branch}`.\n"
        "- Pi owns implementation; the control plane publishes feature branches only.\n"
        "- Keep validation commands in `.ainative/project.yaml` current.\n"
        "- Never commit secrets or push protected branches.\n"
        "\n"
        f"{_control_plane_section(project_id, repository, branch)}\n"
    )

def _manifest_text(project_id: str, repository: str, branch: str) -> str:
    return (
        f"name: {project_id}\n"
        "description: Onboarded via the hermes_kanban onboarding command\n"
        f"repository: {repository}\n"
        f"default_branch: {branch}\n"
        "\n"
        "workflow:\n"
        "  default: feature-loop\n"
        "\n"
        "validation:\n"
        "  commands:\n"
        '    - echo "TODO: declare real validation commands in .ainative/project.yaml"\n'
    )


SUGGESTED_VALIDATION_COMMANDS = (
    "uv run pytest",
    "uv run ruff check src tests",
)


def scaffold_project_files(
    location: Path, project_id: str, repository: str, branch: str
) -> tuple[str, ...]:
    """Create missing onboarding files; compose an existing AGENTS.md."""
    files = {
        "README.md": _readme_text(project_id, repository, branch),
        ".ainative/project.yaml": _manifest_text(project_id, repository, branch),
    }
    created: list[str] = []
    for relative, text in files.items():
        path = location / relative
        if path.exists():
            continue
        path.parent.mkdir(parents=True, exist_ok=True)
        try:
            path.write_text(text, encoding="utf-8")
        except OSError as exc:
            raise OnboardError(f"cannot scaffold {relative}: {exc}") from exc
        created.append(relative)
    agents_path = location / "AGENTS.md"
    if agents_path.is_file():
        try:
            existing = agents_path.read_text(encoding="utf-8")
        except (OSError, UnicodeError) as exc:
            raise OnboardError(f"cannot read existing AGENTS.md: {exc}") from exc
        composed = _compose_agents_text(existing, project_id, repository, branch)
        if composed != existing:
            try:
                agents_path.write_text(composed, encoding="utf-8")
            except OSError as exc:
                raise OnboardError(f"cannot update AGENTS.md: {exc}") from exc
            created.append("AGENTS.md")
    else:
        try:
            agents_path.write_text(
                _agents_text(project_id, repository, branch), encoding="utf-8"
            )
        except OSError as exc:
            raise OnboardError(f"cannot scaffold AGENTS.md: {exc}") from exc
        created.append("AGENTS.md")
    return tuple(created)


def commit_scaffold(location: Path, scaffolded: tuple[str, ...]) -> bool:
    """Commit scaffold-created files in the enrolled copy. Operator-initiated."""
    if not scaffolded:
        return False

    def _git(*args: str) -> str:
        result = subprocess.run(
            ["git", "-C", str(location), *args], capture_output=True, text=True
        )
        if result.returncode != 0:
            raise OnboardError(
                f"cannot commit scaffold (git {' '.join(args)}): "
                f"{result.stderr.strip() or result.stdout.strip()}"
            )
        return result.stdout
    _git("add", "--", *scaffolded)
    staged = _git("diff", "--cached", "--name-only")
    if not staged.strip():
        # Nothing staged: files were already committed or identical. Not an error.
        return False
    _git("commit", "-m", _SCAFFOLD_COMMIT_MESSAGE)
    return True


_SCAFFOLD_COMMIT_MESSAGE = "chore: ainative onboarding scaffold"


def push_scaffold(location: Path, branch: str) -> None:
    """Push the scaffold commit to the remote default branch. Operator-initiated."""
    result = subprocess.run(
        ["git", "-C", str(location), "push", "origin", branch],
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        raise OnboardError(f"git push failed: {result.stderr.strip()}")


def _verify_manifest(location: Path) -> None:
    manifest_path = location / ".ainative" / "project.yaml"
    if not manifest_path.is_file():
        raise OnboardError(f"missing project manifest: {manifest_path}")
    try:
        _manifest_from_file(manifest_path)
    except ProjectRegistryError as exc:
        raise OnboardError(f"project manifest is invalid: {exc}") from exc


def _derive_project_id(repository: str) -> str:
    slug = _SLUG_NOISE.sub("-", repository.partition("/")[2].lower()).strip("-")
    if not slug or _path_like_id(slug):
        raise OnboardError(f"cannot derive a safe project id from {repository}")
    return slug


def run_onboard(
    request: OnboardRequest,
    config_path: Path,
    *,
    cloner: CloneFn = live_clone,
    projects_db: Path | None = None,
    native_project_creator: Callable[[str], None] = live_create_native_project,
    card_creator: CardCreateFn = live_create_card,
) -> OnboardResult:
    """Run the full fail-closed onboarding sequence for one repository."""
    repository = request.repository.strip()
    if not _OWNER_NAME.fullmatch(repository):
        raise OnboardError(f"repository must be owner/name: {repository}")
    project_id = request.project_id or _derive_project_id(repository)
    if _path_like_id(project_id):
        raise OnboardError(f"invalid project id: {project_id}")
    branch = request.branch.strip() or "main"
    try:
        enrolled = load_project_entries(config_path)
        workspace_root = load_workspace_root(config_path)
    except (OSError, ProjectRegistryError, InvalidWorkspaceRootError) as exc:
        raise OnboardError(f"cannot read config: {config_path}") from exc
    existing = next((record for record in enrolled if record.id == project_id), None)
    location = workspace_root / project_id
    if existing is not None:
        if existing.repository != repository:
            raise OnboardError(
                f"project {project_id} is already enrolled as {existing.repository}"
            )
        if not existing.kanban_project_ids:
            raise OnboardError(
                f"project {project_id} is enrolled without a native id; declare "
                "kanban_project_ids manually"
            )
        return OnboardResult(
            project_id=project_id,
            repository=repository,
            native_id=existing.kanban_project_ids[0],
            location=location,
            default_branch=existing.default_branch,
            cloned=False,
            scaffolded=(),
            already_enrolled=True,
        )
    try:
        native_id = native_project_id(projects_db or resolve_projects_db(), repository)
    except UnknownNativeProjectError:
        if request.dry_run:
            raise
        native_project_creator(repository)
        native_id = native_project_id(projects_db or resolve_projects_db(), repository)
    clone_url = f"git@github.com:{repository}.git"
    cloned = False
    scaffolded: tuple[str, ...] = ()
    drafts: tuple[Path, ...] = ()
    incomplete = 0
    if request.dry_run:
        return OnboardResult(
            project_id=project_id,
            repository=repository,
            native_id=native_id,
            location=location,
            default_branch=branch,
            cloned=False,
            scaffolded=(),
            already_enrolled=False,
            drafts=(),
            incomplete_drafts=0,
        )
    if location.exists():
        if not location.is_dir():
            raise OnboardError(f"workspace location is a file: {location}")
        if any(location.iterdir()) and not _remote_matches_owner(location, repository):
            raise OnboardError(
                f"workspace location is non-empty without a matching remote: {location}"
            )
    else:
        location.parent.mkdir(parents=True, exist_ok=True)
        cloner(clone_url, location, branch)
        cloned = True
    scaffolded = scaffold_project_files(location, project_id, repository, branch)
    _verify_manifest(location)
    commit_scaffold(location, scaffolded)
    pushed = False
    if request.push_scaffold and scaffolded:
        push_scaffold(location, branch)
        pushed = True
    entry = _entry_lines(project_id, repository, location, branch, native_id)
    append_project_entry(config_path, entry)
    if request.prd is not None:
        drafts, incomplete = import_prd(
            request.prd,
            request.drafts_out or Path("scratch") / "card-drafts" / project_id,
            default_priority=request.default_priority,
        )
    created_cards: tuple[str, ...] = ()
    triaged = 0
    if request.create_cards and drafts:
        created_cards, triaged = create_cards_from_drafts(
            drafts, native_id, allow_todo=request.allow_todo, creator=card_creator
        )
    return OnboardResult(
        project_id=project_id,
        repository=repository,
        native_id=native_id,
        location=location,
        default_branch=branch,
        cloned=cloned,
        scaffolded=scaffolded,
        already_enrolled=False,
        drafts=drafts,
        incomplete_drafts=incomplete,
        created_cards=created_cards,
        triaged_cards=triaged,
        pushed=pushed,
    )


def _resolve_enrolled_project(repository: str, config_path: Path) -> tuple[str, str, Path, str]:
    """Resolve one enrolled project by owner/name for PRD import."""
    if not _OWNER_NAME.fullmatch(repository):
        raise OnboardError(f"repository must be owner/name: {repository}")
    try:
        enrolled = load_project_entries(config_path)
    except (OSError, ProjectRegistryError, InvalidWorkspaceRootError) as exc:
        raise OnboardError(f"cannot read config: {config_path}") from exc

    def _matches(record_name: str, record_repository: str) -> bool:
        return (
            record_name == repository
            or record_name.endswith(f"/{repository}")
            or record_repository == repository
        )

    record = next(
        (
            entry
            for entry in enrolled
            if _matches(entry.name, entry.repository)
        ),
        None,
    )
    if record is None:
        raise OnboardError(f"project is not enrolled: {repository}")
    if not record.kanban_project_ids:
        raise OnboardError(
            f"project {record.id} is enrolled without a native id; declare "
            "kanban_project_ids manually"
        )
    return (
        record.id,
        record.kanban_project_ids[0],
        record.location,
        record.default_branch,
    )


def run_import_prd(
    request: ImportPrdRequest,
    config_path: Path,
    *,
    card_creator: CardCreateFn = live_create_card,
) -> OnboardResult:
    """Turn a PRD into card drafts for an already-enrolled project."""
    project_id, native_id, location, default_branch = _resolve_enrolled_project(
        request.repository.strip(), config_path
    )
    drafts_out = request.drafts_out or Path("scratch") / "card-drafts" / project_id
    if request.dry_run:
        # Validate the PRD end-to-end without writing drafts or cards.
        with tempfile.TemporaryDirectory() as temp_dir:
            drafts, incomplete = import_prd(
                request.prd,
                Path(temp_dir),
                default_priority=request.default_priority,
            )
        return OnboardResult(
            project_id=project_id,
            repository=request.repository.strip(),
            native_id=native_id,
            location=location,
            default_branch=default_branch,
            cloned=False,
            scaffolded=(),
            already_enrolled=False,
            drafts=(),
            incomplete_drafts=incomplete,
        )
    drafts, incomplete = import_prd(
        request.prd,
        drafts_out,
        default_priority=request.default_priority,
    )
    created_cards: tuple[str, ...] = ()
    triaged = 0
    if request.create_cards and drafts:
        created_cards, triaged = create_cards_from_drafts(
            drafts, native_id, allow_todo=request.allow_todo, creator=card_creator
        )
    return OnboardResult(
        project_id=project_id,
        repository=request.repository.strip(),
        native_id=native_id,
        location=location,
        default_branch=default_branch,
        cloned=False,
        scaffolded=(),
        already_enrolled=False,
        drafts=drafts,
        incomplete_drafts=incomplete,
        created_cards=created_cards,
        triaged_cards=triaged,
    )


@dataclass(frozen=True)
class CardDraft:
    """One validated Kanban card draft rendered from PRD text."""

    title: str
    priority: str
    problem: str
    expected_result: str
    technical_notes: str


def _prd_sections(text: str) -> list[tuple[str, str]]:
    """Split PRD markdown into one candidate card per second-level heading."""
    sections: list[tuple[str, str]] = []
    title: str | None = None
    body: list[str] = []
    for line in text.splitlines():
        match = _H2_HEADING.match(line)
        if match:
            if title is not None:
                sections.append((title, "\n".join(body).strip()))
            title = match.group(1)
            body = []
        elif title is not None:
            body.append(line)
    if title is not None:
        sections.append((title, "\n".join(body).strip()))
    return sections


def _build_draft(title: str, body: str, default_priority: str) -> CardDraft:
    """Turn one PRD section into a validated card draft."""
    priority = default_priority
    expected: str | None = None
    problem_lines: list[str] = []
    for line in body.splitlines():
        priority_match = _PRIORITY_LINE.match(line.strip())
        if priority_match:
            declared = priority_match.group(1).upper()
            if declared not in _PRIORITIES:
                raise PrdDraftError(
                    f"card '{title}' declares invalid priority {declared} "
                    f"(allowed: {', '.join(_PRIORITIES)})"
                )
            priority = declared
            continue
        expected_match = _EXPECTED_LINE.match(line.strip())
        if expected_match and expected is None:
            expected = expected_match.group(1)
            continue
        problem_lines.append(line)
    problem = "\n".join(problem_lines).strip()
    if not expected:
        expected = "TODO: expected result — complete before grooming."
    if not problem:
        problem = "TODO: problem statement — complete before grooming."
    notes = ""
    return CardDraft(
        title=title,
        priority=priority,
        problem=problem,
        expected_result=expected,
        technical_notes=notes,
    )


def _slugify(title: str) -> str:
    slug = _SLUG_NOISE.sub("-", title.lower()).strip("-")[:40].strip("-")
    return slug or "card"


def render_card_draft(draft: CardDraft) -> str:
    """Render one card draft with the exact native card headings."""
    parts = [
        f"# {draft.title}",
        "",
        "## Priority",
        draft.priority,
        "",
        "## Problem",
        draft.problem,
        "",
        "## Expected Result",
        draft.expected_result,
    ]
    if draft.technical_notes:
        parts.extend(["", "## Technical Notes", draft.technical_notes])
    return "\n".join(parts) + "\n"


def validate_card_draft(text: str) -> None:
    """Reject card drafts that miss a required heading or a valid priority."""
    headings: dict[str, list[str]] = {}
    current = ""
    for line in text.splitlines():
        match = _H2_HEADING.match(line)
        if match:
            current = match.group(1).strip()
            headings.setdefault(current, [])
        elif current:
            headings[current].append(line)
    for required in ("Priority", "Problem", "Expected Result"):
        if required not in headings:
            raise PrdDraftError(f"card draft is missing the '{required}' heading")
    priority = (headings.get("Priority") or [""])[0].strip().upper()
    if priority not in _PRIORITIES:
        raise PrdDraftError(f"card draft has invalid priority: {priority or '(empty)'}")
    for required in ("Problem", "Expected Result"):
        if not any(value.strip() for value in headings.get(required, [])):
            raise PrdDraftError(f"card draft has an empty '{required}' section")


def import_prd(
    prd_path: Path,
    out_dir: Path,
    *,
    default_priority: str = "P2",
) -> tuple[tuple[Path, ...], int]:
    """Split a PRD into validated card draft files under the output directory."""
    if default_priority not in _PRIORITIES:
        raise PrdDraftError(f"invalid default priority: {default_priority}")
    try:
        text = prd_path.read_text(encoding="utf-8")
    except (OSError, UnicodeError) as exc:
        raise PrdDraftError(f"cannot read PRD: {prd_path}") from exc
    sections = _prd_sections(text)
    if not sections:
        raise PrdDraftError(f"PRD has no '## ' sections to turn into cards: {prd_path}")
    out_dir.mkdir(parents=True, exist_ok=True)
    drafts: list[Path] = []
    incomplete = 0
    for index, (title, body) in enumerate(sections, start=1):
        draft = _build_draft(title, body, default_priority)
        if "TODO: expected result" in draft.expected_result:
            incomplete += 1
        rendered = render_card_draft(draft)
        validate_card_draft(rendered)
        path = out_dir / f"{index:03d}-{_slugify(title)}.md"
        try:
            path.write_text(rendered, encoding="utf-8")
        except OSError as exc:
            raise PrdDraftError(f"cannot write card draft: {path}") from exc
        drafts.append(path)
    return tuple(drafts), incomplete
