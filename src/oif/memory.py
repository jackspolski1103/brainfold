"""Permissioned navigation of an explicit, virtual organizational repository.

Paths identify in-memory entries only. They are never passed to an operating-system
file API, decoded, resolved, expanded or followed as links. The adapter deliberately
does not choose a persistent backing store or expose a publication/write workflow.
"""

from __future__ import annotations

import threading
import unicodedata
from collections import Counter
from collections.abc import Mapping, Sequence
from typing import Any

from oif.domain import MemoryNode, OIFError, Principal

MAX_PATH_BYTES = 1024
MAX_DEPTH = 32
MAX_NODES = 2048
MAX_DIRECTORY_CHILDREN = 256
MAX_FILE_BYTES = 65_536
MAX_TOTAL_BYTES = 8_388_608

_NodeKey = tuple[str, str]
_Snapshot = Mapping[_NodeKey, MemoryNode]


def _unavailable() -> OIFError:
    # Same public error for an invalid path, wrong kind, absence or denial.
    return OIFError("ruta_no_disponible", "La ruta no está disponible.")


def _canonical(path: str) -> bool:
    if not isinstance(path, str) or not path.startswith("/"):
        return False
    if unicodedata.normalize("NFC", path) != path:
        return False
    if any(ord(character) < 32 or ord(character) == 127 for character in path):
        return False
    if "\\" in path or "%" in path or "//" in path:
        return False
    try:
        if len(path.encode("utf-8")) > MAX_PATH_BYTES:
            return False
    except UnicodeEncodeError:
        return False
    if path == "/":
        return True
    parts = path[1:].split("/")
    return len(parts) <= MAX_DEPTH and all(
        part not in {"", ".", ".."} and len(part.encode("utf-8")) <= 255 for part in parts
    )


def _parent(path: str) -> str:
    return path.rsplit("/", 1)[0] or "/"


def _ancestors(path: str) -> list[str]:
    paths = ["/"]
    if path != "/":
        current = ""
        for part in path[1:].split("/"):
            current += f"/{part}"
            paths.append(current)
    return paths


class PermissionedMemory:
    def __init__(self, nodes: Sequence[MemoryNode]) -> None:
        self._lock = threading.Lock()
        initial: dict[_NodeKey, MemoryNode] = {}
        for node in nodes:
            key = (node.organization_id, node.path)
            if key in initial:
                raise OIFError("configuracion_invalida", "La memoria contiene entradas duplicadas.")
            initial[key] = node
        self._validate_snapshot(initial)
        self._nodes = initial
        self._revision = 1

    @property
    def revision(self) -> int:
        """Global generation for service-side authorization/history revalidation."""
        with self._lock:
            return self._revision

    @staticmethod
    def _validate_snapshot(nodes: _Snapshot) -> None:
        if len(nodes) > MAX_NODES:
            raise OIFError("configuracion_invalida", "La memoria excede el límite de entradas.")
        total_bytes = 0
        children: Counter[_NodeKey] = Counter()
        for (organization_id, path), node in nodes.items():
            if (
                not organization_id
                or not _canonical(path)
                or (path == "/" and node.kind != "directory")
                or (node.kind == "directory" and node.content)
            ):
                raise OIFError(
                    "configuracion_invalida", "La memoria contiene una entrada inválida."
                )
            try:
                content_bytes = len(node.content.encode("utf-8"))
            except UnicodeEncodeError:
                raise OIFError(
                    "configuracion_invalida", "El contenido de memoria no es válido."
                ) from None
            if content_bytes > MAX_FILE_BYTES:
                raise OIFError("configuracion_invalida", "Un archivo de memoria excede el límite.")
            total_bytes += content_bytes + len(path.encode("utf-8"))
            if path != "/":
                children[(organization_id, _parent(path))] += 1
        if total_bytes > MAX_TOTAL_BYTES or any(
            count > MAX_DIRECTORY_CHILDREN for count in children.values()
        ):
            raise OIFError("configuracion_invalida", "La memoria excede los límites de capacidad.")

    def replace_node(self, node: MemoryNode) -> None:
        """Trusted configuration mutation, never an agent tool or an HTTP write endpoint.

        Copy-on-write means every read authorizes and returns data from one snapshot;
        a concurrent update cannot combine an old grant with new file content.
        """
        with self._lock:
            updated = {**self._nodes, (node.organization_id, node.path): node}
            self._validate_snapshot(updated)
            self._nodes = updated
            self._revision += 1

    def _snapshot(self) -> _Snapshot:
        with self._lock:
            return self._nodes

    @staticmethod
    def _authorized(
        nodes: _Snapshot,
        organization_id: str,
        path: str,
        principals: Sequence[Principal],
    ) -> bool:
        if not principals or any(
            not principal.active or principal.organization_id != organization_id
            for principal in principals
        ):
            return False
        for ancestor_path in _ancestors(path):
            node = nodes.get((organization_id, ancestor_path))
            if node is None or node.status != "published":
                return False
            if ancestor_path != path and node.kind != "directory":
                return False
            if ancestor_path == "/" and (
                node.allowed_projects is None and node.allowed_principals is None
            ):
                return False
            for principal in principals:
                if node.allowed_projects is not None and not (
                    node.allowed_projects & principal.project_ids
                ):
                    return False
                if (
                    node.allowed_principals is not None
                    and principal.id not in node.allowed_principals
                ):
                    return False
        return True

    async def list_directory(
        self, organization_id: str, path: str, principals: Sequence[Principal]
    ) -> list[dict[str, Any]]:
        if not _canonical(path):
            raise _unavailable()
        nodes = self._snapshot()
        node = nodes.get((organization_id, path))
        if (
            node is None
            or node.kind != "directory"
            or not self._authorized(nodes, organization_id, path, principals)
        ):
            raise _unavailable()
        # No await occurs between authorization and returning this snapshot's metadata.
        return [
            {"path": child.path, "kind": child.kind, "version": child.version}
            for child in sorted(nodes.values(), key=lambda item: item.path)
            if child.organization_id == organization_id
            and child.path != path
            and _parent(child.path) == path
            and self._authorized(nodes, organization_id, child.path, principals)
        ]

    async def read_file(
        self, organization_id: str, path: str, principals: Sequence[Principal]
    ) -> dict[str, Any]:
        if not _canonical(path):
            raise _unavailable()
        nodes = self._snapshot()
        node = nodes.get((organization_id, path))
        if (
            node is None
            or node.kind != "file"
            or not self._authorized(nodes, organization_id, path, principals)
        ):
            raise _unavailable()
        return {"path": node.path, "version": node.version, "content": node.content}
