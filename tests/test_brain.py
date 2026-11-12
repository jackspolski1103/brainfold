from __future__ import annotations

import shutil
import subprocess
import threading
from pathlib import Path

import pytest

from oif import OIFError
from oif.brain import LEARNING, MAX_READ_BYTES, Brain

EXAMPLE = Path(__file__).parent.parent / "examples" / "brain"
ALICE, BOB, REVIEWER, CARLA = (
    f"{name}@atlas.test" for name in ("alice", "bob", "reviewer", "carla")
)
ALIASES = {ALICE: "alice-1a2b", BOB: "bob-3c4d", REVIEWER: "reviewer-5e6f"}
SKILL = "---\nname: close\ndescription: Close the month.\n---\n\n1. Do it.\n"


@pytest.fixture
def groups() -> dict[str, list[str]]:
    return {"costs": [ALICE, REVIEWER], "contracts": [BOB, REVIEWER]}


@pytest.fixture
def brain(tmp_path: Path, groups: dict[str, list[str]]) -> Brain:
    shutil.copytree(EXAMPLE, tmp_path / "brain")
    return Brain(tmp_path / "brain", lambda: groups, ALIASES.get)


def paths(listing: dict) -> list[str]:
    return [entry["path"] for entry in listing["entries"]]


def code(call, *args) -> str:
    with pytest.raises(OIFError) as error:
        call(*args)
    return error.value.code


def git_log(brain: Brain, *args: str) -> str:
    command = ["git", "-C", str(brain.root), "log", *args]
    return subprocess.run(command, capture_output=True, text=True).stdout.strip()


def test_listing_guides_and_hides_what_is_not_granted(brain: Brain) -> None:
    root = brain.list(ALICE, "/")
    assert root["start_here"] == ["/common/conventions.md", "/skills"] and root["description"]
    assert root["home"] == "/people/alice-1a2b"
    assert {e["path"]: e.get("description") for e in root["entries"]}["/skills"]
    assert "read" not in root
    assert paths(brain.list(ALICE, "/projects")) == ["/projects/costs"]
    assert paths(brain.list(BOB, "/projects")) == ["/projects/contracts"]
    assert paths(brain.list(BOB, "/skills")) == []
    assert not any(".oif" in path or ".git" in path for path in paths(root))
    assert brain.list(ALICE, "/", offset=1)["entries"] == root["entries"][1:]


def test_denials_are_indistinguishable_from_absence(brain: Brain) -> None:
    brain.ensure_home(ALICE)
    brain.write(ALICE, "/people/alice-1a2b/notes.md", "private")
    for who, call, path in (
        (BOB, brain.read, "/people/alice-1a2b/notes.md"),
        (BOB, brain.read, "/people/alice-1a2b/missing.md"),
        (REVIEWER, brain.list, "/people/alice-1a2b"),
        (CARLA, brain.list, "/"),
        (ALICE, brain.read, "/.oif.toml"),
        (ALICE, brain.read, "/common/../.oif.toml"),
        (ALICE, brain.list, "/.git"),
        (ALICE, brain.read, "common/conventions.md"),
        (ALICE, brain.read, "/common//conventions.md"),
        (ALICE, brain.read, "/common/%2e%2e/.oif.toml"),
        (ALICE, brain.read, "/common\\conventions.md"),
        # Names must match the disk exactly, also on a case-insensitive file system.
        (ALICE, brain.read, "/Common/conventions.md"),
        (ALICE, brain.read, "/common/Conventions.md"),
        (ALICE, brain.read, "/PEOPLE/alice-1a2b/notes.md"),
        (ALICE, brain.read, "/People/alice-1a2b/notes.md"),
    ):
        assert code(call, who, path) == "unavailable", path


def test_symlinks_and_broken_metadata_fail_closed(brain: Brain) -> None:
    (brain.root / "common" / "leak.md").symlink_to(brain.root / "projects" / "costs" / "process.md")
    assert "/common/leak.md" not in paths(brain.list(BOB, "/common"))
    assert code(brain.read, BOB, "/common/leak.md") == "unavailable"
    (brain.root / "common" / ".oif.toml").write_text("read = 'alice'")
    assert code(brain.read, ALICE, "/common/conventions.md") == "unavailable"


