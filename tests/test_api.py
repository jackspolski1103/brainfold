"""HTTP and development identity tests require no real tokens or external services."""

import json

import httpx
import pytest

from oif.api import create_app
from oif.auth import DevelopmentTokenAuth
from oif.domain import (
    AgentDefinition,
    Configuration,
    OIFError,
    OrganizationContext,
    Principal,
    RunReply,
)
from oif.registry import Registry
from oif.service import SharedService


class Runner:
    async def turn(self, session, text):
        return RunReply(
            session_id=session.id,
            agent_id=session.agent_id,
            text="Resultado sintético.",
            tool_results=(),
            capability_versions={},
        )

    def cancel(self, session_id):
        return False


class UnusedTransport:
    async def list_tools(self, connection):
        raise AssertionError("no transport required")

    async def call(self, connection, tool_name, arguments):
        raise AssertionError("no transport required")


DEFAULT_RUNNER = Runner()


def build_app(runner=DEFAULT_RUNNER):
    config = Configuration(
        organizations=(
            OrganizationContext(id="atlas", content="Synthetic", version=1, status="published"),
        ),
        principals=(
            Principal(id="ana", organization_id="atlas", project_ids=frozenset({"costs"})),
            Principal(id="bea", organization_id="atlas", project_ids=frozenset({"contracts"})),
        ),
        connections=(),
        capabilities=(),
        agents=tuple(
            AgentDefinition(
                id=project,
                organization_id="atlas",
                project_id=project,
                instructions="Synthetic",
                capability_ids=(),
            )
            for project in ("costs", "contracts")
        ),
    )
    service = SharedService(Registry(config), UnusedTransport())
    auth = DevelopmentTokenAuth({"fixture-ana": "ana", "fixture-bea": "bea"})
    return create_app(service, runner, auth, model="test-model", model_provider="fixture"), service


def headers(person="ana"):
    return {"Authorization": f"Bearer fixture-{person}"}


async def test_health_identifies_development_auth_and_model_without_secret():
    app, _ = build_app()
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app), base_url="http://test"
    ) as client:
        response = await client.get("/health")
    assert response.json() == {
        "status": "ok",
        "authentication": "development-token",
        "model": "test-model",
        "model_provider": "fixture",
    }


@pytest.mark.parametrize("authorization", [None, "Bearer invalid-secret", "Basic fixture-ana"])
async def test_identity_required_for_agent_listing(authorization):
    app, _ = build_app()
    request_headers = {} if authorization is None else {"Authorization": authorization}
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app), base_url="http://test"
    ) as client:
        response = await client.get("/v1/agents", headers=request_headers)
    assert response.status_code == 401 and response.json()["error"]["code"] == "no_autenticado"
    assert "invalid-secret" not in response.text


async def test_agents_and_sessions_enforce_server_identity_and_scope():
    app, _ = build_app()
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app), base_url="http://test"
    ) as client:
        response = await client.get("/v1/agents", headers=headers())
        assert [agent["id"] for agent in response.json()["agents"]] == ["costs"]
        denied = await client.post(
            "/v1/sessions", headers=headers(), json={"agent_id": "contracts"}
        )
        assert denied.status_code == 403
        created = await client.post("/v1/sessions", headers=headers(), json={"agent_id": "costs"})
        assert created.status_code == 201
        session = created.json()
        assert session["principal_id"] == "ana"
        other = await client.get(f"/v1/sessions/{session['id']}", headers=headers("bea"))
        assert other.status_code == 403


async def test_requests_cannot_choose_identity_and_validation_does_not_echo_input():
    app, _ = build_app()
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app), base_url="http://test"
    ) as client:
        response = await client.post(
            "/v1/sessions",
            headers=headers(),
            json={
                "agent_id": "costs",
                "principal_id": "private-input-value",
            },
        )
    assert response.status_code == 422
    assert "private-input-value" not in response.text


async def test_audience_identity_is_checked_at_creation():
    app, _ = build_app()
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app), base_url="http://test"
    ) as client:
        response = await client.post(
            "/v1/sessions",
            headers=headers(),
            json={
                "agent_id": "costs",
                "audience_ids": ["bea"],
            },
        )
    assert response.status_code == 403


