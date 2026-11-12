from __future__ import annotations

import asyncio
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


async def test_a_harness_connects_with_a_personal_token_until_it_is_revoked(tmp_path: Path) -> None:
    shutil.copytree(EXAMPLE, tmp_path / "brain")
    app = create_app(tmp_path / "brain", tmp_path / "oif.db")
    accounts = Accounts(tmp_path / "oif.db")
    accounts.setup(ALICE, PASSWORD)
    accounts.set_group("costs", [ALICE])
    identifier, token = accounts.issue(ALICE, "access", "claude code")

    async def call(bearer: str | None, tool: str, arguments: dict) -> tuple[bool, str]:
        headers = {"Authorization": f"Bearer {bearer}"} if bearer else {}
        async with streamablehttp_client(url, headers=headers) as (read, write, _):
            async with ClientSession(read, write) as session:
                await session.initialize()
                result = await session.call_tool(tool, arguments)
                return result.isError, result.content[0].text

    async with running(app) as url:
        failed, text = await call(token, "list", {"path": "/skills"})
        assert not failed and "analyze-costs" in text
        failed, text = await call(token, "write", {"path": "/projects/costs/n.md", "content": "x"})
        assert not failed
        assert (await call(token, "read", {"path": "/people/alice/preferences.md"}))[0] is False
        failed, text = await call(None, "list", {})
        assert failed and "Authentication" in text
        accounts.revoke(ALICE, identifier)
        assert (await call(token, "list", {}))[0] is True
    done = {(row["action"], row["ok"]) for row in accounts.activity()}
    assert {("write", True), ("read", True)} <= done


async def test_use_skill_lists_only_what_each_identity_can_read(tmp_path: Path) -> None:
    shutil.copytree(EXAMPLE, tmp_path / "brain")
    app = create_app(tmp_path / "brain", tmp_path / "oif.db")
    accounts = Accounts(tmp_path / "oif.db")
    accounts.setup(ALICE, PASSWORD)
    accounts.accept(accounts.invite(BOB, "member"), PASSWORD)
    accounts.set_group("costs", [ALICE])
    accounts.set_group("contracts", [BOB])
    tokens = {who: accounts.issue(who, "access", "harness")[1] for who in (ALICE, BOB)}

    async def session_for(token: str | None, action: Any) -> Any:
        headers = {"Authorization": f"Bearer {token}"} if token else {}
        async with streamablehttp_client(url, headers=headers) as (read, write, _):
            async with ClientSession(read, write) as session:
                await session.initialize()
                return await action(session)

    async def description(session: ClientSession) -> str:
        tools = (await session.list_tools()).tools
        return next(tool.description for tool in tools if tool.name == "use_skill")

    async with running(app) as url:
        seen = await session_for(tokens[ALICE], description)
        assert "analyze-costs-" in seen and "truncated samples" in seen
        name = seen.split("- analyze-costs-")[1].split(":")[0]
        for other in (tokens[BOB], None):
            assert "analyze-costs" not in await session_for(other, description)

        async def use(session: ClientSession) -> Any:
            return await session.call_tool("use_skill", {"name": f"analyze-costs-{name}"})

        assert (
            "Ask for the summary first" in (await session_for(tokens[ALICE], use)).content[0].text
        )
        assert (await session_for(tokens[BOB], use)).isError

        async def instructions(token: str | None) -> str:
            headers = {"Authorization": f"Bearer {token}"} if token else {}
            async with streamablehttp_client(url, headers=headers) as (read, write, _):
                async with ClientSession(read, write) as session:
                    return (await session.initialize()).instructions or ""

        # Tool descriptions can be deferred by the harness; instructions are always in context.
        assert f"analyze-costs-{name}" in await instructions(tokens[ALICE])
        for other in (tokens[BOB], None):
            assert "analyze-costs" not in await instructions(other)
