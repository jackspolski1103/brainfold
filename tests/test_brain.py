from __future__ import annotations

import shutil
import subprocess
import threading
import time
from pathlib import Path

import pytest

from brainfold import BrainfoldError
from brainfold.brain import LEARNING, MAX_READ_BYTES, Brain

EXAMPLE = Path(__file__).parent.parent / "examples" / "brain"
ALICE, BOB, REVIEWER, CARLA = (
    f"{name}@atlas.test" for name in ("alice", "bob", "reviewer", "carla")
)
ALIASES = {ALICE: "alice-1a2b", BOB: "bob-3c4d", REVIEWER: "reviewer-5e6f"}
SKILL = "---\nname: close\ndescription: Close the month.\n---\n\n1. Do it.\n"


@pytest.fixture
def groups() -> dict[str, list[str]]:
    return {"costs": [ALICE, REVIEWER], "contracts": [BOB, REVIEWER]}


class Journal:
    """In-memory stand-in for the revision records kept by the accounts database."""

    def __init__(self) -> None:
        self.rows: list[dict] = []
        self.joined: dict[str, float] = {}

    def add_revision(self, path, commit, author, kind, readers, version) -> None:
        row = {"id": len(self.rows) + 1, "path": path, "commit": commit, "author": author}
        self.rows.append(
            row | {"at": time.time(), "kind": kind, "readers": readers, "version": version}
        )

    def revisions(self, path: str) -> list[dict]:
        return [row for row in self.rows if row["path"] == path]

    def created(self, email: str) -> float:
        return self.joined.get(email, 0.0)


@pytest.fixture
def journal() -> Journal:
    return Journal()


@pytest.fixture
def brain(tmp_path: Path, groups: dict[str, list[str]], journal: Journal) -> Brain:
    shutil.copytree(EXAMPLE, tmp_path / "brain")
    return Brain(tmp_path / "brain", lambda: groups, ALIASES.get, journal=journal)


def changes(brain: Brain, who: str, path: str) -> list[str]:
    return [row["change"] for row in brain.history(who, path)["revisions"]]


def paths(listing: dict) -> list[str]:
    return [entry["path"] for entry in listing["entries"]]


def entry(brain: Brain, who: str, path: str) -> dict:
    listing = brain.list(who, path.rsplit("/", 1)[0])
    return next(item for item in listing["entries"] if item["path"] == path)


def code(call, *args) -> str:
    with pytest.raises(BrainfoldError) as error:
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
    assert not any(".brainfold" in path or ".git" in path for path in paths(root))
    assert brain.list(ALICE, "/", offset=1)["entries"] == root["entries"][1:]


def test_denials_are_indistinguishable_from_absence(brain: Brain) -> None:
    brain.ensure_home(ALICE)
    brain.write(ALICE, "/people/alice-1a2b/notes.md", "private")
    for who, call, path in (
        (BOB, brain.read, "/people/alice-1a2b/notes.md"),
        (BOB, brain.read, "/people/alice-1a2b/missing.md"),
        (REVIEWER, brain.list, "/people/alice-1a2b"),
        (CARLA, brain.list, "/"),
        (ALICE, brain.read, "/.brainfold.toml"),
        (ALICE, brain.read, "/common/../.brainfold.toml"),
        (ALICE, brain.list, "/.git"),
        (ALICE, brain.read, "/common//conventions.md"),
        (ALICE, brain.read, "/common/%2e%2e/.brainfold.toml"),
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
    (brain.root / "common" / ".brainfold.toml").write_text("read = 'alice'")
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
        except BrainfoldError as error:
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
    for bad in (["/absolute.md"], ["../up.md"], [".brainfold.toml"], "text"):
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
    # A stray `.brainfold.toml` inside cannot widen it, and nobody else can create one.
    (brain.root / "people" / "alice-1a2b" / ".brainfold.toml").write_text(
        'read = ["*"]\nwrite = ["*"]'
    )
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
    assert "brainfold: baseline projects/costs/a.md" in git_log(brain, "--format=%s")
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
    (tmp_path / "brain" / "projects" / "costs" / ".x.md.brainfold-tmp").write_text("crash leftover")
    Brain(tmp_path / "brain", lambda: {}, ALIASES.get)  # initializes git, cleans leftovers
    assert not (tmp_path / "brain" / "projects" / "costs" / ".x.md.brainfold-tmp").exists()
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
        (brain.move, (who, folder, f"{folder}-moved")),
        (brain.delete, (who, folder)),
        (brain.restore, (who, file, 1)),
        (brain.put_file, (who, file, brain.root / "missing-upload", None)),
    ]
    for call, args in attempts:
        assert code(call, *args) in DENIED | {"conflict"}, (call.__name__, situation)
    after = {
        path: path.read_bytes()
        for path in brain.root.rglob("*")
        if path.is_file() and ".git" not in path.parts
    }
    assert after == before


