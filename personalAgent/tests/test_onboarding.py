"""Hermetic onboarding checks: no network, no live board, no live model."""

import sqlite3
import subprocess
from pathlib import Path

import pytest

from hermes_kanban.onboard import (
    ImportPrdRequest,
    OnboardError,
    OnboardRequest,
    PrdDraftError,
    render_card_draft,
    run_import_prd,
    run_onboard,
    validate_card_draft,
)
from hermes_kanban.projects import ProjectRegistry

REPOSITORY = "owner/new-project"
NATIVE_ID = "p_1234567"


def write_projects_db(tmp_path: Path, rows: list[tuple[str, str]]) -> Path:
    database = tmp_path / "projects.db"
    connection = sqlite3.connect(database)
    connection.execute("create table projects (id text, slug text)")
    connection.executemany("insert into projects values (?, ?)", rows)
    connection.commit()
    connection.close()
    return database


def write_config(tmp_path: Path, workspace_root: Path, entries: str = "") -> Path:
    workspace_root.mkdir(parents=True, exist_ok=True)
    config = tmp_path / "config.yaml"
    config.write_text(
        f"workspace:\n  root: {workspace_root}\nprojects:\n{entries}",
        encoding="utf-8",
    )
    return config


def _git(*args: str, cwd: Path | None = None) -> None:
    subprocess.run(["git", *args], cwd=cwd, check=True, capture_output=True)


def fake_cloner(url: str, location: Path, branch: str) -> None:
    location.mkdir(parents=True)
    _git("init", "-b", branch, cwd=location)
    _git("remote", "add", "origin", url, cwd=location)
    _git("commit", "--allow-empty", "-m", "seed", cwd=location)


def request(**overrides: object) -> OnboardRequest:
    values: dict[str, object] = {"repository": REPOSITORY}
    values.update(overrides)
    return OnboardRequest(**values)  # type: ignore[arg-type]


def test_onboard_enrolls_clones_scaffolds_and_loads_context(tmp_path: Path) -> None:
    workspace = tmp_path / "workspaces"
    config = write_config(tmp_path, workspace)
    projects_db = write_projects_db(tmp_path, [(NATIVE_ID, "owner/new-project")])

    result = run_onboard(
        request(), config, cloner=fake_cloner, projects_db=projects_db
    )

    assert result.cloned is True
    assert result.native_id == NATIVE_ID
    assert result.location == workspace / "new-project"
    assert (result.location / ".git").is_dir()
    assert set(result.scaffolded) == {"README.md", "AGENTS.md", ".ainative/project.yaml"}
    registry = ProjectRegistry.from_config(config)
    record = registry.get_project("new-project")
    assert record.kanban_project_ids == (NATIVE_ID,)
    assert record.default_branch == "main"
    assert registry.canonical_id(NATIVE_ID) == "new-project"
    registry.load_project_context("new-project")


def test_onboard_reuses_existing_matching_clone(tmp_path: Path) -> None:
    workspace = tmp_path / "workspaces"
    config = write_config(tmp_path, workspace)
    projects_db = write_projects_db(tmp_path, [(NATIVE_ID, "owner/new-project")])
    location = workspace / "new-project"
    location.mkdir(parents=True)
    _git("init", "-b", "main", cwd=location)
    _git("remote", "add", "origin", "git@github.com:owner/new-project.git", cwd=location)

    result = run_onboard(
        request(), config, cloner=fake_cloner, projects_db=projects_db
    )

    assert result.cloned is False
    assert set(result.scaffolded) == {"README.md", "AGENTS.md", ".ainative/project.yaml"}


def test_onboard_fails_closed_when_native_creation_fails(tmp_path: Path) -> None:
    workspace = tmp_path / "workspaces"
    config = write_config(tmp_path, workspace)
    projects_db = write_projects_db(tmp_path, [])
    before = config.read_text(encoding="utf-8")

    def failing_creator(repository: str) -> None:
        raise OnboardError("hermes project create failed")

    with pytest.raises(OnboardError, match="hermes project create failed"):
        run_onboard(
            request(),
            config,
            cloner=fake_cloner,
            projects_db=projects_db,
            native_project_creator=failing_creator,
        )

    assert config.read_text(encoding="utf-8") == before
    assert not (workspace / "new-project").exists()


