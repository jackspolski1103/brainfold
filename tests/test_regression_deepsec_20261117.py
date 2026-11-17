"""Regressions for the findings of the Deepsec scan of 2026-11-17."""

from __future__ import annotations

import os
import stat
import subprocess
from pathlib import Path

import pytest
from starlette.testclient import TestClient

from brainfold import BrainfoldError, accounts, cli
from brainfold.accounts import MAX_ADDRESS_FAILURES, Accounts
from brainfold.brain import Brain
from brainfold.server import create_app

ADMIN, PASSWORD = "lead@atlas.test", "a-long-password"


def code(response) -> str:
    return response.json()["error"]["code"]


# Naming a new email on every attempt reset the throttle, each attempt cost a password
# hash and left a counter and an activity row behind for good.
def test_one_address_cannot_buy_unlimited_logins(tmp_path: Path, monkeypatch) -> None:
    (tmp_path / "brain").mkdir()
    app = create_app(tmp_path / "brain", tmp_path / "a.db", git=False)
    panel = TestClient(app)
    assert panel.post("/api/setup", json={"email": ADMIN, "password": PASSWORD}).status_code == 200
    stranger = TestClient(app)
    for number in range(MAX_ADDRESS_FAILURES):
        body = {"email": f"nobody{number}@x.test", "password": "x" * 12}
        assert code(stranger.post("/api/login", json=body)) == "invalid_credentials"
    wrong = {"email": ADMIN, "password": "x" * 12}
    assert code(stranger.post("/api/login", json=wrong)) == "too_many_attempts"
    # Neither invented emails nor throttled attempts reach the activity log.
    failed = [row for row in panel.get("/api/activity").json()["activity"] if not row["ok"]]
    assert failed == []

    # A wrong password for a real account is still recorded, and idle counters are dropped.
    store = Accounts(tmp_path / "b.db")
    store.setup(ADMIN, PASSWORD)
    for number in range(50):
        with pytest.raises(BrainfoldError):
            store.login(f"nobody{number}@x.test", "x" * 12, f"203.0.113.{number}")
    assert len(store._failures) == 100
    monkeypatch.setattr(accounts, "LOCK_SECONDS", 0)
    with pytest.raises(BrainfoldError):
        store.login(ADMIN, "x" * 12, "198.51.100.7")
    assert len(store._failures) == 2


# Accepting an invitation hashed the password before looking at the link.
def test_no_password_hash_without_a_valid_link(tmp_path: Path, monkeypatch) -> None:
    store = Accounts(tmp_path / "a.db")
    store.setup(ADMIN, PASSWORD)
    monkeypatch.setattr(accounts, "_hash", lambda *_: pytest.fail("hashed for an invalid link"))
    with pytest.raises(BrainfoldError) as refused:
        store.accept("not-a-link", PASSWORD)
    assert refused.value.code == "invalid_invite"


# A pending administrator counted as one, so the only usable administrator could go.
def test_a_pending_administrator_does_not_cover_the_last_one(tmp_path: Path) -> None:
    store = Accounts(tmp_path / "a.db")
    store.setup(ADMIN, PASSWORD)
    invite = store.invite("second@atlas.test", "admin")
    with pytest.raises(BrainfoldError) as refused:
        store.remove_user(ADMIN)
    assert refused.value.code == "last_admin"
    store.accept(invite, PASSWORD)
    assert store.remove_user(ADMIN) == ADMIN


# Writing to "/" without read on the root walked above the brain and failed with an error
# that named the server's folders.
def test_writing_to_the_root_answers_like_any_hidden_path(tmp_path: Path) -> None:
    brain = Brain(tmp_path, lambda: {}, git=False)
    for call in (
        lambda: brain.write("a@x.test", "/", "x"),
        lambda: brain.append("a@x.test", "/", "x"),
        lambda: brain.delete("a@x.test", "/"),
        lambda: brain.describe_folder("a@x.test", "/", "x"),
    ):
        with pytest.raises(BrainfoldError) as refused:
            call()
        assert refused.value.code == "unavailable"


# The mirror's private key existed for a moment with the default permissions, a key that
# was not base64 printed a traceback, and the mirror's host key could not be pinned.
def test_the_mirror_key_is_private_from_the_start(tmp_path: Path, monkeypatch, capsys) -> None:
    import uvicorn

    mirror = tmp_path / "mirror.git"
    subprocess.run(["git", "init", "--quiet", "--bare", str(mirror)], check=True)
    serve = ["serve", "--root", str(tmp_path / "brain"), "--db", str(tmp_path / "data" / "a.db")]
    serve += ["--mirror", str(mirror), "--port", "0"]
    monkeypatch.setenv("BRAINFOLD_MIRROR_KEY", "abc")
    assert cli.main(serve) == 1 and "invalid_configuration" in capsys.readouterr().err

    modes, real_open = [], os.open
    monkeypatch.setattr(uvicorn, "run", lambda *_, **__: None)
    monkeypatch.setattr(
        cli.os,
        "open",
        lambda path, flags, mode=0o777, **more: (
            modes.append(mode) if Path(path).name == "mirror_key" else None,
            real_open(path, flags, mode, **more),
        )[1],
    )
    monkeypatch.setenv("BRAINFOLD_MIRROR_KEY", "-----BEGIN OPENSSH PRIVATE KEY-----\nx")
    monkeypatch.setenv("BRAINFOLD_MIRROR_HOST_KEY", "example.test ssh-ed25519 AAAA")
    used = {}
    real = create_app
    monkeypatch.setattr(
        "brainfold.server.create_app", lambda *a, **k: used.update(k) or real(*a, **k)
    )
    assert cli.main(serve) == 0
    key = tmp_path / "data" / "mirror_key"
    assert modes == [0o600] and stat.S_IMODE(os.stat(key).st_mode) == 0o600
    assert "StrictHostKeyChecking=yes" in used["ssh"]
    assert (tmp_path / "data" / "mirror_known_hosts").read_text() == (
        "example.test ssh-ed25519 AAAA\n"
    )
