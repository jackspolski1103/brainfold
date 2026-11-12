from pathlib import Path

import httpx

from oif.bootstrap import build_service_app
from oif.mcp_client import MCPTransport

CONFIG_PATH = Path(__file__).resolve().parents[1] / "examples" / "atlas.json"


async def test_unconfigured_model_does_not_contact_mcp_or_provider(monkeypatch):
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.delenv("OIF_OPENAI_MODEL", raising=False)
    monkeypatch.setenv("OIF_IDENTITY_ENV_MAP", '{"alice":"OIF_TOKEN_ALICE"}')
    monkeypatch.setenv("OIF_TOKEN_ALICE", "test-only-token")

    async def unexpected_network(*args, **kwargs):
        raise AssertionError("No se debe contactar MCP sin un modelo configurado.")

    monkeypatch.setattr(MCPTransport, "list_tools", unexpected_network)
    app = build_service_app(CONFIG_PATH)
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app),
        base_url="http://test",
        headers={"Authorization": "Bearer test-only-token"},
    ) as client:
        health = (await client.get("/health")).json()
        assert health["model"] is None
        assert health["model_provider"] is None
        created = await client.post("/v1/sessions", json={"agent_id": "costs-agent"})
        assert created.status_code == 201
        response = await client.post(
            f"/v1/sessions/{created.json()['id']}/messages",
            json={"text": "Hola"},
        )
        assert response.status_code == 503
        assert response.json()["error"]["code"] == "modelo_no_configurado"
        assert "test-only-token" not in response.text
