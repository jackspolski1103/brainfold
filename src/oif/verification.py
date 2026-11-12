"""Reproducible HTTP/MCP integration proof, not a simulated conversational product.

The scripted model only drives known tool calls. No provider credential, client data,
external email or paid inference is used. All temporary servers close on completion.
"""

from __future__ import annotations

import asyncio
import json
import secrets
import socket
from collections.abc import AsyncIterator, Callable, Sequence
from contextlib import asynccontextmanager, contextmanager, suppress
from importlib.resources import files
from pathlib import Path
from typing import Any

import httpx
import uvicorn

from oif.domain import Configuration, Message, ModelTurn, OIFError, ToolCall, ToolDescription


class FixtureQueryModel:
    """A test driver: it does not understand language or evaluate model reasoning."""

    async def complete(
        self, messages: Sequence[Message], tools: Sequence[ToolDescription]
    ) -> ModelTurn:
        last = messages[-1]
        if last.role == "user":
            name = "consultar_registros"
            arguments = {"kind": "fail" if last.content == "fail" else "details"}
            for prefix, memory_tool in (
                ("memory-list:", "listar_memoria"),
                ("memory-read:", "leer_memoria"),
            ):
                if last.content.startswith(prefix):
                    name = memory_tool
                    arguments = {"path": last.content.removeprefix(prefix)}
            return ModelTurn(
                tool_calls=(
                    ToolCall(
                        id=secrets.token_hex(8),
                        name=name,
                        arguments=arguments,
                    ),
                )
            )
        if last.role == "tool":
            return ModelTurn(content="Resultado de la prueba sintética: " + last.content)
        raise OIFError("verificacion_fallida", "El driver de prueba recibió un turno inesperado.")


class _ProofServer(uvicorn.Server):
    @contextmanager
    def capture_signals(self):
        # Multiple temporary servers run in the same event loop; don't replace app signals.
        yield


@asynccontextmanager
async def serve_for_verification(
    factory: Callable[[str, int], Any],
) -> AsyncIterator[str]:
    """Start a bounded temporary loopback ASGI server on a reserved socket."""
    host = "127.0.0.1"
    listener = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    task: asyncio.Task | None = None
    server: _ProofServer | None = None
    try:
        listener.bind((host, 0))
        port = listener.getsockname()[1]
        app = factory(host, port)
        server = _ProofServer(
            uvicorn.Config(
                app,
                host=host,
                port=port,
                log_level="critical",
                access_log=False,
                timeout_graceful_shutdown=2,
            )
        )
        task = asyncio.create_task(server.serve(sockets=[listener]))
        async with asyncio.timeout(10):
            while not server.started:
                if task.done():
                    await task
                    raise OIFError(
                        "verificacion_fallida", "No se pudo iniciar el servicio de prueba."
                    )
                await asyncio.sleep(0.01)
        yield f"http://{host}:{port}"
    finally:
        if server is not None:
            server.should_exit = True
        if task is not None:
            try:
                async with asyncio.timeout(5):
                    await task
            except TimeoutError:
                task.cancel()
                with suppress(asyncio.CancelledError):
                    await task
        listener.close()


def example_configuration() -> Configuration:
    # The source tree and a built wheel both carry the same canonical secret-free manifest.
    source = Path(__file__).resolve().parents[2] / "examples" / "atlas.json"
    text = (
        source.read_text(encoding="utf-8")
        if source.is_file()
        else files("oif.fixtures").joinpath("atlas.json").read_text(encoding="utf-8")
    )
    return Configuration.model_validate_json(text)


def _require(condition: bool, check: str) -> None:
    if not condition:
        raise OIFError("verificacion_fallida", f"Falló la comprobación: {check}.")