def test_onboard_fails_closed_on_ambiguous_native_project(tmp_path: Path) -> None:
    workspace = tmp_path / "workspaces"
    config = write_config(tmp_path, workspace)
    projects_db = write_projects_db(
        tmp_path,
        [(NATIVE_ID, "owner/new-project"), (NATIVE_ID + "8", "owner-new-project")],
    )

    with pytest.raises(OnboardError, match="ambiguously"):
        run_onboard(request(), config, cloner=fake_cloner, projects_db=projects_db)


def test_onboard_creates_missing_native_project(tmp_path: Path) -> None:
    workspace = tmp_path / "workspaces"
    config = write_config(tmp_path, workspace)
    projects_db = write_projects_db(tmp_path, [])
    created: list[str] = []

    def creator(repository: str) -> None:
        created.append(repository)
        connection = sqlite3.connect(projects_db)
        connection.execute(
            "insert into projects values (?, ?)", (NATIVE_ID, "owner-new-project")
        )
        connection.commit()
        connection.close()

    result = run_onboard(
        request(),
        config,
        cloner=fake_cloner,
        projects_db=projects_db,
        native_project_creator=creator,
    )

    assert created == [REPOSITORY]
    assert result.native_id == NATIVE_ID
    registry = ProjectRegistry.from_config(config)
    assert registry.canonical_id(NATIVE_ID) == "new-project"


def test_onboard_dry_run_does_not_create_native_project(tmp_path: Path) -> None:
    workspace = tmp_path / "workspaces"
    config = write_config(tmp_path, workspace)
    projects_db = write_projects_db(tmp_path, [])

    with pytest.raises(OnboardError, match="no native Hermes project"):
        run_onboard(
            request(dry_run=True),
            config,
            cloner=fake_cloner,
            projects_db=projects_db,
            native_project_creator=lambda repository: pytest.fail("must not create"),
        )


def test_onboard_fails_closed_on_duplicate_native_alias(tmp_path: Path) -> None:
    workspace = tmp_path / "workspaces"
    existing = workspace / "existing"
    existing.mkdir(parents=True)
    entries = (
        "  - id: existing\n"
        "    name: owner/existing\n"
        "    repository: github.com/owner/existing\n"
        f"    location: {existing}\n"
        "    kanban_project_ids:\n"
        f"      - {NATIVE_ID}\n"
    )
    config = write_config(tmp_path, workspace, entries=entries)
    projects_db = write_projects_db(tmp_path, [(NATIVE_ID, "owner/new-project")])
    before = config.read_text(encoding="utf-8")

    with pytest.raises(OnboardError, match="invalid config"):
        run_onboard(request(), config, cloner=fake_cloner, projects_db=projects_db)

    assert config.read_text(encoding="utf-8") == before


def test_onboard_rejects_mismatched_re_enrollment(tmp_path: Path) -> None:
    workspace = tmp_path / "workspaces"
    location = workspace / "new-project"
    entries = (
        "  - id: new-project\n"
        "    name: owner/other\n"
        "    repository: github.com/owner/other\n"
        f"    location: {location}\n"
        "    kanban_project_ids:\n"
        f"      - {NATIVE_ID}\n"
    )
    config = write_config(tmp_path, workspace, entries=entries)

    with pytest.raises(OnboardError, match="already enrolled"):
        run_onboard(request(), config, cloner=fake_cloner)


def test_onboard_is_idempotent_when_already_enrolled(tmp_path: Path) -> None:
    workspace = tmp_path / "workspaces"
    entries = (
        "  - id: new-project\n"
        f"    name: {REPOSITORY}\n"
        f"    repository: {REPOSITORY}\n"
        f"    location: {workspace / 'new-project'}\n"
        "    kanban_project_ids:\n"
        f"      - {NATIVE_ID}\n"
    )
    config = write_config(tmp_path, workspace, entries=entries)

    result = run_onboard(request(), config, cloner=fake_cloner)

    assert result.already_enrolled is True
    assert result.native_id == NATIVE_ID
    assert result.scaffolded == ()


