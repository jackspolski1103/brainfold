"""An interoperable MCP server backed only by deterministic synthetic records."""

from __future__ import annotations

from typing import Any, Literal

from mcp.server.fastmcp import FastMCP
from mcp.types import ToolAnnotations
from starlette.applications import Starlette

_RECORDS: dict[str, list[dict[str, Any]]] = {
    "costs": [
        {"id": "synthetic-cost-1", "category": "materials", "amount": 120},
        {"id": "synthetic-cost-2", "category": "transport", "amount": 80},
    ],
    "contracts": [
        {"id": "synthetic-contract-1", "category": "service", "amount": 240},
        {"id": "synthetic-contract-2", "category": "maintenance", "amount": 60},
    ],
}


def create_mcp_app(host: str = "127.0.0.1", port: int = 8766) -> Starlette:
    """Return a real MCP /mcp ASGI app, including its session-manager lifespan."""
    server = FastMCP(
        "OIF synthetic records",
        host=host,
        port=port,
        log_level="ERROR",
        json_response=True,
        stateless_http=True,
        streamable_http_path="/mcp",
    )

    @server.tool(
        annotations=ToolAnnotations(readOnlyHint=True, destructiveHint=False, openWorldHint=False)
    )
    def query_records(
        project_id: str,
        kind: Literal["summary", "details", "fail"] = "summary",
        limit: int = 10,
    ) -> dict[str, Any]:
        """Query synthetic costs or contracts; no real client or organization data."""
        if project_id not in _RECORDS:
            raise ValueError("Proyecto sintético no disponible.")
        if not 1 <= limit <= 100:
            raise ValueError("El límite sintético debe estar entre 1 y 100.")
        if kind == "fail":
            raise ValueError("Falla sintética solicitada.")
        records = _RECORDS[project_id]
        if kind == "summary":
            rows = [{"project_id": project_id, "total": sum(row["amount"] for row in records)}]
        else:
            rows = [dict(row) for row in records[:limit]]
        return {
            "rows": rows,
            "count": len(rows),
            "truncated": kind == "details" and len(records) > limit,
            "currency": "ARS",
            "source": "synthetic",
        }

    return server.streamable_http_app()
