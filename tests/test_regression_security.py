"""Regressions for the findings of the security review of 2026-11-12."""

from __future__ import annotations

import shlex
import shutil
from pathlib import Path

from starlette.testclient import TestClient

from brainfold.accounts import Accounts
from brainfold.brain import Brain
from brainfold.server import COOKIE, create_app

EXAMPLE = Path(__file__).parent.parent / "examples" / "brain"
ADMIN, PASSWORD = "lead@atlas.test", "a-long-password"


# Finding 1: a harness token worked on the whole panel API, so an administrator's agent
# could be talked into changing access lists or inviting an administrator.
def test_harness_tokens_and_panel_sessions_are_not_interchangeable(tmp_path: Path) -> None:
    shutil.copytree(EXAMPLE, tmp_path / "brain")
    app = create_app(tmp_path / "brain", tmp_path / "a.db", git=False)
    panel = TestClient(app)
    assert panel.post("/api/setup", json={"email": ADMIN, "password": PASSWORD}).status_code == 200
    token = panel.post("/api/tokens", json={"name": "harness"}).json()["token"]
    session = panel.cookies[COOKIE]

    agent = TestClient(app, headers={"Authorization": f"Bearer {token}"})
    change = {"path": "/projects/costs", "read": ["*"], "write": ["*"]}
    assert agent.put("/api/folder", json=change).status_code == 401
    assert agent.post("/api/users", json={"email": "m@x.test", "role": "admin"}).status_code == 401
    assert agent.post("/api/tokens", json={"name": "second"}).status_code == 401
    assert agent.get("/api/activity").status_code == 401
    assert agent.put("/files/people/x.bin", content=b"x").status_code != 401  # still a file token

    # And a panel session is not a harness credential.
    accounts = Accounts(tmp_path / "a.db")
    assert accounts.authenticate(session, "session").email == ADMIN
    stolen = TestClient(app, headers={"Authorization": f"Bearer {session}"})
    assert stolen.get("/files/common/conventions.md").status_code == 401
    assert stolen.get("/api/users").status_code == 401  # only the cookie carries a session
    assert panel.get("/api/users").status_code == 200


# Finding 2: the hint for fetching a binary file put an attacker-chosen name, unquoted,
# into a shell command the server told the agent to run.
def test_the_fetch_command_quotes_hostile_file_names(tmp_path: Path) -> None:
    shutil.copytree(EXAMPLE, tmp_path / "brain")
    brain = Brain(tmp_path / "brain", lambda: {"costs": ["a@x.test"]}, git=False)
    name = "q3$(touch pwned)`id`; rm -rf ~ & x.xlsx"
    source = brain.root / ".upload-test.brainfold-tmp"
    source.write_bytes(b"\x00binary")
    brain.put_file("a@x.test", f"/projects/costs/{name}", source, None)
    command = brain.read("a@x.test", f"/projects/costs/{name}")["fetch"]
    assert shlex.split(command) == ["brainfold", "get", f"/projects/costs/{name}", f"./{name}"]