def test_onboard_dry_run_writes_nothing(tmp_path: Path) -> None:
    workspace = tmp_path / "workspaces"
    config = write_config(tmp_path, workspace)
    projects_db = write_projects_db(tmp_path, [(NATIVE_ID, "owner/new-project")])
    before = config.read_text(encoding="utf-8")

    result = run_onboard(
        request(dry_run=True), config, cloner=fake_cloner, projects_db=projects_db
    )

    assert result.cloned is False
    assert result.scaffolded == ()
    assert config.read_text(encoding="utf-8") == before
    assert not (workspace / "new-project").exists()


def test_onboard_rejects_bad_repository_format(tmp_path: Path) -> None:
    config = write_config(tmp_path, tmp_path)

    with pytest.raises(OnboardError, match="owner/name"):
        run_onboard(request(repository="just-a-name"), config, cloner=fake_cloner)


def test_onboard_enrolls_via_overlay_when_config_is_read_only(tmp_path: Path) -> None:
    workspace = tmp_path / "workspaces"
    overlay_dir = tmp_path / "overlay"
    overlay_dir.mkdir()
    workspace.mkdir(parents=True, exist_ok=True)
    config = tmp_path / "config.yaml"
    base_location = workspace / "ich-mag-dich"
    base_location.mkdir()
    config.write_text(
        "projects:\n"
        "  - id: ich-mag-dich\n"
        "    name: owner/ich-mag-dich\n"
        "    repository: github.com/owner/ich-mag-dich\n"
        f"    location: {base_location}\n"
        "    default_branch: main\n"
        f"workspace:\n  root: {workspace}\n"
        f"execution:\n  overlay_dir: {overlay_dir}\n",
        encoding="utf-8",
    )
    before = config.read_text(encoding="utf-8")
    projects_db = write_projects_db(tmp_path, [(NATIVE_ID, "owner/new-project")])
    mode = tmp_path.stat().st_mode
    tmp_path.chmod(mode & ~0o222)
    try:
        result = run_onboard(
            request(), config, cloner=fake_cloner, projects_db=projects_db
        )
    finally:
        tmp_path.chmod(mode)

    assert result.cloned is True
    assert result.native_id == NATIVE_ID
    assert config.read_text(encoding="utf-8") == before
    assert not (config.parent / "config.yaml.onboard-tmp").exists()
    overlay = overlay_dir / "enrolled-projects.yaml"
    assert "id: new-project" in overlay.read_text(encoding="utf-8")
    registry = ProjectRegistry.from_config(config)
    base = registry.get_project("ich-mag-dich")
    assert base.location == workspace / "ich-mag-dich"
    record = registry.get_project("new-project")
    assert record.kanban_project_ids == (NATIVE_ID,)
    assert registry.canonical_id(NATIVE_ID) == "new-project"


PRD = """# My project PRD

Intro paragraph that is ignored.

## Ship login

Priority: P1

Users cannot sign in.

Expected result: users can sign in with a password.

## Dark mode toggle

Users want a dark theme.
"""

DRAFT_WITH_TODO = """# Dark mode toggle

## Priority
P2

## Problem
Users want a dark theme.

## Expected Result
TODO: expected result — complete before grooming.
"""


def test_import_prd_creates_valid_drafts(tmp_path: Path) -> None:
    prd = tmp_path / "PRD.md"
    prd.write_text(PRD, encoding="utf-8")
    out_dir = tmp_path / "drafts"

    from hermes_kanban.onboard import import_prd

    drafts, incomplete = import_prd(prd, out_dir)

    assert len(drafts) == 2
    assert incomplete == 1
    login = drafts[0].read_text(encoding="utf-8")
    validate_card_draft(login)
    assert "## Priority\nP1" in login
    validate_card_draft(drafts[1].read_text(encoding="utf-8"))


def test_import_prd_rejects_declared_invalid_priority(tmp_path: Path) -> None:
    prd = tmp_path / "PRD.md"
    prd.write_text("## Broken card\n\nPriority: P9\n\nBody text.\n", encoding="utf-8")

    from hermes_kanban.onboard import import_prd

    with pytest.raises(PrdDraftError, match="invalid priority P9"):
        import_prd(prd, tmp_path / "drafts")


def test_card_draft_render_validate_round_trip() -> None:
    from hermes_kanban.onboard import CardDraft

    draft = CardDraft(
        title="Example",
        priority="P3",
        problem="Something is wrong.",
        expected_result="It is right.",
        technical_notes="Note.",
    )

    rendered = render_card_draft(draft)

    validate_card_draft(rendered)
    assert "## Technical Notes\nNote." in rendered