def test_history_and_restore_undo_changes_and_deletions(brain: Brain) -> None:
    path = "/projects/costs/plan.md"
    first = brain.write(ALICE, path, "v1")
    second = brain.write(REVIEWER, path, "v2", first["version"])
    brain.delete(ALICE, path, second["version"])
    assert changes(brain, ALICE, path) == ["write", "write", "delete"]
    revisions = brain.history(REVIEWER, path)["revisions"]
    assert [row["author"] for row in revisions] == [ALICE, REVIEWER, ALICE]
    assert set(revisions[0]) == {"revision", "author", "date", "change"}  # no content, no paths
    assert code(brain.restore, ALICE, path, revisions[2]["revision"]) == "no_history"  # a delete
    restored = brain.restore(ALICE, path, revisions[0]["revision"])
    assert brain.read(ALICE, path)["content"] == "v1" and restored["versioned"]
    assert code(brain.restore, ALICE, path, revisions[1]["revision"]) == "already_exists"
    brain.restore(ALICE, path, revisions[1]["revision"], restored["version"])
    assert brain.read(ALICE, path)["content"] == "v2"
    assert code(brain.history, BOB, path) == "no_history"
    assert code(brain.history, ALICE, "/projects/costs/never.md") == "no_history"
    other = brain.write(ALICE, "/projects/costs/other.md", "x")
    assert other and code(
        brain.restore, ALICE, "/projects/costs/other.md", revisions[0]["revision"]
    ) == ("no_history")
    # A file that predates the records gets a baseline, so its first change is undoable.
    original = brain.read(ALICE, "/projects/costs/process.md")["content"]
    brain.edit(ALICE, "/projects/costs/process.md", "To analyze costs", "CHANGED")
    process = brain.history(ALICE, "/projects/costs/process.md")["revisions"]
    assert [row["change"] for row in process] == ["baseline", "edit"]
    current = brain.read(ALICE, "/projects/costs/process.md")["version"]
    brain.restore(ALICE, "/projects/costs/process.md", process[0]["revision"], current)
    assert brain.read(ALICE, "/projects/costs/process.md")["content"] == original


def test_history_never_reveals_what_the_caller_could_not_read_then(
    brain: Brain, journal: Journal
) -> None:
    secret = "/projects/costs/secret"
    brain.create_folder(REVIEWER, secret, "Restricted")
    brain.set_access(CARLA, secret, "Restricted", [], [REVIEWER], [REVIEWER])
    brain.write(REVIEWER, f"{secret}/plan.md", "for the reviewer only")
    old = journal.rows[-1]["id"]
    shutil.rmtree(brain.root / "projects" / "costs" / "secret")  # an administrator, by hand
    # The path is reused by someone who could never read the old content.
    brain.create_folder(ALICE, secret, "Reused")
    assert code(brain.history, ALICE, f"{secret}/plan.md") == "no_history"
    assert code(brain.restore, ALICE, f"{secret}/plan.md", old) == "no_history"
    brain.write(ALICE, f"{secret}/plan.md", "new")
    assert changes(brain, ALICE, f"{secret}/plan.md") == ["write"]
    assert changes(brain, REVIEWER, f"{secret}/plan.md") == ["write", "write"]
    # Widening read later does not open earlier revisions either.
    brain.write(BOB, "/projects/contracts/deal.md", "contracts only")
    brain.set_access(
        CARLA, "/projects/contracts", "", [], ["@contracts", ALICE], ["@contracts", ALICE]
    )
    assert brain.read(ALICE, "/projects/contracts/deal.md")["content"]
    assert code(brain.history, ALICE, "/projects/contracts/deal.md") == "no_history"
    # A grant by email does not reach back before that account existed.
    brain.write(ALICE, "/projects/contracts/mine.md", "after the grant")
    assert changes(brain, ALICE, "/projects/contracts/mine.md") == ["write"]
    journal.joined[ALICE] = time.time() + 60  # the email now belongs to a newer account
    assert code(brain.history, ALICE, "/projects/contracts/mine.md") == "no_history"


