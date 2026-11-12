from __future__ import annotations

import asyncio
import json
import shutil
import socket
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any

import pytest
import uvicorn
from mcp import ClientSession
from mcp.client.streamable_http import streamablehttp_client
from starlette.testclient import TestClient

from oif import OIFError
from oif.accounts import Accounts
from oif.server import create_app

EXAMPLE = Path(__file__).parent.parent / "examples" / "brain"
ADMIN, ALICE, BOB = "admin@atlas.test", "alice@atlas.test", "bob@atlas.test"
PASSWORD = "a-long-password"


@pytest.fixture
def app(tmp_path: Path) -> Any:
    shutil.copytree(EXAMPLE, tmp_path / "brain")
    return create_app(tmp_path / "brain", tmp_path / "oif.db")


def join(app: Any, admin: TestClient, email: str) -> TestClient:
    invite = admin.post("/api/users", json={"email": email}).json()["invite"]
    member = TestClient(app)
    assert (
        member.post("/api/accept", json={"invite": invite, "password": PASSWORD}).status_code == 200
    )
    return member


def code(response: Any) -> str:
    return response.json()["error"]["code"]


def test_first_account_administers_and_members_join_by_invite(app: Any) -> None:
    admin = TestClient(app)
    assert admin.get("/api/state").json() == {"setup_needed": True, "user": None}
    assert admin.post("/api/setup", json={"email": ADMIN, "password": PASSWORD}).status_code == 200
    assert admin.get("/api/state").json()["user"] == {"email": ADMIN, "role": "admin"}
    # Setup cannot be repeated, and weak passwords are refused.
    other = TestClient(app)
    assert (
        code(other.post("/api/setup", json={"email": BOB, "password": PASSWORD}))
        == "already_set_up"
    )
    assert other.get("/api/users").status_code == 401

    invite = admin.post("/api/users", json={"email": ALICE}).json()["invite"]
    assert code(other.post("/api/accept", json={"invite": invite, "password": "short"})) == (
        "invalid_password"
    )
    assert (
        other.post("/api/accept", json={"invite": invite, "password": PASSWORD}).status_code == 200
    )
    assert code(
        TestClient(app).post("/api/accept", json={"invite": invite, "password": PASSWORD})
    ) == ("invalid_invite")
    # Members cannot administer.
    for call in (
        lambda: other.get("/api/users"),
        lambda: other.get("/api/activity"),
        lambda: other.put("/api/groups/costs", json={"members": [ALICE]}),
        lambda: other.put("/api/folder", json={"path": "/", "read": ["*"]}),
    ):
        assert call().status_code == 403
    assert code(admin.delete(f"/api/users/{ADMIN}")) == "last_admin"


def test_login_is_throttled_and_sessions_end(app: Any) -> None:
    admin = TestClient(app)
    admin.post("/api/setup", json={"email": ADMIN, "password": PASSWORD})
    assert admin.post("/api/logout", json={}).status_code == 200
    assert admin.get("/api/tokens").status_code == 401
    fresh = TestClient(app)
    for _ in range(5):
        assert code(fresh.post("/api/login", json={"email": ADMIN, "password": "x" * 12})) == (
            "invalid_credentials"
        )
    assert code(fresh.post("/api/login", json={"email": ADMIN, "password": PASSWORD})) == (
        "too_many_attempts"
    )
    # Cross-site form posts cannot carry a JSON content type.
    assert fresh.post("/api/login", data={"email": ADMIN, "password": PASSWORD}).status_code == 400


def test_panel_manages_groups_folders_files_and_activity(app: Any) -> None:
    admin = TestClient(app)
    admin.post("/api/setup", json={"email": ADMIN, "password": PASSWORD})
    alice, bob = join(app, admin, ALICE), join(app, admin, BOB)
    assert code(admin.put("/api/groups/costs", json={"members": ["nobody@atlas.test"]})) == (
        "invalid_group"
    )
    admin.put("/api/groups/costs", json={"members": [ALICE]})
    admin.put("/api/groups/contracts", json={"members": [BOB]})

    entries = {
        e["path"] for e in alice.get("/api/tree", params={"path": "/projects"}).json()["entries"]
    }
    assert entries == {"/projects/costs"}
    path = {"path": "/projects/costs/process.md"}
    assert alice.get("/api/file", params=path).status_code == 200
    assert bob.get("/api/file", params=path).status_code == 404
    # The administrator sees structure and grants, not content, until granted.
    managed = admin.get("/api/tree", params={"path": "/projects"}).json()
    assert len(managed["entries"]) == 2 and managed["entries"][0]["read"]
    assert admin.get("/api/file", params=path).status_code == 404

    change = {"path": "/projects/costs", "description": "Costs", "read": ["@costs", BOB]}
    assert admin.put("/api/folder", json=change).status_code == 200
    assert bob.get("/api/file", params=path).status_code == 200
    admin.delete(f"/api/users/{BOB}")
    assert bob.get("/api/file", params=path).status_code == 401

    actions = [
        (row["actor"], row["action"], row["ok"])
        for row in admin.get("/api/activity").json()["activity"]
    ]
    assert (BOB, "read", False) in actions and (ADMIN, "edit_access", True) in actions


@asynccontextmanager
async def running(app: Any) -> AsyncIterator[str]:
    listener = socket.socket()
    listener.bind(("127.0.0.1", 0))
    listener.listen()
    server = uvicorn.Server(uvicorn.Config(app, log_level="critical", lifespan="on"))
    task = asyncio.create_task(server.serve(sockets=[listener]))
    try:
        async with asyncio.timeout(5):
            while not server.started:  # noqa: ASYNC110
                await asyncio.sleep(0.01)
        yield f"http://127.0.0.1:{listener.getsockname()[1]}/mcp"
    finally:
        server.should_exit = True
        await task


