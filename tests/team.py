"""A real server on a local port with a whole team connected: for the multi-user tests.

Each `Person` holds what a real teammate holds: a panel session (cookie) and a harness
token (Bearer). Requests travel over HTTP, so simultaneous calls from several threads
reach the server the way several people and agents would.
"""

from __future__ import annotations

import json
import socket
import threading
import time
from collections.abc import Callable, Iterator
from concurrent.futures import ThreadPoolExecutor
from contextlib import contextmanager
from pathlib import Path
from typing import Any

import httpx
import uvicorn

from brainfold.server import create_app

PASSWORD = "a-long-password"
ADMIN = "admin@atlas.test"


class Person:
    def __init__(self, base: str, email: str) -> None:
        self.email = email
        self.panel = httpx.Client(base_url=base, timeout=60)  # keeps the session cookie
        self.agent = httpx.Client(base_url=base, timeout=60)  # sends only the token
        self.token = ""

    def connect(self, name: str = "harness", manage: bool = False) -> str:
        """Create a harness token in the panel, as a person does in Connect."""
        body = {"name": name, "manage": manage}
        self.token = self.panel.post("/api/tokens", json=body).json()["token"]
        self.agent.headers["Authorization"] = f"Bearer {self.token}"
        return self.token

    def tree(self, path: str = "/") -> httpx.Response:
        return self.panel.get("/api/tree", params={"path": path})

    def file(self, path: str) -> httpx.Response:
        return self.panel.get("/api/file", params={"path": path})

    def download(self, path: str) -> httpx.Response:
        return self.panel.get("/api/files", params={"path": path})

    def upload(self, path: str, data: bytes, version: str | None = None) -> httpx.Response:
        headers = {"Content-Type": "application/octet-stream"}
        if version:
            headers["If-Match"] = f'"{version}"'
        return self.panel.put("/api/files", params={"path": path}, content=data, headers=headers)

    def tool(self, name: str, /, **arguments: Any) -> tuple[str, Any]:
        """Call one MCP tool as this person's agent. Returns ("ok", result) or the error
        code and its text, which is all an agent receives of a failure."""
        response = self.agent.post(
            "/mcp",
            json={
                "jsonrpc": "2.0",
                "id": 1,
                "method": "tools/call",
                "params": {"name": name, "arguments": arguments},
            },
            headers={"Accept": "application/json, text/event-stream"},
        )
        assert response.status_code == 200, response.text
        result = response.json()["result"]
        text = result["content"][0]["text"]
        if result.get("isError"):
            # "Error executing tool read: unavailable: The path is not available."
            return text.split(": ")[1] if text.count(": ") > 1 else text, text
        return "ok", json.loads(text)


class Team:
    def __init__(self, base: str, root: Path, app: Any) -> None:
        self.base, self.root, self.app = base, root, app
        self.admin = Person(base, ADMIN)
        setup = self.admin.panel.post("/api/setup", json={"email": ADMIN, "password": PASSWORD})
        assert setup.status_code == 200, setup.text
        self.admin.connect()

    def invite(self, email: str, role: str = "member") -> str:
        response = self.admin.panel.post("/api/users", json={"email": email, "role": role})
        assert response.status_code == 200, response.text
        return response.json()["invite"]

    def join(self, email: str, role: str = "member") -> Person:
        person = Person(self.base, email)
        accepted = person.panel.post(
            "/api/accept", json={"invite": self.invite(email, role), "password": PASSWORD}
        )
        assert accepted.status_code == 200, accepted.text
        person.connect()
        return person

    def login(self, email: str, password: str = PASSWORD) -> Person:
        person = Person(self.base, email)
        response = person.panel.post("/api/login", json={"email": email, "password": password})
        assert response.status_code == 200, response.text
        return person

    def group(self, name: str, *members: Person | str) -> httpx.Response:
        emails = [member if isinstance(member, str) else member.email for member in members]
        return self.admin.panel.put(f"/api/groups/{name}", json={"members": emails})

    def access(
        self,
        path: str,
        read: list[str] | None = None,
        write: list[str] | None = None,
        description: str = "",
    ) -> httpx.Response:
        body = {"path": path, "description": description, "read": read, "write": write}
        return self.admin.panel.put("/api/folder", json=body)

    def health(self) -> dict[str, Any]:
        return self.admin.panel.get("/api/health").json()


@contextmanager
def serving(root: Path, database: Path) -> Iterator[Team]:
    root.mkdir(parents=True, exist_ok=True)
    app = create_app(root, database)
    listener = socket.socket()
    listener.bind(("127.0.0.1", 0))
    listener.listen(128)
    # Idle connections stay open for the whole test: with uvicorn's 5 seconds, a slow
    # machine closes a person's connection just as their next request reuses it.
    config = uvicorn.Config(app, log_level="critical", lifespan="on", timeout_keep_alive=300)
    server = uvicorn.Server(config)
    thread = threading.Thread(target=server.run, kwargs={"sockets": [listener]}, daemon=True)
    thread.start()
    deadline = time.time() + 10
    while not server.started:
        assert time.time() < deadline, "the server did not start"
        time.sleep(0.01)
    try:
        yield Team(f"http://127.0.0.1:{listener.getsockname()[1]}", root, app)
    finally:
        server.should_exit = True
        thread.join(10)


def together(*calls: Callable[[], Any]) -> list[Any]:
    """Run every call at the same instant, each on its own thread, and return the answers
    in order. A barrier holds them all until the last one is ready."""
    barrier = threading.Barrier(len(calls))

    def run(call: Callable[[], Any]) -> Any:
        barrier.wait(10)
        return call()

    with ThreadPoolExecutor(len(calls)) as pool:
        return [future.result(120) for future in [pool.submit(run, call) for call in calls]]
