"""Read-only access to an AiNative methodology checkout."""

from __future__ import annotations

import re
import subprocess
from dataclasses import dataclass
from pathlib import Path

from .external_framework import AINATIVE_STEP_AGENTS


class AiNativeAdapterError(Exception):
    """Base error for AiNative adapter failures."""


class InvalidMethodologyError(AiNativeAdapterError):
    """Raised when configuration or the methodology location is invalid."""


class UnknownAgentError(AiNativeAdapterError):
    """Raised when an agent name is not in the discovered roster."""


class IncompleteAgentError(AiNativeAdapterError):
    """Raised when an agent has no readable instruction files."""


class UnresolvedDependencyError(AiNativeAdapterError):
    """Raised when an agent references an unavailable skill."""


class RevisionError(AiNativeAdapterError):
    """Raised when a methodology revision cannot be captured."""


class ReadOnlyError(AiNativeAdapterError):
    """Raised when a caller attempts to mutate the methodology."""


@dataclass(frozen=True)
class AiNativeSettings:
    """Configured location and access policy for AiNative."""

    path: Path
    read_only: bool


@dataclass(frozen=True)
class AgentDefinition:
    """Raw instruction documents for one discovered agent."""

    name: str
    purpose_path: Path | None
    howto_path: Path | None
    constraints_path: Path | None
    purpose: str | None
    howto: str | None
    constraints: str | None


@dataclass(frozen=True)
class AgentDependency:
    """One rule or shared skill required by an agent."""

    kind: str
    name: str
    path: Path
    text: str


@dataclass(frozen=True)
class Revision:
    """Point-in-time git identity for the methodology checkout."""

    repository: str
    sha: str
    branch: str
    dirty: bool


@dataclass(frozen=True)
class ExecutionContext:
    """Methodology identity passed to a later executor."""

    methodology_path: Path
    revision: Revision
    agent: AgentDefinition
    workflow_phase: str | None = None


# ponytail: two-scalar YAML subset (path, read_only); no nested YAML, quotes, or aliases.
# Upgrade: PyYAML if the ainative: block grows.
def load_ainative_settings(config_path: Path) -> AiNativeSettings:
    """Load and validate the ainative settings block from a YAML file."""
    try:
        lines = config_path.read_text(encoding="utf-8").splitlines()
    except (OSError, UnicodeError) as exc:
        raise InvalidMethodologyError(f"cannot read config: {config_path}") from exc

    values: dict[str, str] = {}
    in_block = False
    for line in lines:
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        if not line[0].isspace():
            if in_block:
                break
            in_block = bool(re.fullmatch(r"ainative\s*:", stripped))
            continue
        if not in_block:
            continue
        match = re.fullmatch(r"\s*([A-Za-z_][\w-]*)\s*:\s*(.*?)\s*", line)
        if match and match.group(1) in {"path", "read_only"}:
            values[match.group(1)] = match.group(2)

    if "path" not in values or "read_only" not in values:
        raise InvalidMethodologyError("config must define ainative.path and ainative.read_only")
    raw_path = values["path"]
    if not raw_path.strip():
        raise InvalidMethodologyError("ainative.path must be a non-empty path")
    return AiNativeSettings(Path(raw_path), values["read_only"] == "true")


