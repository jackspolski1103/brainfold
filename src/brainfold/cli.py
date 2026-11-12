"""`brainfold serve` runs the server; `brainfold put` and `get` move files of any type."""

from __future__ import annotations

import argparse
import ipaddress
import json
import os
import stat
import sys
import tomllib
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

from brainfold import BrainfoldError

CONFIG = Path.home() / ".config" / "brainfold" / "config.toml"


def _loopback(host: str) -> bool:
    if host == "localhost":
        return True
    try:
        return ipaddress.ip_address(host).is_loopback
    except ValueError:
        return False


def _connection() -> tuple[str, str]:
    """Server URL and token from the environment or a private config file. They are
    never accepted as arguments and never printed."""
    url, token = os.environ.get("BRAINFOLD_URL"), os.environ.get("BRAINFOLD_TOKEN")
    if not (url and token) and CONFIG.is_file():
        if stat.S_IMODE(CONFIG.stat().st_mode) & 0o077:
            raise BrainfoldError("invalid_configuration", f"{CONFIG} must have mode 0600.")
        config = tomllib.loads(CONFIG.read_text("utf-8"))
        url, token = url or config.get("url"), token or config.get("token")
    if not (url and token):
        raise BrainfoldError(
            "invalid_configuration",
            f"Set BRAINFOLD_URL and BRAINFOLD_TOKEN, or write them to {CONFIG}.",
        )
    parsed = urllib.parse.urlsplit(url)
    if parsed.scheme != "https" and not (
        parsed.scheme == "http" and _loopback(parsed.hostname or "")
    ):
        raise BrainfoldError(
            "invalid_configuration", "BRAINFOLD_URL must be https, or http on loopback."
        )
    return url.rstrip("/"), token


def _request(method: str, path: str, data: bytes | None = None, version: str | None = None):
    url, token = _connection()
    headers = {"Authorization": f"Bearer {token}"}
    if version:
        headers["If-Match"] = f'"{version}"'
    request = urllib.request.Request(
        f"{url}/files{urllib.parse.quote(path)}", data=data, method=method, headers=headers
    )
    try:
        return urllib.request.urlopen(request)  # noqa: S310 - scheme checked in _connection
    except urllib.error.HTTPError as error:
        try:
            detail = json.load(error)["error"]
        except (ValueError, KeyError):
            detail = {"code": "request_failed", "message": f"The server answered {error.code}."}
        raise BrainfoldError(detail["code"], detail["message"]) from None
    except urllib.error.URLError:
        raise BrainfoldError("request_failed", "The server could not be reached.") from None


def _put(source: Path, path: str, replace: bool) -> None:
    version = None
    if replace:
        try:
            version = _request("GET", path).headers["ETag"].strip('"')
        except BrainfoldError as error:
            if error.code != "unavailable":
                raise
    result = json.load(_request("PUT", path, source.read_bytes(), version))
    print(f"Stored {result['path']} ({result['size']} bytes, version {result['version'][:12]}).")


def _get(path: str, destination: Path) -> None:
    data = _request("GET", path).read()
    destination.write_bytes(data)
    print(f"Saved {path} to {destination} ({len(data)} bytes).")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="brainfold", description="A shared brain over MCP.")
    commands = parser.add_subparsers(dest="command", required=True)
    serve = commands.add_parser("serve", help="Serve a folder as a shared brain")
    serve.add_argument("--root", type=Path, required=True)
    serve.add_argument("--db", type=Path, default=Path("brainfold.db"), help="Accounts database")
    serve.add_argument("--host", default="127.0.0.1")
    serve.add_argument(
        "--public-url",
        help="https address of the TLS proxy in front of the server; required to listen "
        "beyond loopback",
    )
    serve.add_argument("--port", type=int, default=8020)
    put = commands.add_parser("put", help="Upload a file of any type to the brain")
    put.add_argument("file", type=Path)
    put.add_argument("path", help="Destination in the brain, for example /hr/salaries.xlsx")
    put.add_argument("--replace", action="store_true", help="Replace the file if it exists")
    get = commands.add_parser("get", help="Download a file from the brain")
    get.add_argument("path")
    get.add_argument("destination", type=Path)
    args = parser.parse_args(argv)
    try:
        if args.command == "put":
            _put(args.file, args.path, args.replace)
            return 0
        if args.command == "get":
            _get(args.path, args.destination)
            return 0
        import uvicorn

        from brainfold.server import create_app

        public = args.public_url
        if public and urllib.parse.urlsplit(public).scheme != "https":
            raise BrainfoldError("invalid_configuration", "--public-url must start with https://")
        if not public and not _loopback(args.host):
            raise BrainfoldError(
                "invalid_configuration",
                "Listening beyond loopback needs --public-url: run the server behind a proxy "
                "that terminates TLS.",
            )
        app = create_app(args.root, args.db, host=args.host, port=args.port, public_url=public)
    except BrainfoldError as exc:
        print(f"Error ({exc.code}): {exc.message}", file=sys.stderr)
        return 1
    except OSError:
        print("Error: a file or folder does not exist or cannot be read.", file=sys.stderr)
        return 1
    print(f"Brainfold · MCP at http://{args.host}:{args.port}/mcp · API at /api", flush=True)
    if app.state.setup_code:
        print(f"Setup code for the first account: {app.state.setup_code}", flush=True)
    uvicorn.run(app, host=args.host, port=args.port, access_log=False, log_level="warning")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
