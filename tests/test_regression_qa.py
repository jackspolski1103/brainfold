"""Regressions found by /qa on 2026-11-12.

Report: .gstack/qa-reports/run-20261112T190916Z/qa-report-brainfold-2026-11-12.md
"""

from __future__ import annotations

import shutil
from pathlib import Path

import pytest

from brainfold import BrainfoldError
from brainfold.brain import Brain

EXAMPLE = Path(__file__).parent.parent / "examples" / "brain"
ALICE, DANA, ADMIN = "alice@atlas.test", "dana@atlas.test", "lead@atlas.test"
ALIASES = {ALICE: "alice-1a2b", DANA: "dana-9z8y"}


@pytest.fixture
def brain(tmp_path: Path) -> Brain:
    shutil.copytree(EXAMPLE, tmp_path / "brain")
    return Brain(tmp_path / "brain", lambda: {"costs": [ALICE]}, ALIASES.get)


def code(call, *args, **kwargs) -> str:
    with pytest.raises(BrainfoldError) as error:
        call(*args, **kwargs)
    return error.value.code


# Regression: ISSUE-002 — a member in no group could not list the root, so their agent
# never learned where its personal folder was.
def test_a_member_without_any_group_still_finds_their_personal_folder(brain: Brain) -> None:
    brain.ensure_home(DANA)
    root = brain.list(DANA, "/")
    assert root["home"] == "/people/dana-9z8y"
    assert [entry["path"] for entry in root["entries"]] == ["/people/dana-9z8y"]
    assert root["description"] == "" and not root["can_write"]  # nothing else about the root
    brain.write(DANA, "/people/dana-9z8y/notes.md", "mine")
    assert brain.search(DANA, "mine")["hits"][0]["path"] == "/people/dana-9z8y/notes.md"
    assert code(brain.list, DANA, "/projects") == "unavailable"
    assert code(brain.read, DANA, "/common/conventions.md") == "unavailable"


# Regression: ISSUE-003 — an administrator could open a personal folder's listing.
def test_an_administrator_cannot_open_a_personal_folder_even_in_manage_mode(brain: Brain) -> None:
    brain.ensure_home(ALICE)
    brain.write(ALICE, "/people/alice-1a2b/notes.md", "private")
    names = [entry["path"] for entry in brain.list(ADMIN, "/people", manage=True)["entries"]]
    assert names == ["/people/alice-1a2b"]  # the administrator still sees that it exists
    assert code(brain.list, ADMIN, "/people/alice-1a2b", manage=True) == "unavailable"


# Regression: ISSUE-001 — agents send folder paths with a trailing slash or without the
# leading one; both were answered "not available".
def test_common_path_forms_are_accepted_and_answers_use_the_canonical_path(brain: Brain) -> None:
    assert brain.list(ALICE, "/projects/costs/")["path"] == "/projects/costs"
    assert brain.list(ALICE, "projects/costs")["path"] == "/projects/costs"
    assert brain.read(ALICE, "projects/costs/process.md")["path"] == "/projects/costs/process.md"
    sizes = {e["path"]: e.get("size") for e in brain.list(ALICE, "/projects/costs")["entries"]}
    assert sizes["/projects/costs/process.md"] == 157  # files carry their size in a listing
    assert brain.write(ALICE, "projects/costs/new.md", "x")["path"] == "/projects/costs/new.md"
    made = brain.create_folder(ALICE, "/projects/costs/reports/", "Reports")
    assert made["path"] == "/projects/costs/reports"
    for unsafe in ("/projects//costs", "projects/costs/../../.brainfold.toml", "/projects/costs//"):
        assert code(brain.list, ALICE, unsafe) == "unavailable", unsafe


# Regression: ISSUE-004 — storing a file again with identical content was reported as
# "not in history" and raised the unversioned counter.
def test_storing_identical_content_again_is_not_reported_as_unversioned(brain: Brain) -> None:
    first = brain.write(ALICE, "/projects/costs/same.md", "same")
    again = brain.write(ALICE, "/projects/costs/same.md", "same", first["version"])
    assert again["versioned"] and brain.unversioned == 0


# Regression: ISSUE-008 — reading a folder gave the same answer as a missing path.
def test_reading_a_folder_points_the_agent_to_list(brain: Brain) -> None:
    with pytest.raises(BrainfoldError) as error:
        brain.read(ALICE, "/projects/costs")
    assert error.value.code == "unavailable" and "list" in error.value.message
    with pytest.raises(BrainfoldError) as hidden:
        brain.read(DANA, "/projects/costs")  # not readable: nothing extra is revealed
    assert "list" not in hidden.value.message


# Regression: ISSUE-009 — with the port taken, `serve` announced itself before failing.
def test_serve_reports_a_busy_port_without_announcing_the_server(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    import socket

    from brainfold import cli

    shutil.copytree(EXAMPLE, tmp_path / "brain")
    with socket.socket() as taken:
        taken.bind(("127.0.0.1", 0))
        taken.listen()
        port = str(taken.getsockname()[1])
        arguments = ["serve", "--root", str(tmp_path / "brain"), "--db", str(tmp_path / "a.db")]
        assert cli.main([*arguments, "--port", port]) == 1
    output = capsys.readouterr()
    assert "MCP at" not in output.out and "in use" in output.err


def test_serve_takes_its_settings_from_the_environment_and_creates_its_folders(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    import socket

    from brainfold import cli

    with socket.socket() as taken:  # a busy port makes `serve` return after setting up
        taken.bind(("127.0.0.1", 0))
        taken.listen()
        monkeypatch.setenv("BRAINFOLD_ROOT", str(tmp_path / "volume" / "brain"))
        monkeypatch.setenv("BRAINFOLD_DB", str(tmp_path / "volume" / "accounts" / "b.db"))
        monkeypatch.setenv("PORT", str(taken.getsockname()[1]))
        monkeypatch.setenv("BRAINFOLD_PUBLIC_URL", "https://brain.example.test")
        assert cli.main(["serve"]) == 1
    assert (tmp_path / "volume" / "brain" / ".git").is_dir()
    assert (tmp_path / "volume" / "accounts" / "b.db").is_file()
    assert "in use" in capsys.readouterr().err
    monkeypatch.setenv("BRAINFOLD_PUBLIC_URL", "http://brain.example.test")
    assert cli.main(["serve"]) == 1  # a public address must be https