@pytest.mark.parametrize(
    "text",
    [
        "# Example\n\n## Priority\nP1\n\n## Problem\nBody.\n",
        "# Example\n\n## Priority\nP9\n\n## Problem\nBody.\n\n## Expected Result\nDone.\n",
        "# Example\n\n## Priority\nP1\n\n## Expected Result\nDone.\n",
    ],
)
def test_card_draft_validation_rejects_invalid_shapes(text: str) -> None:
    with pytest.raises(PrdDraftError):
        validate_card_draft(text)


def onboard_with_cards(tmp_path: Path, prd: str, **request_overrides: object):
    workspace = tmp_path / "workspaces"
    config = write_config(tmp_path, workspace)
    projects_db = write_projects_db(tmp_path, [(NATIVE_ID, "owner/new-project")])
    prd_path = tmp_path / "PRD.md"
    prd_path.write_text(prd, encoding="utf-8")
    created: list[list[str]] = []
    result = run_onboard(
        request(prd=prd_path, drafts_out=tmp_path / "drafts", **request_overrides),
        config,
        cloner=fake_cloner,
        projects_db=projects_db,
        card_creator=lambda args: created.append(args),
    )
    return result, created


def test_create_cards_pushes_validated_drafts_to_the_board(tmp_path: Path) -> None:
    result, created = onboard_with_cards(
        tmp_path,
        "## Ship login\n\nPriority: P1\n\nUsers cannot sign in.\n\n"
        "Expected result: users can sign in.\n",
        create_cards=True,
    )

    assert result.created_cards == ("Ship login",)
    assert result.triaged_cards == 0
    assert len(created) == 1
    args = created[0]
    assert args[0] == "Ship login"
    assert args[args.index("--project") + 1] == NATIVE_ID
    assert args[args.index("--priority") + 1] == "P1"
    assert args[args.index("--idempotency-key") + 1] == "ship-login"
    assert "--triage" not in args


def test_create_cards_trips_incomplete_drafts_into_triage(tmp_path: Path) -> None:
    result, created = onboard_with_cards(
        tmp_path,
        "## Dark mode\n\nUsers want a dark theme.\n",
        create_cards=True,
        allow_todo=True,
    )

    assert result.created_cards == ("Dark mode",)
    assert result.triaged_cards == 1
    args = created[0]
    assert args[-1] == "--triage"


def test_create_cards_fail_closed_on_todo_without_allow(tmp_path: Path) -> None:
    with pytest.raises(PrdDraftError, match="TODO sections"):
        onboard_with_cards(
            tmp_path,
            "## Dark mode\n\nUsers want a dark theme.\n",
            create_cards=True,
        )


def test_without_create_cards_drafts_stay_files(tmp_path: Path) -> None:
    result, created = onboard_with_cards(
        tmp_path,
        "## Ship login\n\nPriority: P1\n\nUsers cannot sign in.\n\n"
        "Expected result: users can sign in.\n",
    )

    assert result.created_cards == ()
    assert created == []


def _git_out(*args: str, cwd: Path) -> str:
    return subprocess.run(
        ["git", *args], cwd=cwd, check=True, capture_output=True, text=True
    ).stdout


def test_onboard_commits_scaffold_files(tmp_path: Path) -> None:
    workspace = tmp_path / "workspaces"
    config = write_config(tmp_path, workspace)
    projects_db = write_projects_db(tmp_path, [(NATIVE_ID, "owner/new-project")])

    result = run_onboard(request(), config, cloner=fake_cloner, projects_db=projects_db)

    status = _git_out("status", "--porcelain", cwd=result.location)
    assert status == ""
    last = _git_out("log", "-1", "--format=%s", cwd=result.location).strip()
    assert last == "chore: ainative onboarding scaffold"
    names = _git_out(
        "show", "--name-only", "--format=", "HEAD", cwd=result.location
    ).splitlines()
    assert set(names) == {"README.md", "AGENTS.md", ".ainative/project.yaml"}


