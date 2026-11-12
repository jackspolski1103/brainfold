"""A bounded Streamable HTTP MCP adapter using the official MCP SDK.

Connection configuration and the credential-name allowlist are administrator inputs.
No model credential, caller header or process proxy configuration is forwarded.
"""

from __future__ import annotations

import asyncio
import ipaddress
import json
import logging
import os
import re
from collections.abc import AsyncIterator, Collection
from contextlib import asynccontextmanager
from contextvars import ContextVar
from datetime import timedelta
from typing import Any
from urllib.parse import urlsplit

import httpx
from mcp import ClientSession
from mcp.client.streamable_http import streamable_http_client
from mcp.shared.exceptions import McpError
from pydantic import ValidationError

from oif.domain import Connection, OIFError, RemoteTool

MAX_MESSAGE_BYTES = 1_048_576
MAX_TOOLS = 128
MAX_TOOL_PAGES = 16
_TOKEN_ENV_PATTERN = re.compile(r"OIF_MCP_[A-Z0-9_]+\Z")
_PRIVATE_MCP_LOGS: ContextVar[bool] = ContextVar("oif_private_mcp_logs", default=False)


class _SafeMCPLogs(logging.Filter):
    """The SDK logs remote payloads on parse failures; keep those out of application logs."""

    def filter(self, record: logging.LogRecord) -> bool:
        if _PRIVATE_MCP_LOGS.get():
            record.msg = "MCP transport diagnostic; use the classified OIF error."
            record.args = ()
            record.exc_info = None
            record.exc_text = None
            record.stack_info = None
        return True


_SAFE_LOG_FILTER = _SafeMCPLogs()
for _logger_name in ("", "mcp.client.streamable_http", "mcp.client.session", "mcp.shared.session"):
    logging.getLogger(_logger_name).addFilter(_SAFE_LOG_FILTER)


def _is_loopback(hostname: str) -> bool:
    if hostname == "localhost":
        return True
    try:
        return ipaddress.ip_address(hostname).is_loopback
    except ValueError:
        return False


class _BoundedStream(httpx.AsyncByteStream):
    def __init__(self, stream: httpx.AsyncByteStream):
        self._stream = stream

    async def __aiter__(self) -> AsyncIterator[bytes]:
        size = 0
        async for chunk in self._stream:
            size += len(chunk)
            if size > MAX_MESSAGE_BYTES:
                raise OIFError("respuesta_invalida", "La respuesta de la fuente excede el límite.")
            yield chunk

    async def aclose(self) -> None:
        await self._stream.aclose()


def _json_bytes(value: Any) -> bytes:
    try:
        encoded = json.dumps(value, ensure_ascii=False, allow_nan=False).encode("utf-8")
    except (ValueError, TypeError, OverflowError, RecursionError):
        raise OIFError(
            "respuesta_invalida", "La fuente debe intercambiar contenido JSON."
        ) from None
    if len(encoded) > MAX_MESSAGE_BYTES:
        raise OIFError("respuesta_invalida", "El contenido excede el límite permitido.")
    return encoded


def _reject_json_constant(value: str) -> Any:
    raise ValueError("Non-JSON number")


def _leaf_errors(error: Exception) -> list[Exception]:
    if isinstance(error, ExceptionGroup):
        return [leaf for nested in error.exceptions for leaf in _leaf_errors(nested)]
    return [error]


def _safe_error(error: Exception) -> OIFError:
    errors = _leaf_errors(error)
    for item in errors:
        if isinstance(item, OIFError):
            return item
    if any(isinstance(item, (TimeoutError, httpx.TimeoutException)) for item in errors):
        return OIFError("tiempo_agotado", "La fuente no respondió a tiempo.", retryable=True)
    # The SDK also represents a response timeout as the MCP request-timeout error.
    if any(isinstance(item, McpError) and item.error.code == -32001 for item in errors):
        return OIFError("tiempo_agotado", "La fuente no respondió a tiempo.", retryable=True)
    if any(
        isinstance(item, (RuntimeError, ValidationError, json.JSONDecodeError)) for item in errors
    ):
        return OIFError("respuesta_invalida", "La fuente devolvió una respuesta inválida.")
    return OIFError("fuente_no_disponible", "No se pudo consultar la fuente.", retryable=True)


