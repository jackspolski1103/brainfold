"""A permission change during reasoning cannot release data from an earlier grant."""

import asyncio

import httpx
import pytest

from oif.api import create_app
from oif.auth import DevelopmentTokenAuth
from oif.domain import ModelTurn, OIFError, RemoteTool, ToolCall
from oif.memory import PermissionedMemory
from oif.registry import Registry
from oif.runtime import AgentRunner
from oif.service import SharedService
from oif.verification import example_configuration

MARKER = "SYNTHETIC_RESTRICTED_CONTRACT_CONTEXT"


class DiscoveryOnly:
    async def list_tools(self, connection):
        return [RemoteTool(name="query_records", input_schema={"type": "object"})]

    async def call(self, connection, tool_name, arguments):
        raise OIFError("herramienta_no_disponible", "No usada por esta prueba.")


class PausedModel:
    def __init__(self):
        self.entered = asyncio.Event()
        self.release = asyncio.Event()
        self.last_messages = []

    async def complete(self, messages, tools):
        self.last_messages = messages
        last = messages[-1]
        if last.role == "user" and last.content == "leer archivo":
            return ModelTurn(
                tool_calls=(
                    ToolCall(
                        id="memory-call",
                        name="leer_memoria",
                        arguments={"path": "/proyectos/contratos/proceso.md"},
                    ),
                )
            )
        if last.role == "tool":
            return ModelTurn(content=MARKER)
        if last.content == "retomar":
            self.entered.set()
            await self.release.wait()
            return ModelTurn(content=MARKER)
        return ModelTurn(content="Continuamos con los permisos vigentes.")


@pytest.mark.parametrize("changed_identity", ["alice", "reviewer"])
async def test_partial_requester_or_audience_revocation_during_model_drops_response(
    changed_identity,
):
    config = example_configuration()
    config = config.model_copy(
        update={
            "principals": tuple(
                principal.model_copy(update={"project_ids": frozenset({"costs", "contracts"})})
                if principal.id == "alice"
                else principal
                for principal in config.principals
            ),
            "memory_nodes": tuple(
                node.model_copy(update={"content": MARKER})
                if node.path == "/proyectos/contratos/proceso.md"
                else node
                for node in config.memory_nodes
            ),
        }
    )
    registry = Registry(config)
    service = SharedService(registry, DiscoveryOnly(), PermissionedMemory(config.memory_nodes))
    model = PausedModel()
    runner = AgentRunner(service, model)
    app = create_app(service, runner, DevelopmentTokenAuth({"test-only-token": "alice"}))
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app),
        base_url="http://test",
        headers={"Authorization": "Bearer test-only-token"},
    ) as client:
        response = await client.post(
            "/v1/sessions",
            json={
                "agent_id": "costs-agent",
                "audience_ids": ["reviewer"],
            },
        )
        session_id = response.json()["id"]
        path = f"/v1/sessions/{session_id}/messages"
        seeded = await client.post(path, json={"text": "leer archivo"})
        assert seeded.status_code == 200 and MARKER in seeded.text
        request = asyncio.create_task(client.post(path, json={"text": "retomar"}))
        async with asyncio.timeout(5):
            await model.entered.wait()
        principal = registry.principal(changed_identity)
        registry.replace_principal(
            principal.model_copy(update={"project_ids": frozenset({"costs"})})
        )
        model.release.set()
        blocked = await request
        assert blocked.status_code == 409
        assert MARKER not in blocked.text
        history = await client.get(f"/v1/sessions/{session_id}")
        assert history.status_code == 200
        assert history.json()["messages"] == []
        next_turn = await client.post(path, json={"text": "continuar"})
        assert next_turn.status_code == 200
        assert all(MARKER not in message.content for message in model.last_messages)
