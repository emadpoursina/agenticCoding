"""Read-only adapters for the native Hermes Kanban database."""

from __future__ import annotations

import re
import sqlite3
from collections.abc import Callable
from datetime import UTC, datetime
from pathlib import Path

from .orchestrator import (
    BoardTask,
    MissingTaskBoardError,
    OrchestratorError,
    UnknownTaskError,
)

_PRIORITIES = frozenset({"P0", "P1", "P2", "P3"})
_HEADING = re.compile(r"^##[ \t]+(.+?)\s*$")
_REQUIRED_COLUMNS = (
    "id",
    "project_id",
    "body",
    "assignee",
    "status",
    "priority",
    "created_at",
)


class SqliteTaskBoardError(OrchestratorError):
    """Raised when the native Kanban database cannot be read."""


def _sections(body: str) -> dict[str, str]:
    sections: dict[str, list[str]] = {}
    current: str | None = None
    for line in body.splitlines():
        match = _HEADING.match(line.strip())
        if match:
            current = match.group(1).strip()
            sections.setdefault(current, [])
            continue
        if current is not None:
            sections[current].append(line)
    return {name: "\n".join(lines).strip() for name, lines in sections.items()}


def _created_at(value: object) -> str:
    if isinstance(value, (int, float)):
        return datetime.fromtimestamp(value, tz=UTC).isoformat().replace("+00:00", "Z")
    if not isinstance(value, str) or not value.strip():
        return ""
    raw = value.strip()
    if raw.isdigit():
        return datetime.fromtimestamp(int(raw), tz=UTC).isoformat().replace("+00:00", "Z")
    try:
        parsed = datetime.fromisoformat(raw.replace("Z", "+00:00"))
    except ValueError:
        return ""
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=UTC)
    return parsed.astimezone(UTC).isoformat().replace("+00:00", "Z")


def _body_dependencies(value: str) -> tuple[str, ...]:
    dependencies: list[str] = []
    for line in value.splitlines():
        item = line.strip().lstrip("-*").strip()
        if not item or item.casefold() in {"none", "n/a"}:
            continue
        for part in item.split(","):
            dependency = part.strip().split()[0] if part.strip() else ""
            if dependency and dependency not in dependencies:
                dependencies.append(dependency)
    return tuple(dependencies)


class SqliteTaskBoard:
    """Read native Hermes tasks without ever opening the database writable."""

    def __init__(
        self,
        db_path: Path,
        *,
        resolve_project_id: Callable[[str], str] | None = None,
    ) -> None:
        self.db_path = Path(db_path).expanduser().resolve()
        self._resolve_project_id = resolve_project_id
        if not self.db_path.is_file():
            raise MissingTaskBoardError(f"Kanban board does not exist: {self.db_path}")
        try:
            with self._connect() as connection:
                columns = {
                    row[1]
                    for row in connection.execute("PRAGMA table_info(tasks)").fetchall()
                }
                missing = [column for column in _REQUIRED_COLUMNS if column not in columns]
                if missing:
                    raise SqliteTaskBoardError(
                        f"Kanban tasks table is missing columns: {', '.join(missing)}"
                    )
                connection.execute(
                    "SELECT parent_id, child_id FROM task_links LIMIT 0"
                ).fetchall()
        except SqliteTaskBoardError:
            raise
        except sqlite3.Error as exc:
            raise MissingTaskBoardError(
                f"cannot read Kanban board: {self.db_path}"
            ) from exc

    def _connect(self) -> sqlite3.Connection:
        try:
            connection = sqlite3.connect(f"{self.db_path.as_uri()}?mode=ro", uri=True)
            connection.row_factory = sqlite3.Row
            return connection
        except sqlite3.Error as exc:
            raise MissingTaskBoardError(
                f"cannot open Kanban board read-only: {self.db_path}"
            ) from exc

    def _dependencies(self, connection: sqlite3.Connection, task_id: str) -> tuple[str, ...]:
        linked = [
            str(row[0])
            for row in connection.execute(
                "SELECT parent_id FROM task_links WHERE child_id = ?",
                (task_id,),
            ).fetchall()
            if row[0] is not None and str(row[0]).strip()
        ]
        return tuple(linked)

    def _canonical_project_id(self, project_id: str) -> str:
        """Translate a native project id to the operational id when resolvable."""
        if self._resolve_project_id is None or not project_id:
            return project_id
        return self._resolve_project_id(project_id)

    def _task(self, connection: sqlite3.Connection, row: sqlite3.Row) -> BoardTask:
        body = _sections(str(row["body"] or ""))
        dependencies = list(self._dependencies(connection, str(row["id"])))
        for dependency in _body_dependencies(body.get("Dependencies", "")):
            if dependency not in dependencies:
                dependencies.append(dependency)
        priority = body.get("Priority", "").strip()
        if priority not in _PRIORITIES:
            priority = priority or ""
        status = str(row["status"] or "").strip().lower()
        raw_path = body.get("Path", "").strip().lower()
        card_path = raw_path or "feature"
        card_skill = body.get("Skill", "").strip().lower()
        return BoardTask(
            id=str(row["id"]),
            project_id=self._canonical_project_id(str(row["project_id"] or "").strip()),
            problem=body.get("Problem", ""),
            expected_result=body.get("Expected Result", ""),
            platform=body.get("Platform", ""),
            acceptance_criteria=body.get("Acceptance Criteria", ""),
            technical_notes=body.get("Technical Notes", ""),
            dependencies=tuple(dependencies),
            owner=str(row["assignee"] or "").strip(),
            reviewer=body.get("Reviewer", ""),
            priority=priority,
            created_at=_created_at(row["created_at"]),
            complete=status in {"done", "archived"},
            column=status,
            card_path=card_path,
            card_skill=card_skill,
        )

    def get(self, task_id: str) -> BoardTask:
        try:
            with self._connect() as connection:
                row = connection.execute(
                    "SELECT id, project_id, body, assignee, status, priority, created_at "
                    "FROM tasks WHERE id = ?",
                    (task_id,),
                ).fetchone()
                if row is None:
                    raise UnknownTaskError(f"unknown task: {task_id}")
                return self._task(connection, row)
        except UnknownTaskError:
            raise
        except sqlite3.Error as exc:
            raise SqliteTaskBoardError(
                f"cannot read Kanban task {task_id}: {self.db_path}"
            ) from exc

    def list(self) -> tuple[BoardTask, ...]:
        try:
            with self._connect() as connection:
                rows = connection.execute(
                    "SELECT id, project_id, body, assignee, status, priority, created_at "
                    "FROM tasks"
                ).fetchall()
                return tuple(self._task(connection, row) for row in rows)
        except sqlite3.Error as exc:
            raise SqliteTaskBoardError(
                f"cannot list Kanban tasks: {self.db_path}"
            ) from exc

