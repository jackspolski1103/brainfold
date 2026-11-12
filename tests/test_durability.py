"""The brain must not be lost: mirror, restore from it, and the folder identity check."""

from __future__ import annotations

import shutil
import subprocess
import time
from pathlib import Path

import pytest
from starlette.testclient import TestClient

from brainfold import BrainfoldError, cli
from brainfold.accounts import Accounts
from brainfold.server import create_app

EXAMPLE = Path(__file__).parent.parent / "examples" / "brain"
ADMIN, PASSWORD = "lead@atlas.test", "a-long-password"


def wait_for(condition, seconds: float = 10) -> bool:
    deadline = time.time() + seconds
    while time.time() < deadline:
        if condition():
            return True
        time.sleep(0.05)
    return False


def test_every_change_reaches_the_mirror_and_an_empty_volume_is_restored_from_it(
    tmp_path: Path,
) -> None:
    mirror = tmp_path / "mirror.git"
    subprocess.run(["git", "init", "-q", "--bare", str(mirror)], check=True)
    shutil.copytree(EXAMPLE, tmp_path / "brain")
    app = create_app(tmp_path / "brain", tmp_path / "a.db", mirror=str(mirror))
    panel = TestClient(app)
    panel.post("/api/setup", json={"email": ADMIN, "password": PASSWORD})
    assert wait_for(lambda: panel.get("/api/health").json()["mirror"] == "ok")
    change = {"path": "/common", "description": "Changed after start", "read": None}
    assert panel.put("/api/folder", json=change).status_code == 200

    def mirrored() -> bool:
        shown = subprocess.run(
            ["git", "-C", str(mirror), "show", "main:common/.brainfold.toml"],
            capture_output=True,
            text=True,
        )
        return "Changed after start" in shown.stdout

    assert wait_for(mirrored)
    # The volume is lost: a new, empty folder and a new accounts database.
    (tmp_path / "new").mkdir()
    create_app(tmp_path / "new", tmp_path / "b.db", mirror=str(mirror))
    assert "Changed after start" in (tmp_path / "new" / "common" / ".brainfold.toml").read_text()
    assert (tmp_path / "new" / ".brainfold-id").read_text() == (
        tmp_path / "brain" / ".brainfold-id"
    ).read_text()


def test_a_server_never_starts_on_a_folder_that_is_not_its_brain(tmp_path: Path) -> None:
    shutil.copytree(EXAMPLE, tmp_path / "brain")
    create_app(tmp_path / "brain", tmp_path / "a.db", git=False)
    create_app(tmp_path / "brain", tmp_path / "a.db", git=False)  # same pair: fine
    (tmp_path / "empty").mkdir()  # what an unmounted volume looks like
    with pytest.raises(BrainfoldError) as error:
        create_app(tmp_path / "empty", tmp_path / "a.db", git=False)
    assert error.value.code == "invalid_configuration" and "volume" in error.value.message
    assert not any((tmp_path / "empty").iterdir())  # and it left that folder untouched
    shutil.copytree(EXAMPLE, tmp_path / "other")
    create_app(tmp_path / "other", tmp_path / "b.db", git=False)
    with pytest.raises(BrainfoldError):
        create_app(tmp_path / "other", tmp_path / "a.db", git=False)


def test_passwords_can_be_changed_and_recovered(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    shutil.copytree(EXAMPLE, tmp_path / "brain")
    app = create_app(tmp_path / "brain", tmp_path / "a.db", git=False)
    admin, other = TestClient(app), TestClient(app)
    admin.post("/api/setup", json={"email": ADMIN, "password": PASSWORD})
    other.post("/api/login", json={"email": ADMIN, "password": PASSWORD})
    wrong = {"current": "not-the-password", "new": "another-long-one"}
    assert admin.post("/api/password", json=wrong).status_code == 400
    assert (
        admin.post("/api/password", json={"current": PASSWORD, "new": "short"}).status_code == 400
    )
    changed = {"current": PASSWORD, "new": "another-long-one"}
    assert admin.post("/api/password", json=changed).status_code == 200
    assert admin.get("/api/tokens").status_code == 200  # this session continues
    assert other.get("/api/tokens").status_code == 401  # every other session ended
    assert other.post("/api/login", json={"email": ADMIN, "password": PASSWORD}).status_code == 400

    # An administrator resets a member's password with a one-time link.
    invite = admin.post("/api/users", json={"email": "ana@atlas.test"}).json()["invite"]
    member = TestClient(app)
    member.post("/api/accept", json={"invite": invite, "password": PASSWORD})
    assert member.post("/api/users/ana@atlas.test/reset", json={}).status_code == 403
    link = admin.post("/api/users/ana@atlas.test/reset", json={}).json()["invite"]
    fresh = TestClient(app)
    assert (
        fresh.post("/api/accept", json={"invite": link, "password": "ana-new-password"}).status_code
        == 200
    )
    assert member.get("/api/tokens").status_code == 401  # the reset signed the old session out
    assert (
        fresh.post("/api/accept", json={"invite": link, "password": "ana-new-password"}).status_code
        == 400
    )

    # The only administrator recovers access from the server's own command line.
    assert cli.main(["reset-password", ADMIN, "--db", str(tmp_path / "a.db")]) == 0
    token = capsys.readouterr().out.strip().rsplit("/", 1)[-1]
    assert (
        TestClient(app)
        .post("/api/accept", json={"invite": token, "password": "recovered-password"})
        .status_code
        == 200
    )
    assert Accounts(tmp_path / "a.db").login(ADMIN, "recovered-password")
    assert cli.main(["reset-password", "ghost@atlas.test", "--db", str(tmp_path / "a.db")]) == 1
