"""Question-and-answer front for enroll and card creation."""

from __future__ import annotations

import sys
from collections.abc import Callable
from pathlib import Path

from .onboard import (
    CardDraft,
    OnboardError,
    OnboardRequest,
    OnboardResult,
    _slugify,
    live_create_card,
    priority_flag,
    render_card_draft,
    run_onboard,
    validate_card_draft,
)
from .projects import ProjectRegistryError, load_project_entries

InputFn = Callable[[str], str]
OutputFn = Callable[[str], None]
OnboardFn = Callable[[OnboardRequest, Path], OnboardResult]
CardCreateFn = Callable[[list[str]], None]

_PRIORITIES = ("P0", "P1", "P2", "P3")
_KINDS = (
    ("prd", "Write a PRD", "job", "prd-writer"),
    ("bootstrap", "Set up from the PRD", "job", "project-bootstrapper"),
    ("feature", "A feature", "feature", ""),
    ("change", "A small change", "change", ""),
)


class GuideError(Exception):
    """Raised when the operator stops the interview or gives up."""


def _ask(prompt: str, input_fn: InputFn) -> str:
    """Read one stripped answer."""
    try:
        return input_fn(prompt).strip()
    except EOFError as exc:
        raise GuideError("stopped") from exc


def _choose(
    prompt: str,
    options: tuple[tuple[str, str], ...],
    input_fn: InputFn,
    output_fn: OutputFn,
) -> str:
    """Ask until the answer is one of the numbered options."""
    while True:
        output_fn(prompt)
        for index, (_, label) in enumerate(options, start=1):
            output_fn(f"  {index}. {label}")
        raw = _ask("Choice: ", input_fn)
        if raw.isdigit() and 1 <= int(raw) <= len(options):
            return options[int(raw) - 1][0]
        output_fn(f"Enter a number from 1 to {len(options)}.")


def _required(prompt: str, input_fn: InputFn, output_fn: OutputFn) -> str:
    """Ask until the answer is non-empty."""
    while True:
        value = _ask(prompt, input_fn)
        if value:
            return value
        output_fn("That needs an answer.")


def _priority(input_fn: InputFn, output_fn: OutputFn) -> str:
    """Ask for P0–P3, treating a blank answer as P2."""
    while True:
        raw = _ask("Priority (P0–P3) [P2]: ", input_fn).upper()
        if not raw:
            return "P2"
        if raw in _PRIORITIES:
            return raw
        output_fn("Priority must be P0, P1, P2, or P3.")


def card_text(
    *,
    title: str,
    priority: str,
    problem: str,
    expected_result: str,
    path: str,
    skill: str,
) -> str:
    """Render one card body with the headings the dispatcher reads."""
    text = render_card_draft(
        CardDraft(
            title=title,
            priority=priority,
            problem=problem,
            expected_result=expected_result,
            technical_notes="",
        )
    )
    lines = [text.rstrip("\n"), "", "## Path", path]
    if skill:
        lines.extend(["", "## Skill", skill])
    rendered = "\n".join(lines) + "\n"
    validate_card_draft(rendered)
    return rendered


def run_guide(
    config_path: Path,
    *,
    input_fn: InputFn = input,
    output_fn: OutputFn = print,
    onboard: OnboardFn = run_onboard,
    card_creator: CardCreateFn = live_create_card,
) -> int:
    """Interview the operator, then enroll a repository or create one card."""
    try:
        action = _choose(
            "What do you want to do?",
            (("project", "Enroll a repository"), ("card", "Add a card")),
            input_fn,
            output_fn,
        )
        if action == "project":
            return _enroll(config_path, input_fn, output_fn, onboard)
        return _add_card(config_path, input_fn, output_fn, card_creator)
    except (GuideError, OnboardError) as exc:
        print(str(exc), file=sys.stderr)
        return 1


def _enroll(
    config_path: Path,
    input_fn: InputFn,
    output_fn: OutputFn,
    onboard: OnboardFn,
) -> int:
    """Collect enroll answers and run the existing onboard command."""
    repository = _required("Repository (owner/name): ", input_fn, output_fn)
    branch = _ask("Branch [main]: ", input_fn) or "main"
    mode = _choose(
        "Enroll it?",
        (("enroll", "Enroll for real"), ("dry-run", "Dry run")),
        input_fn,
        output_fn,
    )
    from .runtime import _print_onboard_result

    result = onboard(
        OnboardRequest(repository=repository, branch=branch, dry_run=mode == "dry-run"),
        config_path,
    )
    _print_onboard_result(result, dry_run=mode == "dry-run")
    return 0


def _add_card(
    config_path: Path,
    input_fn: InputFn,
    output_fn: OutputFn,
    card_creator: CardCreateFn,
) -> int:
    """Collect card answers and create one native Kanban card."""
    try:
        enrolled = load_project_entries(config_path)
    except ProjectRegistryError as exc:
        raise GuideError(str(exc)) from exc
    projects = tuple(
        project for project in enrolled if project.enabled and project.kanban_project_ids
    )
    if not projects:
        raise GuideError("no enrolled project with a native id; enroll one first")
    project_id = _choose(
        "Which project?",
        tuple((project.id, f"{project.id} ({project.repository})") for project in projects),
        input_fn,
        output_fn,
    )
    project = next(project for project in projects if project.id == project_id)
    kind_id = _choose(
        "What kind of card?",
        tuple((kind[0], kind[1]) for kind in _KINDS),
        input_fn,
        output_fn,
    )
    _, _, path, skill = next(kind for kind in _KINDS if kind[0] == kind_id)
    title = _required("Title: ", input_fn, output_fn)
    priority = _priority(input_fn, output_fn)
    problem = _required("Problem: ", input_fn, output_fn)
    expected = _required("Expected result: ", input_fn, output_fn)
    body = card_text(
        title=title,
        priority=priority,
        problem=problem,
        expected_result=expected,
        path=path,
        skill=skill,
    )
    card_creator(
        [
            title,
            "--project",
            project.kanban_project_ids[0],
            "--priority",
            priority_flag(priority),
            "--body",
            body,
            "--idempotency-key",
            _slugify(title),
        ]
    )
    output_fn(f"card: {title}")
    return 0
