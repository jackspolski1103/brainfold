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

from brainfold import BrainfoldError
from brainfold.accounts import Accounts
from brainfold.server import create_app

EXAMPLE = Path(__file__).parent.parent / "examples" / "brain"
ADMIN, ALICE, BOB = "admin@atlas.test", "alice@atlas.test", "bob@atlas.test"
PASSWORD = "a-long-password"


@pytest.fixture
def app(tmp_path: Path) -> Any:
    shutil.copytree(EXAMPLE, tmp_path / "brain")
    return create_app(tmp_path / "brain", tmp_path / "brainfold.db")


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
    assert admin.get("/api/state").json() == {
        "setup_needed": True,
        "code_required": False,
        "user": None,
    }
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
    app = create_app(tmp_path / "brain", tmp_path / "brainfold.db")
    accounts = Accounts(tmp_path / "brainfold.db")
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
    with pytest.raises(BrainfoldError) as error:
        create_app(tmp_path / "brain", tmp_path / "brain" / "brainfold.db")
    assert error.value.code == "invalid_configuration"
    client = TestClient(create_app(tmp_path / "brain", tmp_path / "brainfold.db", git=False))
    assert client.get("/api/health").json() == {
        "git": False,
        "database": True,
        "unversioned_writes": 0,
        "mirror": "off",
    }


def test_a_removed_member_never_gets_the_old_personal_folder_back(tmp_path: Path) -> None:
    accounts = Accounts(tmp_path / "brainfold.db")
    accounts.setup(ADMIN, PASSWORD)
    accounts.invite(ALICE, "member")
    first = accounts.alias(ALICE)
    accounts.remove_user(ALICE)
    accounts.invite(ALICE, "member")
    assert first and accounts.alias(ALICE) not in (None, first)
    # A database created before aliases existed is migrated in place.
    reopened = Accounts(tmp_path / "brainfold.db")
    assert reopened.alias(ADMIN) == accounts.alias(ADMIN)