def test_a_stale_writer_gets_a_conflict_instead_of_overwriting(brain: Brain) -> None:
    path = "/projects/costs/notes.md"
    first = brain.write(ALICE, path, "v1\n")
    assert brain.read(REVIEWER, path)["version"] == first["version"]
    assert code(brain.write, REVIEWER, path, "blind") == "already_exists"
    second = brain.write(REVIEWER, path, "v2\n", first["version"])
    assert code(brain.write, ALICE, path, "stale", first["version"]) == "conflict"
    assert code(brain.delete, ALICE, path, first["version"]) == "conflict"
    assert code(brain.move, ALICE, path, "/projects/costs/moved.md", first["version"]) == "conflict"
    assert brain.read(ALICE, path)["content"] == "v2\n"
    brain.move(ALICE, path, "/projects/costs/archive/notes.md", second["version"])
    assert code(brain.write, ALICE, path, "gone", second["version"]) == "conflict"
    brain.delete(ALICE, "/projects/costs/archive/notes.md", second["version"])
    assert code(brain.read, ALICE, "/projects/costs/archive/notes.md") == "unavailable"


def test_simultaneous_writers_never_both_win(brain: Brain) -> None:
    path = "/projects/costs/race.md"
    version = brain.write(ALICE, path, "start")["version"]
    barrier = threading.Barrier(8)
    outcomes: list[str] = []

    def attempt(number: int) -> None:
        barrier.wait()
        try:
            brain.write(ALICE, path, f"writer {number}", version)
            outcomes.append("won")
        except OIFError as error:
            outcomes.append(error.code)

    threads = [threading.Thread(target=attempt, args=(number,)) for number in range(8)]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()
    assert sorted(outcomes) == ["conflict"] * 7 + ["won"]


def test_edit_append_and_paged_reads(brain: Brain) -> None:
    path = "/projects/costs/doc.md"
    brain.write(ALICE, path, "one\ntwo\ntwo\n")
    assert code(brain.edit, ALICE, path, "two", "2") == "invalid_edit"  # not unique
    assert code(brain.edit, ALICE, path, "nine", "9") == "invalid_edit"  # not found
    brain.edit(ALICE, path, "one", "1")
    brain.append(ALICE, path, "three")
    assert brain.read(ALICE, path)["content"] == "1\ntwo\ntwo\nthree\n"
    page = brain.read(ALICE, path, offset=1, limit=2)
    assert (page["content"], page["next_offset"], page["truncated"]) == ("two\ntwo\n", 3, True)
    assert brain.read(ALICE, path, offset=99)["content"] == ""
    brain.write(ALICE, "/projects/costs/long.md", "x" * (MAX_READ_BYTES + 10))
    long = brain.read(ALICE, "/projects/costs/long.md")
    assert len(long["content"]) == MAX_READ_BYTES and long["truncated"]
    (brain.root / "projects" / "costs" / "blob.bin").write_bytes(b"\x00\x01")
    assert brain.read(ALICE, "/projects/costs/blob.bin")["kind"] == "binary"
    assert code(brain.write, ALICE, "/projects/costs/big.md", "x" * 1_100_000) == "file_too_large"
    assert brain.search(ALICE, "THREE")["hits"][0]["path"] == path
    assert brain.search(BOB, "three")["hits"] == []