def test_folders_move_whole_or_not_at_all_and_only_empty_ones_are_deleted(brain: Brain) -> None:
    brain.create_folder(ALICE, "/projects/costs/q3", "Third quarter", ["a.md"])
    brain.write(ALICE, "/projects/costs/q3/a.md", "a")
    brain.write(ALICE, "/projects/costs/q3/deep/b.md", "b")
    assert code(brain.delete, ALICE, "/projects/costs/q3") == "folder_not_empty"
    assert code(brain.move, ALICE, "/projects/costs/q3", "/projects/costs/q3/inside") == (
        "folder_not_movable"
    )
    assert code(brain.move, ALICE, "/projects/costs/q3", "/projects/costs/q3") == "already_exists"
    # Hidden content, or access declared by an administrator, keeps a folder where it is.
    hidden = brain.root / "projects" / "costs" / "q3" / "deep" / ".secret"
    hidden.write_text("x")
    assert (
        code(brain.move, ALICE, "/projects/costs/q3", "/projects/costs/q4") == "folder_not_movable"
    )
    hidden.unlink()
    brain.set_access(CARLA, "/projects/costs/q3/deep", "", [], [REVIEWER], None)
    assert code(brain.move, REVIEWER, "/projects/costs/q3", "/projects/costs/q4") == (
        "folder_not_movable"
    )
    assert (brain.root / "projects" / "costs" / "q3" / "a.md").exists()
    brain.set_access(CARLA, "/projects/costs/q3/deep", "", [], None, None)

    moved = brain.move(ALICE, "/projects/costs/q3", "/projects/costs/archive/q3")
    assert moved["versioned"]
    assert brain.list(ALICE, "/projects/costs/archive/q3")["start_here"] == [
        "/projects/costs/archive/q3/a.md"
    ]
    assert brain.read(ALICE, "/projects/costs/archive/q3/deep/b.md")["content"] == "b"
    assert changes(brain, ALICE, "/projects/costs/archive/q3/a.md") == ["move_in"]

    brain.ensure_home(ALICE)
    assert (
        code(brain.move, ALICE, "/people/alice-1a2b", "/projects/costs/me") == "folder_not_movable"
    )
    assert code(brain.delete, ALICE, "/people/alice-1a2b") == "folder_not_movable"
    brain.create_folder(ALICE, "/projects/costs/empty", "Created by mistake")
    assert brain.delete(ALICE, "/projects/costs/empty")["versioned"]
    assert "/projects/costs/empty" not in paths(brain.list(ALICE, "/projects/costs"))
    # Emptying a folder with declared access does not let an agent remove its restriction.
    brain.create_folder(ALICE, "/projects/costs/locked", "Locked")
    brain.set_access(CARLA, "/projects/costs/locked", "Locked", [], ["@costs"], ["@costs"])
    assert code(brain.delete, ALICE, "/projects/costs/locked") == "forbidden"