@asynccontextmanager
async def harness(url: str, token: str | None) -> AsyncIterator[ClientSession]:
    headers = {"Authorization": f"Bearer {token}"} if token else {}
    async with streamablehttp_client(url, headers=headers) as (read, write, _):
        async with ClientSession(read, write) as session:
            session.instructions = (await session.initialize()).instructions or ""
            yield session


async def call(session: ClientSession, tool: str, **arguments: Any) -> tuple[bool, Any]:
    result = await session.call_tool(tool, arguments)
    text = result.content[0].text
    return result.isError, text if result.isError else json.loads(text)


@pytest.fixture
def team(tmp_path: Path) -> tuple[Any, Accounts, dict[str, str]]:
    shutil.copytree(EXAMPLE, tmp_path / "brain")
    app = create_app(tmp_path / "brain", tmp_path / "oif.db")
    accounts = Accounts(tmp_path / "oif.db")
    accounts.setup(ALICE, PASSWORD)
    accounts.accept(accounts.invite(BOB, "member"), PASSWORD)
    accounts.set_group("costs", [ALICE])
    accounts.set_group("contracts", [BOB])
    return app, accounts, {who: accounts.issue(who, "access", "harness")[1] for who in (ALICE, BOB)}


async def test_a_harness_works_with_a_personal_token_until_it_is_revoked(team: Any) -> None:
    app, accounts, tokens = team
    async with running(app) as url:
        async with harness(url, tokens[ALICE]) as alice:
            failed, root = await call(alice, "list")
            assert not failed and root["home"].startswith("/people/alice-")
            failed, written = await call(alice, "write", path=f"{root['home']}/n.md", content="x")
            assert not failed and written["versioned"]
            failed, text = await call(alice, "write", path=f"{root['home']}/n.md", content="y")
            assert failed and "already_exists" not in text and written["version"] in text
            assert not (await call(alice, "edit", path=f"{root['home']}/n.md", old="x", new="z"))[0]
            assert not (
                await call(alice, "create_folder", path="/projects/costs/r", description="R")
            )[0]
            assert not (
                await call(alice, "append", path="/projects/costs/LEARNINGS.md", content="A")
            )[0]
            failed, learned = await call(alice, "list_learnings")
            assert learned["learnings"][0]["author"] == ALICE
        async with harness(url, tokens[BOB]) as bob:
            assert (await call(bob, "read", path=f"{root['home']}/n.md"))[0]
            assert (await call(bob, "list_learnings"))[1]["learnings"] == []
        async with harness(url, None) as nobody:
            failed, text = await call(nobody, "list")
            assert failed and "Authentication" in text
        identifier = accounts.tokens(ALICE)[0]["id"]
        accounts.revoke(ALICE, identifier)
        async with harness(url, tokens[ALICE]) as revoked:
            assert (await call(revoked, "list"))[0]
    done = {(row["action"], row["ok"], row["versioned"]) for row in accounts.activity()}
    assert {("write", True, True), ("write", False, None), ("list_learnings", True, None)} <= done


async def test_each_identity_is_told_only_the_skills_it_can_read(team: Any) -> None:
    app, _, tokens = team

    async def described(session: ClientSession) -> str:
        tools = (await session.list_tools()).tools
        return next(tool.description for tool in tools if tool.name == "use_skill")

    async with running(app) as url:
        async with harness(url, tokens[ALICE]) as alice:
            seen = await described(alice)
            assert "truncated samples" in seen and "propose-skills" in seen
            name = "analyze-costs-" + seen.split("- analyze-costs-")[1].split(":")[0]
            # Harnesses may defer tool descriptions; instructions are always in context.
            assert name in alice.instructions
            assert (
                "Ask for the summary first"
                in (await call(alice, "use_skill", name=name))[1]["content"]
            )
            proposal = (await call(alice, "use_skill", name="propose-skills"))[1]["content"]
            assert all(word in proposal for word in ("untrusted", "Cite", "confirmation"))
        for token in (tokens[BOB], None):
            async with harness(url, token) as other:
                assert "analyze-costs" not in await described(other)
                assert "analyze-costs" not in other.instructions
                assert (await call(other, "use_skill", name=name))[0]


def test_health_and_configuration_guards(tmp_path: Path) -> None:
    shutil.copytree(EXAMPLE, tmp_path / "brain")
    with pytest.raises(OIFError) as error:
        create_app(tmp_path / "brain", tmp_path / "brain" / "oif.db")
    assert error.value.code == "invalid_configuration"
    client = TestClient(create_app(tmp_path / "brain", tmp_path / "oif.db", git=False))
    assert client.get("/api/health").json() == {
        "git": False,
        "database": True,
        "unversioned_writes": 0,
    }


def test_a_removed_member_never_gets_the_old_personal_folder_back(tmp_path: Path) -> None:
    accounts = Accounts(tmp_path / "oif.db")
    accounts.setup(ADMIN, PASSWORD)
    accounts.invite(ALICE, "member")
    first = accounts.alias(ALICE)
    accounts.remove_user(ALICE)
    accounts.invite(ALICE, "member")
    assert first and accounts.alias(ALICE) not in (None, first)
    # A database created before aliases existed is migrated in place.
    reopened = Accounts(tmp_path / "oif.db")
    assert reopened.alias(ADMIN) == accounts.alias(ADMIN)