async def test_message_and_cancel_are_private_to_session_owner():
    app, _ = build_app()
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app), base_url="http://test"
    ) as client:
        created = await client.post("/v1/sessions", headers=headers(), json={"agent_id": "costs"})
        session_id = created.json()["id"]
        reply = await client.post(
            f"/v1/sessions/{session_id}/messages",
            headers=headers(),
            json={"text": "Analizá los datos."},
        )
        assert reply.status_code == 200 and reply.json()["text"] == "Resultado sintético."
        for path in ("messages", "cancel"):
            denied = await client.post(
                f"/v1/sessions/{session_id}/{path}",
                headers=headers("bea"),
                json={"text": "Hola"} if path == "messages" else None,
            )
            assert denied.status_code == 403
        cancelled = await client.post(f"/v1/sessions/{session_id}/cancel", headers=headers())
        assert cancelled.json() == {"cancelled": False}


async def test_missing_model_is_explicit_without_blocking_management():
    app, _ = build_app(runner=None)
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app), base_url="http://test"
    ) as client:
        created = await client.post("/v1/sessions", headers=headers(), json={"agent_id": "costs"})
        response = await client.post(
            f"/v1/sessions/{created.json()['id']}/messages",
            headers=headers(),
            json={"text": "Hola"},
        )
    assert response.status_code == 503
    assert response.json()["error"]["code"] == "modelo_no_configurado"


async def test_membership_revocation_applies_to_existing_session():
    app, service = build_app()
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app), base_url="http://test"
    ) as client:
        created = await client.post("/v1/sessions", headers=headers(), json={"agent_id": "costs"})
        service.registry.replace_principal(
            service.registry.principals["ana"].model_copy(update={"active": False})
        )
        response = await client.get(f"/v1/sessions/{created.json()['id']}", headers=headers())
    assert response.status_code == 403


async def test_unexpected_runner_exception_never_reaches_http_error_body():
    class FailingRunner:
        async def turn(self, session, text):
            raise RuntimeError("private-backend-detail")

    app, _ = build_app(runner=FailingRunner())
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app), base_url="http://test"
    ) as client:
        created = await client.post("/v1/sessions", headers=headers(), json={"agent_id": "costs"})
        response = await client.post(
            f"/v1/sessions/{created.json()['id']}/messages",
            headers=headers(),
            json={"text": "Hola"},
        )
    assert response.json()["error"]["code"] == "fallo_ejecucion"
    assert "private-backend-detail" not in response.text


def test_auth_retains_only_hashes_and_maps_environment_variables():
    auth = DevelopmentTokenAuth.from_env(
        {
            "OIF_IDENTITY_ENV_MAP": json.dumps({"ana": "OIF_TOKEN_ANA"}),
            "OIF_TOKEN_ANA": "synthetic-secret",
        }
    )
    assert auth.authenticate("Bearer synthetic-secret") == "ana"
    assert "synthetic-secret" not in repr(auth.__dict__)


@pytest.mark.parametrize(
    "mapping",
    [
        {"ana": "OPENAI_API_KEY"},
        {"ana": "OIF_MCP_TOKEN"},
        {"ana": "OIF_TOKEN_MISSING"},
    ],
)
def test_auth_environment_mapping_cannot_reuse_model_or_mcp_secrets(mapping):
    with pytest.raises(OIFError) as captured:
        DevelopmentTokenAuth.from_env(
            {
                "OIF_IDENTITY_ENV_MAP": json.dumps(mapping),
                "OPENAI_API_KEY": "synthetic-sensitive",
                "OIF_MCP_TOKEN": "synthetic-sensitive",
            }
        )
    assert "synthetic-sensitive" not in str(captured.value)


def test_duplicate_tokens_for_different_identities_are_rejected():
    with pytest.raises(OIFError):
        DevelopmentTokenAuth.from_env(
            {
                "OIF_IDENTITY_ENV_MAP": json.dumps(
                    {"ana": "OIF_TOKEN_ANA", "bea": "OIF_TOKEN_BEA"}
                ),
                "OIF_TOKEN_ANA": "synthetic-same",
                "OIF_TOKEN_BEA": "synthetic-same",
            }
        )
