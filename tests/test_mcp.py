from __future__ import annotations

import asyncio
import logging
import socket
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from typing import Any

import pytest
import uvicorn
from mcp.server.fastmcp import FastMCP
from starlette.applications import Starlette
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse, RedirectResponse, Response
from starlette.routing import Route

from oif.domain import Connection, OIFError
from oif.fixtures.mcp_server import create_mcp_app
from oif.mcp_client import MCPTransport


@asynccontextmanager
async def running_server(app: Starlette) -> AsyncIterator[str]:
    listener = socket.socket()
    listener.bind(("127.0.0.1", 0))
    listener.listen()
    port = listener.getsockname()[1]
    server = uvicorn.Server(uvicorn.Config(app, log_level="critical", lifespan="on"))
    task = asyncio.create_task(server.serve(sockets=[listener]))
    try:
        async with asyncio.timeout(5):
            while not server.started:
                if task.done():
                    await task
                    raise RuntimeError("Synthetic server failed to start")
                await asyncio.sleep(0.01)
        yield f"http://127.0.0.1:{port}/mcp"
    finally:
        server.should_exit = True
        try:
            async with asyncio.timeout(5):
                await task
        except TimeoutError:
            task.cancel()
            await asyncio.gather(task, return_exceptions=True)
        listener.close()


def connection(url: str, **kwargs: Any) -> Connection:
    return Connection(id="synthetic", organization_id="test", url=url, **kwargs)


async def test_real_mcp_discovery_and_project_specific_results() -> None:
    async with running_server(create_mcp_app()) as url:
        transport = MCPTransport()
        remote_tools = await transport.list_tools(connection(url))
        assert [tool.name for tool in remote_tools] == ["query_records"]
        assert "project_id" in remote_tools[0].input_schema["properties"]
        costs = await transport.call(
            connection(url), "query_records", {"project_id": "costs", "kind": "summary"}
        )
        contracts = await transport.call(
            connection(url), "query_records", {"project_id": "contracts", "kind": "summary"}
        )
        assert costs["rows"] == [{"project_id": "costs", "total": 200}]
        assert contracts["rows"] == [{"project_id": "contracts", "total": 300}]
        details = await transport.call(
            connection(url), "query_records", {"project_id": "costs", "kind": "details", "limit": 1}
        )
        assert details["count"] == 1
        assert details["truncated"] is True
        corrected = await transport.call(
            connection(url), "query_records", {"project_id": "costs", "kind": "details", "limit": 2}
        )
        assert corrected["count"] == 2
        assert corrected["truncated"] is False


@pytest.mark.parametrize("tool,kind", [("query_records", "fail"), ("missing", "summary")])
async def test_remote_failures_do_not_expose_backend_errors(tool: str, kind: str) -> None:
    async with running_server(create_mcp_app()) as url:
        with pytest.raises(OIFError) as caught:
            await MCPTransport().call(connection(url), tool, {"project_id": "costs", "kind": kind})
        assert caught.value.code == "herramienta_no_disponible"
        assert "Falla sintética" not in str(caught.value)
        assert "missing" not in str(caught.value)


@pytest.mark.parametrize(
    "url",
    [
        "stdio://executable",
        "file:///tmp/example",
        "http://example.test/mcp",
        "https://user:password@example.test/mcp",
        "https://example.test/mcp?token=secret",
        "https://example.test/mcp#secret",
    ],
)
async def test_rejects_non_http_and_embedded_credentials(url: str) -> None:
    with pytest.raises(OIFError) as caught:
        await MCPTransport().list_tools(connection(url))
    assert caught.value.code == "configuracion_invalida"
    assert "password" not in str(caught.value)