def test_files_of_any_type_are_stored_with_the_same_rules(brain: Brain, tmp_path: Path) -> None:
    def upload(who: str, path: str, data: bytes, version: str | None = None) -> dict:
        source = brain.root / ".upload-test.brainfold-tmp"
        source.write_bytes(data)
        return brain.put_file(who, path, source, version)

    sheet = bytes(range(256)) * 4
    stored = upload(ALICE, "/projects/costs/salaries.xlsx", sheet)
    assert brain.download(REVIEWER, "/projects/costs/salaries.xlsx") == (sheet, stored["version"])
    seen = brain.read(ALICE, "/projects/costs/salaries.xlsx")
    assert (
        seen["kind"] == "binary" and "brainfold get /projects/costs/salaries.xlsx" in seen["fetch"]
    )
    assert code(brain.download, BOB, "/projects/costs/salaries.xlsx") == "unavailable"
    assert code(upload, ALICE, "/projects/costs/salaries.xlsx", b"new") == "already_exists"
    assert code(upload, ALICE, "/projects/costs/salaries.xlsx", b"new", "0" * 64) == "conflict"
    upload(ALICE, "/projects/costs/salaries.xlsx", b"new", stored["version"])
    assert code(upload, BOB, "/projects/costs/x.bin", b"x") == "unavailable"
    assert code(upload, ALICE, "/projects/costs/k/SKILL.md", b"not a skill") == "invalid_skill"
    brain.max_file_bytes = 10
    assert code(upload, ALICE, "/projects/costs/big.bin", b"x" * 11) == "file_too_large"
    # An earlier binary version comes back with restore.
    first = brain.history(ALICE, "/projects/costs/salaries.xlsx")["revisions"][0]["revision"]
    current = brain.download(ALICE, "/projects/costs/salaries.xlsx")[1]
    brain.restore(ALICE, "/projects/costs/salaries.xlsx", first, current)
    assert brain.download(ALICE, "/projects/costs/salaries.xlsx")[0] == sheet


def test_files_carry_a_description_that_follows_them(brain: Brain) -> None:
    folder = "/projects/costs"
    stored = brain.write(ALICE, f"{folder}/q3.md", "numbers")
    assert "description" not in entry(brain, ALICE, f"{folder}/q3.md")
    brain.describe_file(ALICE, f"{folder}/q3.md", "Third quarter totals, final.")
    assert entry(brain, ALICE, f"{folder}/q3.md")["description"] == "Third quarter totals, final."
    # The folder keeps its guidance and its access rules.
    listing = brain.list(ALICE, folder)
    assert listing["description"] and listing["start_here"] == [f"{folder}/process.md"]
    assert code(brain.read, BOB, f"{folder}/q3.md") == "unavailable"
    # It follows a rename, and leaves with the file: a later file of that name starts clean.
    brain.move(ALICE, f"{folder}/q3.md", f"{folder}/third.md", stored["version"])
    assert entry(brain, ALICE, f"{folder}/third.md")["description"].startswith("Third quarter")
    brain.delete(ALICE, f"{folder}/third.md", stored["version"])
    brain.write(ALICE, f"{folder}/third.md", "other")
    assert "description" not in entry(brain, ALICE, f"{folder}/third.md")
    # Empty text removes it.
    brain.describe_file(ALICE, f"{folder}/process.md", "How the team works.")
    brain.describe_file(ALICE, f"{folder}/process.md", "")
    assert "description" not in entry(brain, ALICE, f"{folder}/process.md")
    # Denials: no write, a folder, several lines.
    assert code(brain.describe_file, BOB, f"{folder}/process.md", "x") == "unavailable"
    assert code(brain.describe_file, ALICE, folder, "x") == "unavailable"
    assert code(brain.describe_file, ALICE, f"{folder}/process.md", "a\nb") == "invalid_metadata"


def test_a_write_names_the_folders_it_created_without_a_description(brain: Brain) -> None:
    written = brain.write(ALICE, "/projects/costs/2026/q1/notes.md", "x")
    assert written["new_folders"] == ["/projects/costs/2026", "/projects/costs/2026/q1"]
    assert "describe_folder" in written["note"]
    again = brain.write(ALICE, "/projects/costs/2026/q1/more.md", "x")
    assert "new_folders" not in again and "note" not in again
