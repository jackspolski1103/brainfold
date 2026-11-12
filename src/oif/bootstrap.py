"""Compose adapters explicitly; configuration never contains credential values."""

from __future__ import annotations

import os
from pathlib import Path

from oif.domain import Configuration, OIFError


def load_configuration(path: str | Path) -> Configuration:
    try:
        return Configuration.model_validate_json(Path(path).read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        raise OIFError(
            "configuracion_invalida", "No se pudo cargar el manifiesto de configuración."
        ) from exc


def build_service_app(config_path: str | Path):
    """Development composition, with server-side auth and no standalone CLI mode."""
    from oif.api import create_app
    from oif.auth import DevelopmentTokenAuth
    from oif.mcp_client import MCPTransport
    from oif.memory import PermissionedMemory
    from oif.models import OpenAIResponsesModel
    from oif.registry import Registry
    from oif.runtime import AgentRunner
    from oif.service import SharedService

    config = load_configuration(config_path)
    registry = Registry(config)
    allowed_envs = tuple(
        name.strip() for name in os.environ.get("OIF_MCP_TOKEN_ENVS", "").split(",") if name.strip()
    )
    service = SharedService(
        registry,
        MCPTransport(allowed_token_envs=allowed_envs),
        PermissionedMemory(config.memory_nodes),
    )
    model_name = os.environ.get("OIF_OPENAI_MODEL", "").strip()
    api_key = os.environ.get("OPENAI_API_KEY", "").strip()
    model = (
        OpenAIResponsesModel(model=model_name, api_key=api_key) if model_name and api_key else None
    )
    runner = AgentRunner(service, model) if model is not None else None
    auth = DevelopmentTokenAuth.from_env()
    return create_app(
        service,
        runner,
        auth,
        model=model_name if model is not None else None,
        model_provider="openai" if model_name and api_key else None,
    )