async def test_files_travel_over_http_with_a_token_and_never_with_the_panel_cookie(
    team: Any, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    import httpx

    from brainfold import cli

    app, accounts, tokens = team
    sheet = bytes(range(256))
    async with running(app) as url:
        base = url.removesuffix("/mcp")
        alice = {"Authorization": f"Bearer {tokens[ALICE]}"}
        async with httpx.AsyncClient(base_url=base) as http:
            target = "/files/projects/costs/salaries.xlsx"
            stored = (await http.put(target, content=sheet, headers=alice)).json()
            assert (await http.put(target, content=b"x", headers=alice)).status_code == 409
            fetched = await http.get(target, headers=alice)
            assert fetched.content == sheet and fetched.headers["etag"] == f'"{stored["version"]}"'
            assert fetched.headers["content-disposition"] == "attachment"
            assert fetched.headers["x-content-type-options"] == "nosniff"
            assert fetched.headers["content-type"] == "application/octet-stream"
            replaced = await http.put(
                target, content=b"\x00v2", headers=alice | {"If-Match": fetched.headers["etag"]}
            )
            assert replaced.status_code == 200
            bob = {"Authorization": f"Bearer {tokens[BOB]}"}
            assert (await http.get(target, headers=bob)).status_code == 404
            assert (
                await http.put("/files/projects/costs/b.bin", content=b"x", headers=bob)
            ).status_code == 404
            assert (await http.get(target)).status_code == 401
            # A logged-in administrator's cookie does not open these routes.
            await http.post("/api/login", json={"email": ALICE, "password": PASSWORD})
            assert http.cookies and (await http.get(target)).status_code == 401
            assert (
                await http.get("/files/projects/costs/%2e%2e/%2e%2e/.brainfold.toml", headers=alice)
            ).status_code == 404

        # The command line reads the server and token from the environment only.
        monkeypatch.setenv("BRAINFOLD_URL", base)
        monkeypatch.setenv("BRAINFOLD_TOKEN", tokens[ALICE])
        local = tmp_path / "manual.pdf"
        local.write_bytes(b"%PDF-1.7 synthetic")
        run = asyncio.to_thread
        assert await run(cli.main, ["put", str(local), "/projects/costs/manual.pdf"]) == 0
        assert await run(cli.main, ["put", str(local), "/projects/costs/manual.pdf"]) == 1
        assert (
            await run(cli.main, ["put", "--replace", str(local), "/projects/costs/manual.pdf"]) == 0
        )
        assert (
            await run(cli.main, ["get", "/projects/costs/manual.pdf", str(tmp_path / "back.pdf")])
            == 0
        )
        assert (tmp_path / "back.pdf").read_bytes() == b"%PDF-1.7 synthetic"
        monkeypatch.setenv("BRAINFOLD_URL", "http://example.com")
        assert (
            await run(cli.main, ["get", "/projects/costs/manual.pdf", str(tmp_path / "no.pdf")])
            == 1
        )

        async with harness(url, tokens[ALICE]) as session:
            failed, seen = await call(session, "read", path="/projects/costs/salaries.xlsx")
            assert not failed and seen["kind"] == "binary" and "brainfold get" in seen["fetch"]
            failed, past = await call(session, "history", path="/projects/costs/salaries.xlsx")
            assert [row["change"] for row in past["revisions"]] == ["upload", "upload"]
            version = (await call(session, "read", path="/projects/costs/salaries.xlsx"))[1][
                "version"
            ]
            failed, _ = await call(
                session,
                "restore",
                path="/projects/costs/salaries.xlsx",
                revision=past["revisions"][0]["revision"],
                version=version,
            )
            assert not failed
        async with httpx.AsyncClient(base_url=base) as http:
            assert (await http.get(target, headers=alice)).content == sheet
    assert not list((tmp_path / "brain").glob(".upload-*"))
    actions = {row["action"] for row in accounts.activity()}
    assert {"upload", "download", "history", "restore"} <= actions


def test_a_retired_group_name_cannot_be_reused(tmp_path: Path) -> None:
    accounts = Accounts(tmp_path / "brainfold.db")
    accounts.setup(ADMIN, PASSWORD)
    accounts.set_group("finance", [ADMIN])
    accounts.set_group("finance", [])
    with pytest.raises(BrainfoldError) as error:
        accounts.set_group("finance", [ADMIN])
    assert error.value.code == "invalid_group"


async def test_behind_a_public_address_the_server_must_be_claimed_with_its_code(
    tmp_path: Path,
) -> None:
    shutil.copytree(EXAMPLE, tmp_path / "brain")
    app = create_app(
        tmp_path / "brain", tmp_path / "brainfold.db", public_url="https://brain.example.test"
    )
    client = TestClient(app, base_url="http://127.0.0.1")
    body = {"email": ADMIN, "password": PASSWORD}
    assert client.post("/api/setup", json=body).status_code == 403
    assert client.post("/api/setup", json=body | {"code": "guess"}).status_code == 403
    claimed = client.post("/api/setup", json=body | {"code": app.state.setup_code})
    assert claimed.status_code == 200 and "Secure" in claimed.headers["set-cookie"]
    again = {"email": BOB, "password": PASSWORD, "code": app.state.setup_code}
    assert code(client.post("/api/setup", json=again)) == "already_set_up"
    # One address failing does not lock the account for everyone else.
    for _ in range(5):
        wrong = {"email": ADMIN, "password": "x" * 12}
        client.post("/api/login", json=wrong, headers={"X-Forwarded-For": "203.0.113.9"})
    blocked = client.post("/api/login", json=body, headers={"X-Forwarded-For": "203.0.113.9"})
    assert code(blocked) == "too_many_attempts"
    assert (
        client.post(
            "/api/login", json=body, headers={"X-Forwarded-For": "198.51.100.7"}
        ).status_code
        == 200
    )

    # The MCP endpoint answers for the public host and refuses any other.
    token = Accounts(tmp_path / "brainfold.db").issue(ADMIN, "access", "harness")[1]
    async with running(app) as url:
        async with harness(url, token) as local:
            assert not (await call(local, "use_skill", name="propose-skills"))[0]
        import httpx

        request = {"jsonrpc": "2.0", "id": 1, "method": "tools/list"}
        headers = {
            "Authorization": f"Bearer {token}",
            "Accept": "application/json, text/event-stream",
        }
        async with httpx.AsyncClient() as http:
            public = await http.post(
                url, json=request, headers=headers | {"Host": "brain.example.test"}
            )
            other = await http.post(
                url, json=request, headers=headers | {"Host": "evil.example.test"}
            )
        assert public.status_code == 200 and other.status_code in {400, 403, 421}


def test_the_built_panel_is_served_with_a_restrictive_policy(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from brainfold import server

    shutil.copytree(EXAMPLE, tmp_path / "brain")
    monkeypatch.setattr(server, "PANEL", tmp_path / "missing")
    assert (
        TestClient(create_app(tmp_path / "brain", tmp_path / "a.db", git=False))
        .get("/")
        .status_code
        == 404
    )
    built = tmp_path / "panel"
    (built / "assets").mkdir(parents=True)
    (built / "index.html").write_text("<div id=root></div>")
    (built / "assets" / "app.js").write_text("console.log(1)")
    monkeypatch.setattr(server, "PANEL", built)
    client = TestClient(create_app(tmp_path / "brain", tmp_path / "b.db", git=False))
    page = client.get("/")
    assert (
        page.status_code == 200 and "default-src 'self'" in page.headers["content-security-policy"]
    )
    assert "frame-ancestors 'none'" in page.headers["content-security-policy"]
    assert client.get("/assets/app.js").status_code == 200
    assert client.get("/assets/../index.html").status_code in {200, 404}  # never outside the panel
    assert client.get("/api/state").json()["code_required"] is False


def test_panel_search_and_skills_follow_the_permissions_of_the_person(app: Any) -> None:
    admin = TestClient(app)
    admin.post("/api/setup", json={"email": ADMIN, "password": PASSWORD})
    alice, bob = join(app, admin, ALICE), join(app, admin, BOB)
    admin.put("/api/groups/costs", json={"members": [ALICE]})
    paths = [skill["path"] for skill in alice.get("/api/skills").json()["skills"]]
    assert paths[0] is None and any(path and path.endswith("/SKILL.md") for path in paths)
    assert [skill["path"] for skill in bob.get("/api/skills").json()["skills"]] == [None]
    hits = alice.get("/api/search", params={"q": "the"}).json()["hits"]
    assert hits and not bob.get("/api/search", params={"q": "the"}).json().get("hits")
    assert code(alice.get("/api/search")) == "empty_query"
    assert TestClient(app).get("/api/search", params={"q": "the"}).status_code == 401