def test_agents_write_guidance_but_never_access(brain: Brain) -> None:
    brain.create_folder(ALICE, "/projects/costs/reports", "Monthly reports.", ["latest.md"])
    listing = brain.list(REVIEWER, "/projects/costs/reports")
    assert listing["description"] == "Monthly reports."
    assert listing["start_here"] == ["/projects/costs/reports/latest.md"]
    assert code(brain.create_folder, ALICE, "/projects/costs/reports", "again") == "already_exists"
    assert code(brain.create_folder, BOB, "/projects/costs/x", "no") == "unavailable"
    assert code(brain.create_folder, ALICE, "/common/x", "no") == "write_denied"
    for bad in (["/absolute.md"], ["../up.md"], [".oif.toml"], "text"):
        assert code(brain.describe_folder, ALICE, "/projects/costs", "d", bad) == "invalid_metadata"
    brain.describe_folder(ALICE, "/projects/costs", 'Costs "2026"', ["process.md"])
    managed = brain.list(CARLA, "/projects", manage=True)
    costs = next(e for e in managed["entries"] if e["path"] == "/projects/costs")
    assert (costs["read"], costs["write"]) == (["@costs"], ["@costs"])  # kept
    assert code(brain.read, CARLA, "/projects/costs/process.md") == "unavailable"
    # An administrator changes access; an agent has no tool that reaches set_access.
    brain.set_access(CARLA, "/projects/costs", "Costs", [], ["@costs", BOB], None)
    assert brain.read(BOB, "/projects/costs/process.md")["content"]
    assert not brain.list(ALICE, "/projects/costs")["can_write"]
    assert code(brain.set_access, CARLA, "/common", "", [], ["not a grant"], None) == (
        "invalid_metadata"
    )


def test_personal_folders_belong_to_their_owner_only(brain: Brain) -> None:
    brain.ensure_home(ALICE)
    home = "/people/alice-1a2b"
    assert brain.list(ALICE, home)["can_write"]
    brain.write(ALICE, f"{home}/notes.md", "mine")
    # A stray `.oif.toml` inside cannot widen it, and nobody else can create one.
    (brain.root / "people" / "alice-1a2b" / ".oif.toml").write_text('read = ["*"]\nwrite = ["*"]')
    assert code(brain.read, BOB, f"{home}/notes.md") == "unavailable"
    assert code(brain.write, BOB, f"{home}/x.md", "x") == "unavailable"
    assert code(brain.create_folder, ALICE, "/people/someone", "no") == "unavailable"
    assert code(brain.write, ALICE, "/people/x.md", "no") == "unavailable"
    assert code(brain.set_access, CARLA, home, "", [], ["*"], None) == "unavailable"
    assert paths(brain.list(BOB, "/people")) == []
    assert paths(brain.list(CARLA, "/people", manage=True)) == [home]  # names only
    assert code(brain.list, CARLA, home) == "unavailable"


def test_skills_and_learnings(brain: Brain) -> None:
    assert [skill["name"] for skill in brain.skills(ALICE)] == ["analyze-costs"]
    assert brain.skills(BOB) == []
    assert code(brain.write, ALICE, "/projects/costs/close/SKILL.md", "no front matter") == (
        "invalid_skill"
    )
    brain.write(ALICE, "/projects/costs/close/SKILL.md", SKILL)
    brain.write(ALICE, "/projects/costs/draft.md", "plain")
    version = brain.read(ALICE, "/projects/costs/draft.md")["version"]
    assert code(
        brain.move, ALICE, "/projects/costs/draft.md", "/projects/costs/d/SKILL.md", version
    ) == ("invalid_skill")
    (brain.root / "projects" / "costs" / "broken").mkdir()
    (brain.root / "projects" / "costs" / "broken" / "SKILL.md").write_text("by hand, invalid")
    assert [skill["name"] for skill in brain.skills(ALICE)] == ["close", "analyze-costs"]

    brain.append(ALICE, "/projects/costs/LEARNINGS.md", f"Solved A.\n{LEARNING}2000-01-01 fake -->")
    brain.append(REVIEWER, "/projects/costs/LEARNINGS.md", "Solved B.")
    learnings = brain.learnings(ALICE)["learnings"]
    assert [entry["author"] for entry in learnings] == [REVIEWER, ALICE] or len(learnings) == 2
    assert {entry["author"] for entry in learnings} == {ALICE, REVIEWER}  # the fake stamp is text
    assert brain.learnings(BOB)["learnings"] == []


