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
    assert brain.write(ALICE, "projects/costs/new.md", "x")["path"] == "/projects/costs/new.md"
    made = brain.create_folder(ALICE, "/projects/costs/reports/", "Reports")
    assert made["path"] == "/projects/costs/reports"
    for unsafe in ("/projects//costs", "projects/costs/../../.brainfold.toml", "/projects/costs//"):
        assert code(brain.list, ALICE, unsafe) == "unavailable", unsafe