class AiNativeAdapter:
    """Read and identify agents from a configured AiNative checkout."""

    _instruction_files = (
        ("purpose_path", "purpose", "AGENTS.md"),
        ("howto_path", "howto", "SKILL.md"),
        ("constraints_path", "constraints", "rule.md"),
    )
    _skill_reference = re.compile(
        r"<!--\s*source:\s*_skills/([^/\s]+)/SKILL\.md\s*-->"
    )

    # Validate adapter settings before exposing any filesystem operations.
    def __init__(self, settings: AiNativeSettings) -> None:
        path = settings.path
        agents_root = path / "docs" / "agents"
        if (
            settings.read_only is not True
            or not path.is_dir()
            or not agents_root.is_dir()
        ):
            raise InvalidMethodologyError(f"invalid read-only methodology: {path}")
        self.settings = settings
        self._agents_root = agents_root

    # Construct an adapter from caller-supplied operational configuration.
    @classmethod
    def from_config(cls, config_path: Path) -> AiNativeAdapter:
        """Load settings from config and validate the methodology location."""
        return cls(load_ainative_settings(config_path))

    # Discover immediate agent directories in deterministic order.
    def list_agents(self) -> list[str]:
        """Return sorted non-reserved agent directory names."""
        try:
            children = self._agents_root.iterdir()
            return sorted(
                child.name
                for child in children
                if child.is_dir() and child.name not in {"template", "_skills"}
            )
        except OSError as exc:
            raise InvalidMethodologyError(
                f"cannot scan agent roster: {self._agents_root}"
            ) from exc

    # Read one optional instruction file while preserving its raw text.
    @staticmethod
    def _read_instruction(path: Path) -> str | None:
        try:
            if not path.exists():
                return None
            if not path.is_file():
                raise OSError(f"not a file: {path}")
            return path.read_text(encoding="utf-8")
        except (OSError, UnicodeError) as exc:
            raise IncompleteAgentError(f"cannot read instruction file: {path}") from exc

    # Validate a roster name before joining it to the agents root.
    def _agent_directory(self, name: str) -> Path:
        if name not in self.list_agents():
            raise UnknownAgentError(f"unknown agent: {name}")
        return self._agents_root / name

    # Load purpose, how-to, and constraints as separate fields.
    def get_agent(self, name: str) -> AgentDefinition:
        """Return the named agent's raw instruction documents."""
        agent_directory = self._agent_directory(name)
        paths: dict[str, Path | None] = {}
        texts: dict[str, str | None] = {}
        for path_field, text_field, filename in self._instruction_files:
            path = agent_directory / filename
            text = self._read_instruction(path)
            paths[path_field] = path if text is not None else None
            texts[text_field] = text

        if all(text is None for text in texts.values()):
            raise IncompleteAgentError(f"agent has no instructions: {name}")
        return AgentDefinition(
            name=name,
            purpose_path=paths["purpose_path"],
            howto_path=paths["howto_path"],
            constraints_path=paths["constraints_path"],
            purpose=texts["purpose"],
            howto=texts["howto"],
            constraints=texts["constraints"],
        )

    # Resolve an agent's local rule and referenced shared skills.
    def resolve_agent_dependencies(self, name: str) -> list[AgentDependency]:
        """Return all readable dependencies in first-seen order."""
        agent = self.get_agent(name)
        dependencies: list[AgentDependency] = []
        if agent.constraints_path is not None and agent.constraints is not None:
            dependencies.append(
                AgentDependency(
                    kind="rule",
                    name=agent.name,
                    path=agent.constraints_path.resolve(),
                    text=agent.constraints,
                )
            )

        if agent.howto is None:
            return dependencies

        seen: set[str] = set()
        for skill_name in self._skill_reference.findall(agent.howto):
            if skill_name in seen:
                continue
            seen.add(skill_name)
            if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._-]*", skill_name):
                raise UnresolvedDependencyError(f"invalid skill reference: {skill_name}")
            skill_path = self._agents_root / "_skills" / skill_name / "SKILL.md"
            try:
                skill_text = skill_path.read_text(encoding="utf-8")
            except (OSError, UnicodeError) as exc:
                raise UnresolvedDependencyError(
                    f"cannot read referenced skill: {skill_name}"
                ) from exc
            dependencies.append(
                AgentDependency(
                    kind="skill",
                    name=skill_name,
                    path=skill_path.resolve(),
                    text=skill_text,
                )
            )
        return dependencies

    # Resolve one live loop agent state (ready/critic/tester/pr-review).
    def resolve_step_agent(self, step_id: str) -> AgentDefinition:
        """Map one agent-kind graph state to its AiNative agent definition."""
        name = AINATIVE_STEP_AGENTS.get(step_id)
        if name is None:
            raise UnknownAgentError(f"step is not an AiNative agent state: {step_id}")
        return self.get_agent(name)

    # Run git in a requested methodology path and return trimmed output.
    @staticmethod
    def _git_output(path: Path, *args: str) -> str:
        try:
            result = subprocess.run(
                ["git", "-C", str(path), *args],
                check=True,
                capture_output=True,
                text=True,
            )
        except (OSError, subprocess.CalledProcessError) as exc:
            raise RevisionError(f"cannot read git metadata: {path}") from exc
        return result.stdout.strip()

    # Capture the current git identity and dirty state.
    def capture_revision(self, path: Path) -> Revision:
        """Return git revision metadata for a methodology checkout."""
        sha = self._git_output(path, "rev-parse", "HEAD")
        if not sha:
            raise RevisionError(f"empty git revision: {path}")
        branch = self._git_output(path, "rev-parse", "--abbrev-ref", "HEAD")
        if not branch:
            raise RevisionError(f"empty git branch: {path}")
        if branch == "HEAD":
            branch = "detached"
        try:
            repository = self._git_output(path, "remote", "get-url", "origin")
        except RevisionError:
            repository = str(path)
        dirty = bool(self._git_output(path, "status", "--porcelain"))
        return Revision(repository or str(path), sha, branch, dirty)

    # Build a context stamped with the configured methodology revision.
    def build_execution_context(
        self,
        agent: AgentDefinition,
        *,
        workflow_phase: str | None = None,
    ) -> ExecutionContext:
        """Return execution identity without inventing task metadata."""
        return ExecutionContext(
            methodology_path=self.settings.path,
            revision=self.capture_revision(self.settings.path),
            agent=agent,
            workflow_phase=workflow_phase,
        )

    # Refuse a write before touching the methodology filesystem.
    def write_file(self, relative_path: str, content: str) -> None:
        """Reject all file writes through the adapter."""
        raise ReadOnlyError("AiNative methodology is read-only")

    # Refuse a copy before touching either filesystem.
    def copy_tree(self, destination: Path) -> None:
        """Reject all methodology copies through the adapter."""
        raise ReadOnlyError("AiNative methodology is read-only")