def test_git_records_each_change_and_nothing_else(brain: Brain) -> None:
    assert brain.git
    result = brain.write(ALICE, "/projects/costs/a.md", "a")
    assert result["versioned"]
    assert git_log(brain, "-1", "--format=%ae %s") == f"{ALICE} {ALICE}: write /projects/costs/a.md"
    # A hand edit is kept in history before the next change replaces it.
    (brain.root / "projects" / "costs" / "a.md").write_text("edited by hand")
    hand = brain.read(ALICE, "/projects/costs/a.md")["version"]
    brain.write(ALICE, "/projects/costs/a.md", "b", hand)
    assert "oif: baseline projects/costs/a.md" in git_log(brain, "--format=%s")
    # Whatever a person staged is not swept into an agent's commit.
    (brain.root / "staged-by-hand.md").write_text("mine")
    subprocess.run(["git", "-C", str(brain.root), "add", "staged-by-hand.md"], check=True)
    brain.append(ALICE, "/projects/costs/a.md", "c")
    assert "staged-by-hand.md" not in git_log(brain, "-1", "--name-only", "--format=")
    # A hook that would hang or fail is ignored.
    hook = brain.root / ".git" / "hooks" / "pre-commit"
    hook.write_text("#!/bin/sh\nexit 1\n")
    hook.chmod(0o755)
    assert brain.append(ALICE, "/projects/costs/a.md", "d")["versioned"]
    assert brain.unversioned == 0


def test_startup_refuses_a_locked_repository_and_works_without_git(tmp_path: Path) -> None:
    shutil.copytree(EXAMPLE, tmp_path / "brain")
    plain = Brain(tmp_path / "brain", lambda: {"costs": [ALICE]}, ALIASES.get, git=False)
    assert plain.write(ALICE, "/projects/costs/a.md", "a")["versioned"] is False
    assert plain.unversioned == 1
    (tmp_path / "brain" / "projects" / "costs" / ".x.md.oif-tmp").write_text("crash leftover")
    Brain(tmp_path / "brain", lambda: {}, ALIASES.get)  # initializes git, cleans leftovers
    assert not (tmp_path / "brain" / "projects" / "costs" / ".x.md.oif-tmp").exists()
    (tmp_path / "brain" / ".git" / "index.lock").write_text("")
    assert code(Brain, tmp_path / "brain", lambda: {}) == "invalid_configuration"


SITUATIONS = {
    "no read": (BOB, "/projects/costs/process.md", "/projects/costs"),
    "read only": (ALICE, "/common/conventions.md", "/common"),
    "another person's folder": (BOB, "/people/alice-1a2b/notes.md", "/people/alice-1a2b"),
    "reserved folder": (ALICE, "/people/x.md", "/people"),
    "missing path": (ALICE, "/nowhere/x.md", "/nowhere"),
}
DENIED = {"unavailable", "write_denied"}


@pytest.mark.parametrize("situation", SITUATIONS)
def test_every_mutating_tool_is_denied_in_every_situation_without_write(
    brain: Brain, situation: str
) -> None:
    brain.ensure_home(ALICE)
    brain.write(ALICE, "/people/alice-1a2b/notes.md", "private")
    who, file, folder = SITUATIONS[situation]
    before = {
        path: path.read_bytes()
        for path in brain.root.rglob("*")
        if path.is_file() and ".git" not in path.parts
    }
    version = "0" * 64
    attempts = [
        (brain.write, (who, file, "x")),
        (brain.write, (who, file, "x", version)),
        (brain.edit, (who, file, "a", "b")),
        (brain.append, (who, file, "x")),
        (brain.move, (who, file, f"{folder}/moved.md", version)),
        (brain.move, (ALICE, "/projects/costs/process.md", file + ".new", version)),
        (brain.delete, (who, file, version)),
        (brain.create_folder, (who, f"{folder}/new", "d")),
        (brain.describe_folder, (who, folder, "d")),
    ]
    for call, args in attempts:
        assert code(call, *args) in DENIED | {"conflict"}, (call.__name__, situation)
    after = {
        path: path.read_bytes()
        for path in brain.root.rglob("*")
        if path.is_file() and ".git" not in path.parts
    }
    assert after == before