def test_onboard_does_not_commit_preexisting_unrelated_files(tmp_path: Path) -> None:
    workspace = tmp_path / "workspaces"
    config = write_config(tmp_path, workspace)
    projects_db = write_projects_db(tmp_path, [(NATIVE_ID, "owner/new-project")])
    location = workspace / "new-project"
    fake_cloner("git@github.com:owner/new-project.git", location, "main")
    (location / "operator-note.txt").write_text("mine", encoding="utf-8")

    result = run_onboard(request(), config, projects_db=projects_db)

    status = _git_out("status", "--porcelain", cwd=result.location).splitlines()
    assert status == ["?? operator-note.txt"]


def test_onboard_composes_existing_agents_md_once(tmp_path: Path) -> None:
    workspace = tmp_path / "workspaces"
    config = write_config(tmp_path, workspace)
    projects_db = write_projects_db(tmp_path, [(NATIVE_ID, "owner/new-project")])
    location = workspace / "new-project"
    fake_cloner("git@github.com:owner/new-project.git", location, "main")
    (location / "AGENTS.md").write_text(
        "# Project rules\n\n- Custom project rule.\n", encoding="utf-8"
    )

    run_onboard(request(), config, projects_db=projects_db)

    text = (location / "AGENTS.md").read_text(encoding="utf-8")
    assert text.startswith("# Project rules\n")
    assert "Custom project rule." in text
    assert "## Hermes control plane" in text
    assert text.count("## Hermes control plane") == 1


def test_onboard_reenroll_does_not_duplicate_agents_section(tmp_path: Path) -> None:
    workspace = tmp_path / "workspaces"
    config = write_config(tmp_path, workspace)
    projects_db = write_projects_db(tmp_path, [(NATIVE_ID, "owner/new-project")])

    first = run_onboard(request(), config, cloner=fake_cloner, projects_db=projects_db)
    text = (first.location / "AGENTS.md").read_text(encoding="utf-8")
    assert text.count("## Hermes control plane") == 1


def _enrolled(tmp_path: Path):
    workspace = tmp_path / "workspaces"
    config = write_config(tmp_path, workspace)
    projects_db = write_projects_db(tmp_path, [(NATIVE_ID, "owner/new-project")])
    result = run_onboard(request(), config, cloner=fake_cloner, projects_db=projects_db)
    return config, result


def _fake_cards():
    created: list[list[str]] = []

    def creator(args: list[str]) -> None:
        created.append(args)

    return creator, created


def test_import_prd_creates_cards_for_enrolled_project(tmp_path: Path) -> None:
    config, enrolled = _enrolled(tmp_path)
    prd = tmp_path / "prd.md"
    prd.write_text(
        "## Ship login\n\nPriority: P1\n\nUsers cannot sign in.\n\n"
        "Expected result: users can sign in.\n",
        encoding="utf-8",
    )
    creator, created = _fake_cards()

    result = run_import_prd(
        ImportPrdRequest(
            repository="owner/new-project",
            prd=prd,
            drafts_out=tmp_path / "drafts",
            create_cards=True,
        ),
        config,
        card_creator=creator,
    )

    assert result.project_id == "new-project"
    assert result.native_id == NATIVE_ID
    assert result.created_cards == ("Ship login",)
    assert len(created) == 1
    args = created[0]
    assert args[args.index("--project") + 1] == NATIVE_ID
    assert args[args.index("--priority") + 1] == "P1"
    assert not (tmp_path / "drafts").exists() or any((tmp_path / "drafts").iterdir())


def test_import_prd_writes_drafts_without_create_cards(tmp_path: Path) -> None:
    config, _ = _enrolled(tmp_path)
    prd = tmp_path / "prd.md"
    prd.write_text("## Dark mode\n\nUsers want a dark theme.\n", encoding="utf-8")
    creator, created = _fake_cards()

    result = run_import_prd(
        ImportPrdRequest(repository="owner/new-project", prd=prd),
        config,
        card_creator=creator,
    )

    assert result.drafts
    assert all(path.is_file() for path in result.drafts)
    assert result.created_cards == ()
    assert created == []


def test_import_prd_dry_run_writes_nothing(tmp_path: Path) -> None:
    config, _ = _enrolled(tmp_path)
    prd = tmp_path / "prd.md"
    prd.write_text("## Dark mode\n\nUsers want a dark theme.\n", encoding="utf-8")
    creator, created = _fake_cards()

    result = run_import_prd(
        ImportPrdRequest(repository="owner/new-project", prd=prd, dry_run=True),
        config,
        card_creator=creator,
    )

    assert result.drafts == ()
    assert created == []
    assert not (tmp_path / "drafts").exists()


