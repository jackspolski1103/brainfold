from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

import pytest

from oif import OIFError
from oif.brain import Brain

EXAMPLE = Path(__file__).parent.parent / "examples" / "brain"
ALICE, BOB, REVIEWER, CARLA = (
    f"{name}@atlas.test" for name in ("alice", "bob", "reviewer", "carla")
)


@pytest.fixture
def groups() -> dict[str, list[str]]:
    return {"costs": [ALICE, REVIEWER], "contracts": [BOB, REVIEWER]}


@pytest.fixture
def brain(tmp_path: Path, groups: dict[str, list[str]]) -> Brain:
    shutil.copytree(EXAMPLE, tmp_path / "brain")
    return Brain(tmp_path / "brain", lambda: groups)


def paths(listing: dict) -> list[str]:
    return [entry["path"] for entry in listing["entries"]]


def denied(call, *args) -> str:
    with pytest.raises(OIFError) as error:
        call(*args)
    return error.value.code


def test_listing_guides_and_hides_what_is_not_granted(brain: Brain) -> None:
    root = brain.list(ALICE, "/")
    assert root["start_here"] and root["description"]
    assert {e["path"]: e.get("description") for e in root["entries"]}["/skills"]
    assert "read" not in root
    assert paths(brain.list(ALICE, "/projects")) == ["/projects/costs"]
    assert paths(brain.list(BOB, "/projects")) == ["/projects/contracts"]
    assert paths(brain.list(BOB, "/people")) == []
    assert not any(".oif" in path for path in paths(root))


def test_skills_are_discovered_only_where_readable(brain: Brain) -> None:
    assert brain.skills(ALICE)["skills"] == [
        {
            "path": "/skills/analyze-costs/SKILL.md",
            "name": "analyze-costs",
            "description": "Analyze a project's costs without presenting totals from truncated "
            "samples.",
        }
    ]
    assert brain.skills(BOB)["skills"] == []


def test_denials_are_indistinguishable_from_absence(brain: Brain) -> None:
    for who, call, path in (
        (BOB, brain.read, "/people/alice/preferences.md"),
        (BOB, brain.read, "/people/alice/missing.md"),
        (REVIEWER, brain.read, "/people/alice/preferences.md"),
        (CARLA, brain.list, "/"),
        (ALICE, brain.read, "/.oif.toml"),
        (ALICE, brain.read, "/common/../.oif.toml"),
        (ALICE, brain.list, "/.git"),
        (ALICE, brain.read, "comun/conventions.md"),
        (ALICE, brain.read, "/common//conventions.md"),
        (ALICE, brain.read, "/common/%2e%2e/.oif.toml"),
        (ALICE, brain.read, "/common\\conventions.md"),
    ):
        assert denied(call, who, path) == "unavailable"


def test_symlinks_and_broken_metadata_fail_closed(brain: Brain) -> None:
    (brain.root / "common" / "leak.md").symlink_to(
        brain.root / "people" / "alice" / "preferences.md"
    )
    assert "/common/leak.md" not in paths(brain.list(BOB, "/common"))
    assert denied(brain.read, BOB, "/common/leak.md") == "unavailable"
    (brain.root / "common" / ".oif.toml").write_text("read = 'alice'")
    assert denied(brain.read, ALICE, "/common/conventions.md") == "unavailable"


def test_write_needs_its_own_grant_and_revocation_applies_at_once(
    brain: Brain, groups: dict[str, list[str]]
) -> None:
    assert brain.list(ALICE, "/projects/costs")["can_write"]
    brain.write(ALICE, "/projects/costs/notes/learning.md", "v1")
    assert brain.read(REVIEWER, "/projects/costs/notes/learning.md")["content"] == "v1"
    assert brain.search(REVIEWER, "V1")["hits"][0]["path"].endswith("learning.md")
    assert brain.search(BOB, "v1")["hits"] == []
    # Readable but not writable, unreadable, metadata and folders.
    assert denied(brain.write, ALICE, "/common/conventions.md", "x") == "write_denied"
    assert denied(brain.write, BOB, "/projects/costs/x.md", "x") == "unavailable"
    assert denied(brain.write, ALICE, "/projects/costs/.oif.toml", "x") == "unavailable"
    assert denied(brain.write, ALICE, "/projects/costs", "x") == "unavailable"
    assert denied(brain.write, ALICE, "/projects/costs/g.md", "x" * 70_000) == ("file_too_large")
    groups["costs"].remove(ALICE)
    assert denied(brain.read, ALICE, "/projects/costs/process.md") == "unavailable"


def test_administrators_manage_grants_without_reading_content(brain: Brain) -> None:
    managed = brain.list(CARLA, "/projects", manage=True)
    assert {e["path"]: e["read"] for e in managed["entries"]} == {
        "/projects/contracts": ["@contracts"],
        "/projects/costs": ["@costs"],
    }
    assert denied(brain.read, CARLA, "/projects/costs/process.md") == "unavailable"
    brain.set_meta(CARLA, "/projects/costs", 'Costs "2026"', [], ["@costs", BOB], None)
    assert brain.read(BOB, "/projects/costs/process.md")["content"]
    assert not brain.list(ALICE, "/projects/costs")["can_write"]  # write no longer declared
    assert brain.list(ALICE, "/projects/costs")["description"] == 'Costs "2026"'
    for bad in (["not a grant"], ["@Invalid Group"]):
        assert (
            denied(brain.set_meta, CARLA, "/projects/costs", "", [], bad, None)
            == "invalid_metadata"
        )
    assert denied(brain.set_meta, CARLA, "/common", "", ["../x"], None, None) == "invalid_metadata"


def test_writes_are_committed_when_the_brain_is_a_git_repository(brain: Brain) -> None:
    subprocess.run(["git", "init", "-q", str(brain.root)], check=True)
    assert brain.write(ALICE, "/people/alice/note.md", "hello")["versioned"]
    log = subprocess.run(
        ["git", "-C", str(brain.root), "log", "--format=%ae %s"], capture_output=True, text=True
    )
    assert log.stdout.strip() == f"{ALICE} {ALICE}: people/alice/note.md"
