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
PASSWORD = "una-clave-larga"


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
        == "ya_configurado"
    )
    assert other.get("/api/users").status_code == 401

    invite = admin.post("/api/users", json={"email": ALICE}).json()["invite"]
    assert code(other.post("/api/accept", json={"invite": invite, "password": "corta"})) == (
        "contrasena_invalida"
    )
    assert (
        other.post("/api/accept", json={"invite": invite, "password": PASSWORD}).status_code == 200
    )
    assert code(
        TestClient(app).post("/api/accept", json={"invite": invite, "password": PASSWORD})
    ) == ("invitacion_invalida")
    # Members cannot administer.
    for call in (
        lambda: other.get("/api/users"),
        lambda: other.get("/api/activity"),
        lambda: other.put("/api/groups/costs", json={"members": [ALICE]}),
        lambda: other.put("/api/folder", json={"path": "/", "read": ["*"]}),
    ):
        assert call().status_code == 403
    assert code(admin.delete(f"/api/users/{ADMIN}")) == "ultimo_admin"


def test_login_is_throttled_and_sessions_end(app: Any) -> None:
    admin = TestClient(app)
    admin.post("/api/setup", json={"email": ADMIN, "password": PASSWORD})
    assert admin.post("/api/logout", json={}).status_code == 200
    assert admin.get("/api/tokens").status_code == 401
    fresh = TestClient(app)
    for _ in range(5):
        assert code(fresh.post("/api/login", json={"email": ADMIN, "password": "x" * 12})) == (
            "credenciales_invalidas"
        )
    assert code(fresh.post("/api/login", json={"email": ADMIN, "password": PASSWORD})) == (
        "demasiados_intentos"
    )
    # Cross-site form posts cannot carry a JSON content type.
    assert fresh.post("/api/login", data={"email": ADMIN, "password": PASSWORD}).status_code == 400


def test_panel_manages_groups_folders_files_and_activity(app: Any) -> None:
    admin = TestClient(app)
    admin.post("/api/setup", json={"email": ADMIN, "password": PASSWORD})
    alice, bob = join(app, admin, ALICE), join(app, admin, BOB)
    assert code(admin.put("/api/groups/costs", json={"members": ["nadie@atlas.test"]})) == (
        "grupo_invalido"
    )
    admin.put("/api/groups/costs", json={"members": [ALICE]})
    admin.put("/api/groups/contracts", json={"members": [BOB]})

    entries = {
        e["path"] for e in alice.get("/api/tree", params={"path": "/proyectos"}).json()["entries"]
    }
    assert entries == {"/proyectos/costos"}
    path = {"path": "/proyectos/costos/proceso.md"}
    assert alice.get("/api/file", params=path).status_code == 200
    assert bob.get("/api/file", params=path).status_code == 404
    # The administrator sees structure and grants, not content, until granted.
    managed = admin.get("/api/tree", params={"path": "/proyectos"}).json()
    assert len(managed["entries"]) == 2 and managed["entries"][0]["read"]
    assert admin.get("/api/file", params=path).status_code == 404

    change = {"path": "/proyectos/costos", "description": "Costos", "read": ["@costs", BOB]}
    assert admin.put("/api/folder", json=change).status_code == 200
    assert bob.get("/api/file", params=path).status_code == 200
    admin.delete(f"/api/users/{BOB}")
    assert bob.get("/api/file", params=path).status_code == 401

    actions = [
        (row["actor"], row["action"], row["ok"])
        for row in admin.get("/api/activity").json()["activity"]
    ]
    assert (BOB, "leer", False) in actions and (ADMIN, "editar_accesos", True) in actions


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
        failed, text = await call(token, "listar_skills", {})
        assert not failed and "analizar-costos" in text
        failed, text = await call(
            token, "escribir_memoria", {"path": "/proyectos/costos/n.md", "content": "x"}
        )
        assert not failed
        assert (await call(token, "leer_memoria", {"path": "/personas/alice/preferencias.md"}))[
            0
        ] is False
        failed, text = await call(None, "listar_memoria", {})
        assert failed and "autenticación" in text
        accounts.revoke(ALICE, identifier)
        assert (await call(token, "listar_memoria", {}))[0] is True
    done = {(row["action"], row["ok"]) for row in accounts.activity()}
    assert {("skills", True), ("escribir", True), ("leer", True)} <= done