async def verify_example() -> dict[str, Any]:
    from oif.api import create_app
    from oif.auth import DevelopmentTokenAuth
    from oif.fixtures.mcp_server import create_mcp_app
    from oif.mcp_client import MCPTransport
    from oif.memory import PermissionedMemory
    from oif.registry import Registry
    from oif.runtime import AgentRunner
    from oif.service import SharedService

    async with serve_for_verification(create_mcp_app) as mcp_url:
        config = example_configuration()
        config = config.model_copy(
            update={
                "connections": tuple(
                    connection.model_copy(update={"url": mcp_url + "/mcp"})
                    for connection in config.connections
                )
            }
        )
        registry = Registry(config)
        memory = PermissionedMemory(config.memory_nodes)
        service = SharedService(registry, MCPTransport(), memory)
        runner = AgentRunner(service, FixtureQueryModel())
        tokens = {principal.id: secrets.token_urlsafe(32) for principal in config.principals}
        auth = DevelopmentTokenAuth({token: identity for identity, token in tokens.items()})
        app = create_app(service, runner, auth)
        async with serve_for_verification(lambda _host, _port: app) as service_url:
            async with httpx.AsyncClient(
                base_url=service_url,
                timeout=30,
                trust_env=False,
            ) as client:

                def headers(identity: str) -> dict[str, str]:
                    return {"Authorization": f"Bearer {tokens[identity]}"}

                sessions: dict[str, str] = {}
                checks: list[str] = []
                response = await client.get("/v1/agents")
                _require(response.status_code == 401, "autenticación obligatoria")
                checks.append("authentication_required")
                for identity, agent_id in (("alice", "costs-agent"), ("bob", "contracts-agent")):
                    response = await client.get("/v1/agents", headers=headers(identity))
                    _require(response.status_code == 200, "listado autorizado")
                    _require(
                        [agent["id"] for agent in response.json()["agents"]] == [agent_id],
                        "aislamiento del catálogo",
                    )
                    response = await client.post(
                        "/v1/sessions",
                        json={"agent_id": agent_id},
                        headers=headers(identity),
                    )
                    _require(response.status_code == 201, "creación de sesión")
                    sessions[identity] = response.json()["id"]
                    result = await client.post(
                        f"/v1/sessions/{sessions[identity]}/messages",
                        json={"text": "details"},
                        headers=headers(identity),
                    )
                    _require(result.status_code == 200, "consulta mediante MCP")
                    body = result.json()
                    _require(body["capability_versions"] == {"consultar_registros": 1}, "versión 1")
                    _require(body["tool_results"][0]["data"]["count"] == 1, "límite compartido v1")
                    expected_prefix = (
                        "synthetic-cost-" if identity == "alice" else "synthetic-contract-"
                    )
                    rows = body["tool_results"][0]["data"]["rows"]
                    _require(
                        all(row["id"].startswith(expected_prefix) for row in rows),
                        "datos de proyecto",
                    )
                checks.extend(["shared_capability_v1", "project_data_isolation"])

                # One trusted server-side publication affects both HTTP clients.
                original = registry.current_capability("consultar_registros")
                registry.publish_capability(
                    original.model_copy(
                        update={
                            "version": 2,
                            "fixed_arguments": {"limit": 2},
                            "instructions": original.instructions
                            + " La corrección v2 amplía la muestra a dos filas.",
                        }
                    )
                )
                errors: list[str] = []
                for identity in sessions:
                    response = await client.post(
                        f"/v1/sessions/{sessions[identity]}/messages",
                        json={"text": "details"},
                        headers=headers(identity),
                    )
                    _require(response.status_code == 200, "consulta con corrección común")
                    body = response.json()
                    _require(body["capability_versions"] == {"consultar_registros": 2}, "versión 2")
                    _require(body["tool_results"][0]["data"]["count"] == 2, "límite compartido v2")
                    response = await client.post(
                        f"/v1/sessions/{sessions[identity]}/messages",
                        json={"text": "fail"},
                        headers=headers(identity),
                    )
                    _require(response.status_code == 200, "falla de herramienta clasificada")
                    tool_result = response.json()["tool_results"][0]
                    _require(not tool_result["ok"], "falla explícita")
                    errors.append(tool_result["error"]["code"])
                _require(errors[0] == errors[1], "mismo contrato de error")
                checks.extend(["single_correction_both_agents_v2", "consistent_tool_errors"])

                for identity in ("bob", "outsider"):
                    response = await client.post(
                        "/v1/sessions",
                        json={"agent_id": "costs-agent"},
                        headers=headers(identity),
                    )
                    _require(response.status_code == 403, "acceso ajeno denegado")
                response = await client.get(
                    f"/v1/sessions/{sessions['alice']}",
                    headers=headers("bob"),
                )
                _require(response.status_code == 403, "propiedad de sesión")
                response = await client.post(
                    "/v1/sessions",
                    json={"agent_id": "costs-agent", "audience_ids": ["bob"]},
                    headers=headers("alice"),
                )
                _require(response.status_code == 403, "audiencia ajena")
                checks.extend(
                    [
                        "cross_project_denied",
                        "cross_organization_denied",
                        "private_session",
                        "audience_checked",
                    ]
                )

                async def memory_result(identity: str, command: str) -> dict[str, Any]:
                    response = await client.post(
                        f"/v1/sessions/{sessions[identity]}/messages",
                        json={"text": command},
                        headers=headers(identity),
                    )
                    _require(response.status_code == 200, "navegación de memoria")
                    return response.json()["tool_results"][0]

                for identity, folder in (("alice", "costos"), ("bob", "contratos")):
                    listing = await memory_result(identity, "memory-list:/proyectos")
                    _require(listing["ok"], "listado autorizado")
                    _require(
                        [item["path"] for item in listing["data"]] == [f"/proyectos/{folder}"],
                        "ocultar carpetas ajenas",
                    )
                    shared_file = await memory_result(
                        identity, "memory-read:/comun/convenciones.md"
                    )
                    _require(shared_file["ok"], "lectura compartida")
                    _require("ARS" in shared_file["data"]["content"], "contenido de memoria")
                forbidden = await memory_result(
                    "bob", "memory-read:/personas/alice/preferencias.md"
                )
                _require(
                    not forbidden["ok"] and forbidden["error"]["code"] == "ruta_no_disponible",
                    "archivo privado",
                )
                traversal = await memory_result("alice", "memory-read:/proyectos/../personas")
                _require(not traversal["ok"], "rutas sin escape")
                shared = next(
                    node for node in config.memory_nodes if node.path == "/comun/convenciones.md"
                )
                memory.replace_node(shared.model_copy(update={"status": "revoked"}))
                response = await client.get(
                    f"/v1/sessions/{sessions['alice']}", headers=headers("alice")
                )
                _require(response.status_code == 200, "sesión vigente tras cambio de memoria")
                _require(response.json()["messages"] == [], "historial invalidado tras revocación")
                denied_file = await memory_result("alice", "memory-read:/comun/convenciones.md")
                _require(not denied_file["ok"] and denied_file["data"] is None, "archivo revocado")
                checks.extend(
                    [
                        "permissioned_memory_navigation",
                        "private_memory_isolation",
                        "memory_path_traversal_denied",
                        "memory_revocation_clears_old_context",
                    ]
                )

                alice = registry.principal("alice")
                registry.replace_principal(alice.model_copy(update={"project_ids": frozenset()}))
                response = await client.post(
                    f"/v1/sessions/{sessions['alice']}/messages",
                    json={"text": "details"},
                    headers=headers("alice"),
                )
                _require(response.status_code == 403, "revocación de membresía")
                checks.append("membership_revocation_on_open_session")
                registry.revoke_capability("consultar_registros")
                response = await client.post(
                    f"/v1/sessions/{sessions['bob']}/messages",
                    json={"text": "details"},
                    headers=headers("bob"),
                )
                if response.status_code == 200:
                    result = response.json()["tool_results"][0]
                    _require(not result["ok"] and result["data"] is None, "revocación de capacidad")
                else:
                    _require(response.status_code in {403, 409}, "revocación de capacidad")
                checks.append("capability_revocation_no_fallback")

                return {
                    "status": "passed",
                    "shared_service": "real HTTP",
                    "tool_connection": "real MCP Streamable HTTP",
                    "memory": "permissioned virtual folders/files; in-memory development adapter",
                    "model": "scripted integration-test driver; no paid inference",
                    "model_reasoning_verified": False,
                    "agents": ["costs-agent", "contracts-agent"],
                    "checks": checks,
                }


def main() -> None:
    print(json.dumps(asyncio.run(verify_example()), ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
