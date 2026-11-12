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
    raise argparse.ArgumentTypeError("The server must listen on loopback.")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="oif", description="A shared brain over MCP.")
    commands = parser.add_subparsers(dest="command", required=True)
    serve = commands.add_parser("serve", help="Serve a folder as a shared brain")
    serve.add_argument("--root", type=Path, required=True)
    serve.add_argument(
        "--db", type=Path, default=Path("oif.db"), help="Accounts and activity database"
    )
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
        print("Error: the brain folder does not exist or cannot be read.", file=sys.stderr)
        return 1
    print(f"OIF brain · MCP at http://{args.host}:{args.port}/mcp · API at /api")
    uvicorn.run(app, host=args.host, port=args.port, access_log=False, log_level="warning")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