class MCPTransport:
    def __init__(self, *, allowed_token_envs: Collection[str] = ()) -> None:
        self._allowed_token_envs = frozenset(allowed_token_envs)

    def _connection_headers(self, connection: Connection) -> dict[str, str]:
        try:
            parsed = urlsplit(connection.url)
            valid = (
                parsed.scheme in {"http", "https"}
                and bool(parsed.hostname)
                and (parsed.scheme == "https" or _is_loopback(parsed.hostname or ""))
                and parsed.username is None
                and parsed.password is None
                and parsed.port != 0
                and not parsed.fragment
                and not parsed.query
                and not any(char.isspace() or ord(char) < 32 for char in connection.url)
            )
        except ValueError:
            valid = False
        if not valid:
            raise OIFError(
                "configuracion_invalida", "La conexión MCP requiere una URL HTTP válida."
            )
        if connection.token_env is None:
            return {}
        name = connection.token_env
        if name not in self._allowed_token_envs or not _TOKEN_ENV_PATTERN.fullmatch(name):
            raise OIFError("configuracion_invalida", "La credencial MCP no está autorizada.")
        token = os.environ.get(name)
        if not token or len(token) > 8192 or any(not 33 <= ord(char) <= 126 for char in token):
            raise OIFError("configuracion_invalida", "La credencial MCP no está disponible.")
        return {"Authorization": f"Bearer {token}"}

    @asynccontextmanager
    async def _session(self, connection: Connection) -> AsyncIterator[tuple[ClientSession, str]]:
        headers = self._connection_headers(connection)
        credential = headers.get("Authorization", "").removeprefix("Bearer ")

        async def protect_response(response: httpx.Response) -> None:
            # SDK 1.30 follows same-origin redirects independently of follow_redirects.
            # Reject them before the SDK can issue the second authenticated request.
            if response.is_redirect:
                raise OIFError("fuente_no_disponible", "La conexión MCP no admite redirecciones.")
            if response.headers.get("content-encoding", "identity").lower() != "identity":
                raise OIFError(
                    "respuesta_invalida", "La fuente debe enviar contenido sin comprimir."
                )
            length = response.headers.get("content-length")
            if length and length.isdecimal() and int(length) > MAX_MESSAGE_BYTES:
                raise OIFError("respuesta_invalida", "La respuesta de la fuente excede el límite.")
            response.stream = _BoundedStream(response.stream)

        log_context = _PRIVATE_MCP_LOGS.set(True)
        try:
            async with asyncio.timeout(connection.timeout_seconds):
                async with httpx.AsyncClient(
                    headers={"Accept-Encoding": "identity", **headers},
                    timeout=httpx.Timeout(connection.timeout_seconds),
                    trust_env=False,
                    follow_redirects=False,
                    event_hooks={"response": [protect_response]},
                ) as client:
                    async with streamable_http_client(
                        connection.url, http_client=client
                    ) as streams:
                        async with ClientSession(
                            streams[0],
                            streams[1],
                            read_timeout_seconds=timedelta(seconds=connection.timeout_seconds),
                        ) as session:
                            await session.initialize()
                            yield session, credential
        except Exception as error:
            raise _safe_error(error) from None
        finally:
            _PRIVATE_MCP_LOGS.reset(log_context)

    @staticmethod
    def _check_content(value: Any, credential: str) -> None:
        encoded = _json_bytes(value)
        if credential and credential.encode() in encoded:
            raise OIFError("respuesta_invalida", "La fuente devolvió contenido no permitido.")

    async def list_tools(self, connection: Connection) -> list[RemoteTool]:
        async with self._session(connection) as (session, credential):
            tools: list[RemoteTool] = []
            cursor = None
            seen_cursors: set[str] = set()
            for _ in range(MAX_TOOL_PAGES):
                page = await session.list_tools(cursor=cursor)
                self._check_content(page.model_dump(mode="json"), credential)
                tools.extend(
                    RemoteTool(name=tool.name, input_schema=tool.inputSchema) for tool in page.tools
                )
                if len(tools) > MAX_TOOLS:
                    raise OIFError(
                        "respuesta_invalida", "La fuente anuncia demasiadas herramientas."
                    )
                if len({tool.name for tool in tools}) != len(tools):
                    raise OIFError(
                        "respuesta_invalida", "La fuente anuncia herramientas duplicadas."
                    )
                self._check_content([tool.model_dump(mode="json") for tool in tools], credential)
                cursor = page.nextCursor
                if cursor is None:
                    return tools
                if cursor in seen_cursors:
                    break
                seen_cursors.add(cursor)
            raise OIFError("respuesta_invalida", "El catálogo de herramientas no es válido.")

    async def call(self, connection: Connection, tool_name: str, arguments: dict[str, Any]) -> Any:
        _json_bytes(arguments)
        async with self._session(connection) as (session, credential):
            result = await session.call_tool(tool_name, arguments)
            if result.isError:
                raise OIFError(
                    "herramienta_no_disponible", "La herramienta no pudo completar la consulta."
                )
            if result.structuredContent is not None:
                data = result.structuredContent
            elif len(result.content) == 1 and result.content[0].type == "text":
                try:
                    data = json.loads(
                        result.content[0].text,
                        parse_constant=_reject_json_constant,
                    )
                except (ValueError, TypeError, RecursionError):
                    raise OIFError(
                        "respuesta_invalida", "La herramienta debe devolver JSON."
                    ) from None
            else:
                raise OIFError(
                    "respuesta_invalida", "La herramienta debe devolver JSON estructurado."
                )
            self._check_content(data, credential)
            return data