async def test_only_explicit_mcp_token_is_forwarded(monkeypatch: pytest.MonkeyPatch) -> None:
    observed: list[str | None] = []
    app = create_mcp_app()

    class CaptureHeaders(BaseHTTPMiddleware):
        async def dispatch(self, request: Request, call_next: Any) -> Response:
            observed.append(request.headers.get("authorization"))
            return await call_next(request)

    app.add_middleware(CaptureHeaders)
    monkeypatch.setenv("OPENAI_API_KEY", "model-secret-never-forward")
    monkeypatch.setenv("OIF_MCP_TEST_TOKEN", "synthetic-connection-secret")
    monkeypatch.setenv("HTTPS_PROXY", "http://127.0.0.1:1")
    monkeypatch.setenv("HTTP_PROXY", "http://127.0.0.1:1")
    monkeypatch.setenv("NO_PROXY", "")
    async with running_server(app) as url:
        transport = MCPTransport(allowed_token_envs={"OIF_MCP_TEST_TOKEN"})
        await transport.list_tools(connection(url, token_env="OIF_MCP_TEST_TOKEN"))
        assert observed and set(observed) == {"Bearer synthetic-connection-secret"}
        observed.clear()
        await transport.list_tools(connection(url))
        assert observed and set(observed) == {None}
        for env_name in ("OPENAI_API_KEY", "OIF_MCP_NOT_ALLOWED"):
            with pytest.raises(OIFError) as caught:
                await transport.list_tools(connection(url, token_env=env_name))
            assert caught.value.code == "configuracion_invalida"


async def test_redirect_is_not_followed() -> None:
    requests: list[str] = []

    async def redirect(request: Request) -> Response:
        requests.append(request.url.path)
        return RedirectResponse("/target", status_code=307)

    async def target(request: Request) -> Response:
        requests.append(request.url.path)
        return Response(status_code=500)

    app = Starlette(routes=[Route("/mcp", redirect, methods=["POST"]), Route("/target", target)])
    async with running_server(app) as url:
        with pytest.raises(OIFError):
            await MCPTransport().list_tools(connection(url))
    assert requests == ["/mcp"]


async def test_timeout_is_classified() -> None:
    async def slow(request: Request) -> Response:
        await asyncio.sleep(0.2)
        return Response(status_code=500)

    async with running_server(Starlette(routes=[Route("/mcp", slow, methods=["POST"])])) as url:
        with pytest.raises(OIFError) as caught:
            await MCPTransport().list_tools(connection(url, timeout_seconds=0.05))
    assert caught.value.code == "tiempo_agotado"
    assert caught.value.retryable is True


async def test_plain_text_result_is_rejected() -> None:
    server = FastMCP("synthetic-text", json_response=True, stateless_http=True, log_level="ERROR")

    @server.tool(structured_output=False)
    def plain_text() -> str:
        return "not JSON and not safe to trust as structured data"

    async with running_server(server.streamable_http_app()) as url:
        with pytest.raises(OIFError) as caught:
            await MCPTransport().call(connection(url), "plain_text", {})
    assert caught.value.code == "respuesta_invalida"


async def test_oversized_http_response_is_rejected() -> None:
    async def oversized(request: Request) -> Response:
        return Response("x" * 1_048_577, media_type="application/json")

    app = Starlette(routes=[Route("/mcp", oversized, methods=["POST"])])
    async with running_server(app) as url:
        with pytest.raises(OIFError) as caught:
            await MCPTransport().list_tools(connection(url))
    assert caught.value.code == "respuesta_invalida"


async def test_echoed_connection_credential_never_becomes_tool_result(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    token = "synthetic-test-credential-never-return"
    monkeypatch.setenv("OIF_MCP_TEST_TOKEN", token)
    server = FastMCP("synthetic-echo", json_response=True, stateless_http=True, log_level="ERROR")

    @server.tool()
    def echo() -> dict[str, str]:
        return {"echo": token}

    async with running_server(server.streamable_http_app()) as url:
        with pytest.raises(OIFError) as caught:
            await MCPTransport(allowed_token_envs={"OIF_MCP_TEST_TOKEN"}).call(
                connection(url, token_env="OIF_MCP_TEST_TOKEN"), "echo", {}
            )
    assert caught.value.code == "respuesta_invalida"
    assert token not in str(caught.value)


async def test_malformed_remote_payload_is_not_logged(
    caplog: pytest.LogCaptureFixture, capsys: pytest.CaptureFixture[str]
) -> None:
    sentinel = "synthetic-remote-value-never-log"

    async def malformed(request: Request) -> Response:
        message = await request.json()
        return JSONResponse({"jsonrpc": "2.0", "id": message["id"], "result": {"secret": sentinel}})

    caplog.set_level(logging.WARNING)
    async with running_server(
        Starlette(routes=[Route("/mcp", malformed, methods=["POST"])])
    ) as url:
        with pytest.raises(OIFError) as caught:
            await MCPTransport().list_tools(connection(url, timeout_seconds=0.5))
    assert sentinel not in str(caught.value)
    assert sentinel not in caplog.text
    captured = capsys.readouterr()
    assert sentinel not in captured.out + captured.err
