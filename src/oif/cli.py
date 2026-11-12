"""`oif serve`: serve a folder as a shared brain (MCP for harnesses, API for the panel)."""

from __future__ import annotations

import argparse
import ipaddress
import sys
from pathlib import Path

from oif import OIFError


def _host(value: str) -> str:
    if value == "localhost":
        return value
    try:
        if ipaddress.ip_address(value).is_loopback:
            return value
    except ValueError:
        pass
    # ponytail: loopback only; put a TLS reverse proxy in front before lifting this.
    raise argparse.ArgumentTypeError("El servidor de desarrollo debe escuchar en loopback.")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="oif", description="Cerebro compartido por MCP.")
    commands = parser.add_subparsers(dest="command", required=True)
    serve = commands.add_parser("serve", help="Servir una carpeta como cerebro compartido")
    serve.add_argument("--root", type=Path, required=True)
    serve.add_argument("--db", type=Path, default=Path("oif.db"), help="Cuentas y actividad")
    serve.add_argument("--host", type=_host, default="127.0.0.1")
    serve.add_argument("--port", type=int, default=8020)
    args = parser.parse_args(argv)
    try:
        import uvicorn

        from oif.server import create_app

        app = create_app(args.root, args.db, host=args.host, port=args.port)
    except OIFError as exc:
        print(f"Error ({exc.code}): {exc.message}", file=sys.stderr)
        return 1
    except OSError:
        print("Error: la carpeta del cerebro no existe o no se puede leer.", file=sys.stderr)
        return 1
    print(f"Cerebro OIF · MCP en http://{args.host}:{args.port}/mcp · API en /api")
    uvicorn.run(app, host=args.host, port=args.port, access_log=False, log_level="warning")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
