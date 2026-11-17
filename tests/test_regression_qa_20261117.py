"""Regressions found by /qa on 2026-11-17.

Report: .gstack/qa-reports/run-20261117T131822Z/qa-report-brainfold-2026-11-17.md
"""

from __future__ import annotations

import asyncio
import shutil
from pathlib import Path
from typing import Any

import pytest
from starlette.testclient import TestClient
from team import serving

from brainfold import BrainfoldError
from brainfold.brain import Brain
from brainfold.server import create_app

EXAMPLE = Path(__file__).parent.parent / "examples" / "brain"
ALICE, PASSWORD = "alice@atlas.test", "a-long-password"
JSON = {"Accept": "application/json, text/event-stream"}


@pytest.fixture
def brain(tmp_path: Path) -> Brain:
    shutil.copytree(EXAMPLE, tmp_path / "brain")
    return Brain(tmp_path / "brain", lambda: {"costs": [ALICE]}, {ALICE: "alice-1a2b"}.get)


def code(call, *args, **kwargs) -> str:
    with pytest.raises(BrainfoldError) as error:
        call(*args, **kwargs)
    return error.value.code


# Regression: ISSUE-001 — every MCP request walked the caller's whole readable tree on the
# event loop to build the session instructions, and every write walked it again. On a
# 3,000-file brain a ping took 1.1 s and /api/health stalled for seconds under 8 agents.
# Found by /qa on 2026-11-17
# Report: .gstack/qa-reports/run-20261117T131822Z/qa-report-brainfold-2026-11-17.md
def test_only_a_session_start_walks_the_brain_and_never_on_the_event_loop(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    walks: list[bool] = []
    original = Brain.skills

    def counted(self: Brain, who: str) -> Any:
        try:
            asyncio.get_running_loop()
            walks.append(True)  # on the event loop: everyone else waits
        except RuntimeError:
            walks.append(False)
        return original(self, who)

    monkeypatch.setattr(Brain, "skills", counted)
    shutil.copytree(EXAMPLE, tmp_path / "brain")
    with serving(tmp_path / "brain", tmp_path / "brainfold.db") as team:
        ana = team.join("ana@atlas.test")
        team.group("costs", ana)

        def rpc(method: str, params: dict[str, Any]) -> dict[str, Any]:
            body = {"jsonrpc": "2.0", "id": 1, "method": method, "params": params}
            return ana.agent.post("/mcp", json=body, headers=JSON).json()

        # The first tool call of a process lists the tools once to validate arguments.
        assert ana.tool("list", path="/")[0] == "ok"
        walks.clear()
        rpc("ping", {})
        assert ana.tool("list", path="/")[0] == "ok"
        assert ana.tool("read", path="/projects/costs/process.md")[0] == "ok"
        assert ana.tool("write", path="/projects/costs/note.md", content="x")[0] == "ok"
        assert ana.tool("append", path="/projects/costs/note.md", content="y")[0] == "ok"
        assert walks == []
        hello = {"protocolVersion": "2025-03-26", "capabilities": {}}
        started = rpc("initialize", hello | {"clientInfo": {"name": "qa", "version": "0"}})
        assert "analyze-costs-" in started["result"]["instructions"]
        skill = "---\nname: close\ndescription: Close the month\n---\n1. Do it.\n"
        answer = ana.tool("write", path="/projects/costs/close/SKILL.md", content=skill)
        assert answer[1]["skill"].startswith("close-")
        assert walks and not any(walks)


# Regression: ISSUE-002 — a file name of 241 to 255 bytes failed with storage_error because
# its temporary name did not fit, and any storage error then deleted the temporary file of
# every upload in flight, so other people's uploads failed too.
# Found by /qa on 2026-11-17
# Report: .gstack/qa-reports/run-20261117T131822Z/qa-report-brainfold-2026-11-17.md
def test_a_storage_error_of_one_caller_never_removes_another_upload_in_flight(
    brain: Brain, monkeypatch: pytest.MonkeyPatch
) -> None:
    assert brain.write(ALICE, "/projects/costs/" + "n" * 240, "x")["versioned"]
    for length in (241, 255):
        assert code(brain.write, ALICE, "/projects/costs/" + "n" * length, "x") == "unavailable"
    upload = brain.root / ".upload-0123456789abcdef.brainfold-tmp"  # someone else's, in flight
    upload.write_bytes(b"half of a file")

    def full_disk(target: Path, data: bytes) -> None:
        raise OSError("no space left on device")

    monkeypatch.setattr(brain, "_store", full_disk)
    assert code(brain.write, ALICE, "/projects/costs/other.md", "x") == "storage_error"
    assert upload.read_bytes() == b"half of a file"
    monkeypatch.undo()
    Brain(brain.root, brain.groups)  # a restart still clears what a crash left behind
    assert not upload.exists()


# Regression: ISSUE-003 — the JSON API read a request body of any size into memory before
# looking at it: an anonymous 200 MB POST to /api/login grew the server from 42 to 556 MB.
# Found by /qa on 2026-11-17
# Report: .gstack/qa-reports/run-20261117T131822Z/qa-report-brainfold-2026-11-17.md
def test_the_json_api_refuses_a_body_larger_than_it_could_ever_need(tmp_path: Path) -> None:
    (tmp_path / "brain").mkdir()
    client = TestClient(create_app(tmp_path / "brain", tmp_path / "brainfold.db", git=False))
    huge = b'{"email":"a@b.cd","password":"' + b"x" * 2_000_000 + b'"}'
    headers = {"Content-Type": "application/json"}
    refused = client.post("/api/login", content=huge, headers=headers)
    assert refused.status_code == 413 and refused.json()["error"]["code"] == "file_too_large"
    setup = client.post("/api/setup", json={"email": ALICE, "password": PASSWORD})
    assert setup.status_code == 200  # ordinary requests are untouched


# Regression: ISSUE-004 — a line longer than one read (64 KB) was cut, and continuing from
# `next_offset` skipped the rest of it without a word: the agent believed it had read it.
# Found by /qa on 2026-11-17
# Report: .gstack/qa-reports/run-20261117T131822Z/qa-report-brainfold-2026-11-17.md
def test_a_line_too_long_for_one_read_says_it_was_cut_and_how_to_get_it_whole(
    brain: Brain,
) -> None:
    path = "/projects/costs/wide.md"
    brain.write(ALICE, path, "first\n" + "x" * 100_000 + "\nlast\n")
    first = brain.read(ALICE, path)
    assert first["content"] == "first\n" and first["truncated"] and "note" not in first
    cut = brain.read(ALICE, path, first["next_offset"])
    assert len(cut["content"]) == 65_536 and cut["truncated"]
    assert "Line 2" in cut["note"] and cut["fetch"].startswith("brainfold get ")
    last = brain.read(ALICE, path, cut["next_offset"])
    assert last["content"] == "last\n" and not last["truncated"] and "note" not in last


# Regression: ISSUE-005 — a description that is not valid text (a lone surrogate, which JSON
# can carry) escaped as a raw Python error, and create_folder left the folder behind
# without its metadata.
# Found by /qa on 2026-11-17
# Report: .gstack/qa-reports/run-20261117T131822Z/qa-report-brainfold-2026-11-17.md
def test_a_description_that_is_not_valid_text_is_refused_and_leaves_nothing(brain: Brain) -> None:
    assert code(brain.create_folder, ALICE, "/projects/costs/new", "\ud800") == "invalid_metadata"
    assert not (brain.root / "projects" / "costs" / "new").exists()
    assert code(brain.describe_folder, ALICE, "/projects/costs", "\ud800") == "invalid_metadata"
    assert code(brain.describe_file, ALICE, "/projects/costs/process.md", "\ud800") == (
        "invalid_metadata"
    )
    assert brain.list(ALICE, "/projects/costs")["description"].startswith("Process")


# Regression: ISSUE-006 — folder grants reached an account whatever its capitals, but a
# group member, a removal or a reset typed with capitals answered "no account".
# Found by /qa on 2026-11-17
# Report: .gstack/qa-reports/run-20261117T131822Z/qa-report-brainfold-2026-11-17.md
def test_administration_reaches_an_account_whatever_the_capitals(tmp_path: Path) -> None:
    (tmp_path / "brain").mkdir()
    app = create_app(tmp_path / "brain", tmp_path / "brainfold.db", git=False)
    admin = TestClient(app)
    admin.post("/api/setup", json={"email": ALICE, "password": PASSWORD})
    invite = admin.post("/api/users", json={"email": "bob@atlas.test"}).json()["invite"]
    TestClient(app).post("/api/accept", json={"invite": invite, "password": PASSWORD})
    grouped = admin.put("/api/groups/costs", json={"members": ["Bob@Atlas.test "]})
    assert grouped.status_code == 200 and grouped.json()["groups"] == {"costs": ["bob@atlas.test"]}
    assert admin.post("/api/users/BOB@atlas.test/reset", json={}).status_code == 200
    assert admin.delete("/api/users/Bob@Atlas.Test").status_code == 200
    assert [user["email"] for user in admin.get("/api/users").json()["users"]] == [ALICE]
