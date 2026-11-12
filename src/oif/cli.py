"""Terminal client for a shared OIF service; credentials never become command arguments."""

from __future__ import annotations

import argparse
import asyncio
import getpass
import ipaddress
import json
import os
import sys
import warnings
from pathlib import Path
from typing import Any
from urllib.parse import urlsplit

import httpx

from oif.domain import OIFError


def _host(value: str) -> str:
    if value == "localhost":
        return value
    try:
        if ipaddress.ip_address(value).is_loopback:
            return value
    except ValueError:
        pass
    raise argparse.ArgumentTypeError("El servicio de desarrollo debe escuchar en loopback.")


def _server(value: str) -> str:
    try:
        url = urlsplit(value)
        if (
            url.scheme not in {"http", "https"}
            or not url.hostname
            or url.username is not None
            or url.password is not None
            or url.query
            or url.fragment
        ):
            raise ValueError
        if url.scheme == "http":
            try:
                local = ipaddress.ip_address(url.hostname).is_loopback
            except ValueError:
                local = url.hostname == "localhost"
            if not local:
                raise ValueError
        _ = url.port
    except ValueError:
        raise argparse.ArgumentTypeError(
            "Usá una URL HTTPS sin credenciales, o HTTP en loopback para desarrollo."
        ) from None
    return value.rstrip("/") + "/"


def parser() -> argparse.ArgumentParser:
    result = argparse.ArgumentParser(prog="oif", description="Agentes conectados al servicio OIF.")
    commands = result.add_subparsers(dest="command", required=True)
    serve = commands.add_parser("serve", help="Iniciar el servicio compartido de desarrollo")
    serve.add_argument("--config", type=Path, required=True)
    serve.add_argument("--host", type=_host, default="127.0.0.1")
    serve.add_argument("--port", type=int, default=8765)
    for name, help_text in (
        ("chat", "Conversar con un agente del servicio"),
        ("run", "Enviar una tarea al servicio"),
    ):
        command = commands.add_parser(name, help=help_text)
        command.add_argument("--server", type=_server, required=True)
        command.add_argument("--agent", required=True)
        command.add_argument(
            "--session", help="Retomar una sesión propia conservada por el servicio"
        )
        if name == "run":
            command.add_argument("text", help="Tarea a enviar")
    commands.add_parser(
        "verify-example", help="Verificar el caso sintético, sin modelo ni credenciales"
    )
    example = commands.add_parser(
        "example-mcp", help="Servidor MCP del caso sintético de desarrollo"
    )
    example.add_argument("--host", type=_host, default="127.0.0.1")
    example.add_argument("--port", type=int, default=8011)
    return result


def _request(client: httpx.Client, method: str, path: str, **kwargs: Any) -> dict[str, Any]:
    try:
        response = client.request(method, path.lstrip("/"), **kwargs)
    except httpx.TimeoutException:
        raise OIFError(
            "servicio_tiempo_agotado",
            "El servicio no respondió a tiempo. Revisá la sesión antes de repetir la tarea.",
            retryable=True,
        ) from None
    except httpx.HTTPError:
        raise OIFError("servicio_no_disponible", "No se pudo conectar con el servicio.") from None
    if not response.is_success:
        # Neither proxy bodies nor upstream/provider diagnostics are safe terminal output.
        if response.status_code == 401:
            raise OIFError("no_autenticado", "El servicio rechazó el token de acceso.")
        if response.status_code in {403, 404}:
            raise OIFError(
                "acceso_denegado", "El recurso no existe o no tenés permiso para usarlo."
            )
        if response.status_code == 409:
            raise OIFError(
                "turno_interrumpido",
                "El turno se interrumpió o cambió el contexto. "
                "Revisá la sesión antes de repetirlo.",
            )
        if response.status_code == 503:
            raise OIFError(
                "servicio_no_disponible",
                "El servicio no pudo completar la tarea. Revisá la configuración del modelo "
                "y las conexiones en el servidor.",
            )
        raise OIFError("servicio_error", "El servicio no pudo completar la solicitud.")
    try:
        data = response.json()
        if not isinstance(data, dict):
            raise ValueError
        return data
    except ValueError:
        raise OIFError(
            "respuesta_invalida", "El servicio devolvió una respuesta inválida."
        ) from None