def test_import_prd_fail_closed_on_unknown_project(tmp_path: Path) -> None:
    config, _ = _enrolled(tmp_path)
    prd = tmp_path / "prd.md"
    prd.write_text("## Dark mode\n\nUsers want a dark theme.\n", encoding="utf-8")

    with pytest.raises(OnboardError, match="not enrolled"):
        run_import_prd(
            ImportPrdRequest(repository="owner/other", prd=prd), config
        )


def test_import_prd_fail_closed_on_todo_without_allow(tmp_path: Path) -> None:
    config, _ = _enrolled(tmp_path)
    prd = tmp_path / "prd.md"
    prd.write_text("## Dark mode\n\nUsers want a dark theme.\n", encoding="utf-8")
    creator, created = _fake_cards()

    with pytest.raises(PrdDraftError, match="TODO sections"):
        run_import_prd(
            ImportPrdRequest(
                repository="owner/new-project",
                prd=prd,
                create_cards=True,
            ),
            config,
            card_creator=creator,
        )

    assert created == []


def _seed_remote(tmp_path: Path) -> tuple[str, Path]:
    """A local bare remote seeded with one commit, like a fresh GitHub repo."""
    seed = tmp_path / "seed"
    remote = tmp_path / "remote.git"
    seed.mkdir()
    _git("init", "-b", "main", cwd=seed)
    _git("config", "user.email", "tests@example.com", cwd=seed)
    _git("config", "user.name", "Tests", cwd=seed)
    (seed / "seed.txt").write_text("seed", encoding="utf-8")
    _git("add", ".", cwd=seed)
    _git("commit", "-m", "seed", cwd=seed)
    _git("clone", "--bare", str(seed), str(remote), cwd=tmp_path)
    return str(remote), remote


def _cloner_from(remote_url: str):
    def cloner(url: str, location: Path, branch: str) -> None:
        subprocess.run(
            ["git", "clone", "--branch", branch, remote_url, str(location)],
            check=True,
            capture_output=True,
        )

    return cloner


def test_onboard_push_scaffold_updates_remote(tmp_path: Path) -> None:
    remote_url, remote = _seed_remote(tmp_path)
    workspace = tmp_path / "workspaces"
    config = write_config(tmp_path, workspace)
    projects_db = write_projects_db(tmp_path, [(NATIVE_ID, "owner/new-project")])

    result = run_onboard(
        request(push_scaffold=True),
        config,
        cloner=_cloner_from(remote_url),
        projects_db=projects_db,
    )

    assert result.pushed is True
    seed_sha = _git_out("rev-parse", "HEAD", cwd=tmp_path / "seed").strip()
    remote_sha = _git_out("rev-parse", "refs/heads/main", cwd=remote).strip()
    assert remote_sha != seed_sha


def test_onboard_without_push_flag_keeps_remote_untouched(tmp_path: Path) -> None:
    remote_url, remote = _seed_remote(tmp_path)
    workspace = tmp_path / "workspaces"
    config = write_config(tmp_path, workspace)
    projects_db = write_projects_db(tmp_path, [(NATIVE_ID, "owner/new-project")])

    result = run_onboard(
        request(),
        config,
        cloner=_cloner_from(remote_url),
        projects_db=projects_db,
    )

    assert result.pushed is False
    seed_sha = _git_out("rev-parse", "HEAD", cwd=tmp_path / "seed").strip()
    remote_sha = _git_out("rev-parse", "refs/heads/main", cwd=remote).strip()
    assert remote_sha == seed_sha


def test_onboard_push_failure_is_fail_closed(tmp_path: Path) -> None:
    # fake_cloner registers an unreachable SSH origin; the push must fail and
    # leave the config untouched.
    workspace = tmp_path / "workspaces"
    config = write_config(tmp_path, workspace)
    projects_db = write_projects_db(tmp_path, [(NATIVE_ID, "owner/new-project")])
    before = config.read_text(encoding="utf-8")

    with pytest.raises(OnboardError, match="git push failed"):
        run_onboard(
            request(push_scaffold=True),
            config,
            cloner=fake_cloner,
            projects_db=projects_db,
        )

    assert config.read_text(encoding="utf-8") == before
