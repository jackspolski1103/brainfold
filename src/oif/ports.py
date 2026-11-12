"""The core depends on these contracts rather than a model or tool provider."""

from __future__ import annotations

from collections.abc import Sequence
from typing import Any, Protocol

from oif.domain import Connection, Message, ModelTurn, Principal, RemoteTool, ToolDescription


class ModelPort(Protocol):
    async def complete(
        self, messages: Sequence[Message], tools: Sequence[ToolDescription]
    ) -> ModelTurn: ...


class ToolTransport(Protocol):
    async def list_tools(self, connection: Connection) -> list[RemoteTool]: ...

    async def call(
        self, connection: Connection, tool_name: str, arguments: dict[str, Any]
    ) -> Any: ...


class MemoryPort(Protocol):
    @property
    def revision(self) -> int: ...

    async def list_directory(
        self, organization_id: str, path: str, principals: Sequence[Principal]
    ) -> list[dict[str, Any]]: ...

    async def read_file(
        self, organization_id: str, path: str, principals: Sequence[Principal]
    ) -> dict[str, Any]: ...