def _session(client: httpx.Client, args: argparse.Namespace) -> str:
    if args.session:
        result = _request(client, "GET", f"v1/sessions/{args.session}")
        if result.get("agent_id") != args.agent:
            raise OIFError("agente_distinto", "La sesión pertenece a otro agente.")
    else:
        result = _request(
            client, "POST", "v1/sessions", json={"agent_id": args.agent, "audience_ids": []}
        )
    identifier = result.get("id")
    if not isinstance(identifier, str) or not identifier:
        raise OIFError("respuesta_invalida", "El servicio no identificó la sesión.")
    return identifier


def _cancel(client: httpx.Client, session_id: str) -> None:
    try:
        _request(client, "POST", f"v1/sessions/{session_id}/cancel", timeout=5)
    except OIFError:
        print("No pude confirmar la cancelación; revisá el estado de la sesión.", file=sys.stderr)


def _reply(client: httpx.Client, session_id: str, text: str) -> str:
    try:
        result = _request(client, "POST", f"v1/sessions/{session_id}/messages", json={"text": text})
    except KeyboardInterrupt:
        _cancel(client, session_id)
        raise
    answer = result.get("text")
    if not isinstance(answer, str):
        raise OIFError("respuesta_invalida", "El servicio no devolvió texto de respuesta.")
    return answer


def _conversation(args: argparse.Namespace) -> int:
    token = os.environ.get("OIF_ACCESS_TOKEN", "").strip()
    if not token:
        try:
            with warnings.catch_warnings():
                # Reject getpass's fallback to echoed input when no terminal is available.
                warnings.simplefilter("error", getpass.GetPassWarning)
                token = getpass.getpass("Token de acceso al servicio (entrada oculta): ").strip()
        except (EOFError, getpass.GetPassWarning):
            raise OIFError(
                "token_ausente", "Configurá OIF_ACCESS_TOKEN o ingresalo de forma oculta."
            ) from None
    if not token:
        raise OIFError("token_ausente", "No se ingresó un token de acceso.")
    with httpx.Client(
        base_url=args.server,
        headers={"Authorization": f"Bearer {token}"},
        timeout=150,
        follow_redirects=False,
        trust_env=False,
    ) as client:
        health = _request(client, "GET", "health")
        session_id = _session(client, args)
        if args.command == "run":
            print(_reply(client, session_id, args.text))
            print(f"Sesión: {session_id}", file=sys.stderr)
            return 0
        model = health.get("model") or "sin modelo configurado"
        provider = health.get("model_provider") or "según configuración del servicio"
        print(f"OIF · agente {args.agent} · servicio {args.server.rstrip('/')}")
        print(f"Modelo: {model} · destino de inferencia: {provider}")
        print(f"Contexto compartido autorizado · conversación privada · sesión {session_id}")
        print("El historial se conserva en memoria del servidor. Para terminar, Ctrl+D o Ctrl+C.")
        while True:
            try:
                text = input("\n> ")
            except EOFError:
                print()
                return 0
            if not text.strip():
                continue
            try:
                print(_reply(client, session_id, text))
            except OIFError as exc:
                print(f"Error ({exc.code}): {exc.message}", file=sys.stderr)


def main(argv: list[str] | None = None) -> int:
    args = parser().parse_args(argv)
    try:
        if args.command in {"serve", "example-mcp"}:
            if not 1 <= args.port <= 65535:
                raise OIFError("puerto_invalido", "El puerto debe estar entre 1 y 65535.")
            import uvicorn

            if args.command == "serve":
                from oif.bootstrap import build_service_app

                app = build_service_app(args.config)
                print(f"Servicio OIF de desarrollo · {args.host}:{args.port}")
                print("Autenticación por tokens de desarrollo; sesiones conservadas en memoria.")
            else:
                from oif.fixtures.mcp_server import create_mcp_app

                app = create_mcp_app(host=args.host, port=args.port)
                print(f"Servidor MCP sintético de desarrollo · {args.host}:{args.port}")
            uvicorn.run(app, host=args.host, port=args.port, access_log=False, log_level="warning")
            return 0
        if args.command == "verify-example":
            from oif.verification import verify_example

            print(json.dumps(asyncio.run(verify_example()), ensure_ascii=False, indent=2))
            return 0
        return _conversation(args)
    except OIFError as exc:
        print(f"Error ({exc.code}): {exc.message}", file=sys.stderr)
        return 1
    except KeyboardInterrupt:
        print(
            "\nConversación terminada. Las operaciones completadas no se deshacen.", file=sys.stderr
        )
        return 130
    except Exception:
        print(
            "No se pudo completar la operación. Revisá la configuración del servicio.",
            file=sys.stderr,
        )
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
