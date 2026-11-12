"""Shared brain: real folders and files with per-folder permissions.

Each folder may carry a `.oif.toml` with `description`, `start_here`, `read` and `write`.
Grants are member emails, `@group` or `*`. Read is intersected down the tree and denied
unless some ancestor grants it; write follows the nearest folder that declares it and is
denied by default. Dot-entries (metadata, `.git`) and symlinks are never visible to or
writable by an agent.
"""

from __future__ import annotations

import json
import os
import re
import subprocess
import tomllib
import unicodedata
from collections.abc import Callable, Mapping, Sequence
from pathlib import Path
from typing import Any

from oif import OIFError

GRANT = re.compile(r"\*|@[a-z0-9][a-z0-9_-]{0,62}|[^@\s]+@[^@\s]+")
MAX_PATH_BYTES = 1024
MAX_DEPTH = 32
MAX_DIRECTORY_CHILDREN = 256
MAX_FILE_BYTES = 65_536
MAX_SEARCH_HITS = 50


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


class Brain:
    def __init__(self, root: Path, groups: Callable[[], Mapping[str, Sequence[str]]]) -> None:
        self.groups = groups
        self.root = root.resolve(strict=True)
        if not self.root.is_dir():
            raise OIFError("configuracion_invalida", "La raíz del cerebro no es una carpeta.")

    def _real(self, path: str) -> Path:
        if not _canonical(path):
            raise _unavailable()
        parts = [part for part in path.split("/") if part]
        if any(part.startswith(".") for part in parts):
            raise _unavailable()
        target = self.root.joinpath(*parts)
        if target.resolve() != target:  # a symlink anywhere on the way
            raise _unavailable()
        return target

    @staticmethod
    def _meta(directory: Path) -> dict[str, Any]:
        try:
            return tomllib.loads((directory / ".oif.toml").read_text("utf-8"))
        except FileNotFoundError:
            return {}
        except (OSError, ValueError):  # unreadable or malformed metadata fails closed
            raise _unavailable() from None

    def _granted(self, who: str, grants: Any) -> bool:
        if not isinstance(grants, list):
            raise _unavailable()
        return (
            "*" in grants
            or who in grants
            or any(
                who in members for name, members in self.groups().items() if f"@{name}" in grants
            )
        )

    def _access(self, who: str, target: Path) -> tuple[bool, bool]:
        """Return (read, write) for a path already checked by `_real`."""
        folders = [self.root]
        for part in target.relative_to(self.root).parts:
            if (folders[-1] / part).is_dir():
                folders.append(folders[-1] / part)
        read = write = False
        for folder in folders:
            meta = self._meta(folder)
            if "read" in meta:
                if not self._granted(who, meta["read"]):
                    return False, False
                read = True
            if "write" in meta:
                write = self._granted(who, meta["write"])
        return read, read and write

    def list(self, who: str, path: str, manage: bool = False) -> dict[str, Any]:
        """`manage` shows an administrator every folder and its grants, not file content."""
        target = self._real(path)
        read, write = self._access(who, target)
        if not (read or manage) or not target.is_dir():
            raise _unavailable()
        meta = self._meta(target)
        entries: list[dict[str, Any]] = []
        for child in sorted(target.iterdir()):
            child_path = f"{path.rstrip('/')}/{child.name}"
            try:
                real = self._real(child_path)
                if child.is_symlink() or not (manage or self._access(who, real)[0]):
                    continue
                entry = {"path": child_path, "kind": "directory" if child.is_dir() else "file"}
                if child.is_dir():
                    child_meta = self._meta(child)
                    if description := child_meta.get("description"):
                        entry["description"] = description
                    if manage:
                        entry |= {"read": child_meta.get("read"), "write": child_meta.get("write")}
            except OIFError:
                continue
            entries.append(entry)
        return {
            **({"read": meta.get("read"), "write": meta.get("write")} if manage else {}),
            "path": path,
            "description": meta.get("description", ""),
            "start_here": meta.get("start_here", []),
            "can_write": write,
            "entries": entries[:MAX_DIRECTORY_CHILDREN],
            "truncated": len(entries) > MAX_DIRECTORY_CHILDREN,
        }

    def read(self, who: str, path: str) -> dict[str, Any]:
        target = self._real(path)
        if not self._access(who, target)[0] or not target.is_file():
            raise _unavailable()
        try:
            if target.stat().st_size > MAX_FILE_BYTES:
                raise OIFError("archivo_demasiado_grande", "El archivo excede el límite.")
            return {"path": path, "content": target.read_text("utf-8")}
        except (OSError, UnicodeDecodeError):
            raise _unavailable() from None

    def write(self, who: str, path: str, content: str) -> dict[str, Any]:
        target = self._real(path)
        read, write = self._access(who, target)
        if not read or target == self.root or target.is_dir():
            raise _unavailable()
        if not write:
            raise OIFError("sin_permiso_escritura", "No tenés permiso de escritura en esta ruta.")
        try:
            data = content.encode("utf-8")
        except UnicodeEncodeError:
            raise OIFError("contenido_invalido", "El contenido no es texto válido.") from None
        if len(data) > MAX_FILE_BYTES:
            raise OIFError("archivo_demasiado_grande", "El contenido excede el límite.")
        target.parent.mkdir(parents=True, exist_ok=True)
        # ponytail: last write wins; add an expected-version check when edits collide.
        temporary = target.with_name(f".{target.name}.tmp")
        temporary.write_bytes(data)
        os.replace(temporary, target)
        return {"path": path, "versioned": self._commit(who, target)}

    def set_meta(
        self,
        who: str,
        path: str,
        description: str,
        start_here: list[str],
        read: list[str] | None,
        write: list[str] | None,
    ) -> dict[str, Any]:
        """Trusted administrator operation; `None` means the folder inherits."""
        target = self._real(path)
        if not target.is_dir():
            raise _unavailable()
        meta: dict[str, Any] = {"description": description, "start_here": start_here}
        meta |= {
            key: value for key, value in (("read", read), ("write", write)) if value is not None
        }
        grants = [*(read or []), *(write or [])]
        if (
            not isinstance(description, str)
            or not all(isinstance(item, str) and _canonical(item) for item in start_here)
            or not all(isinstance(item, str) and GRANT.fullmatch(item) for item in grants)
        ):
            raise OIFError("metadata_invalida", "La descripción o los accesos no son válidos.")
        # ponytail: only the four known keys are kept; extend when the format grows.
        text = "".join(
            f"{key} = {json.dumps(value, ensure_ascii=False)}\n" for key, value in meta.items()
        )
        try:
            if tomllib.loads(text) != meta:
                raise ValueError
        except ValueError:
            raise OIFError("metadata_invalida", "La descripción no es válida.") from None
        temporary = target / ".oif.toml.tmp"
        temporary.write_text(text, "utf-8")
        os.replace(temporary, target / ".oif.toml")
        return {"path": path, "versioned": self._commit(who, target / ".oif.toml")}

    def _commit(self, who: str, target: Path) -> bool:
        """History comes from git when the brain root is its own repository."""
        if not (self.root / ".git").exists():
            return False
        relative = str(target.relative_to(self.root))
        git = ["git", "-C", str(self.root), "-c", f"user.name={who}"]
        git += ["-c", f"user.email={who}"]
        # ponytail: blocking subprocess per write; queue commits if write volume matters.
        steps = (["add", "--", relative], ["commit", "-q", "-m", f"{who}: {relative}"])
        return all(
            subprocess.run([*git, *step], capture_output=True, check=False).returncode == 0
            for step in steps
        )

    def search(self, who: str, query: str, path: str = "/") -> dict[str, Any]:
        needle = query.casefold().strip()
        if not needle:
            raise OIFError("busqueda_vacia", "Indicá un texto para buscar.")
        hits: list[dict[str, Any]] = []
        pending = [path]
        # ponytail: linear scan of readable files; add an index when the brain grows.
        while pending and len(hits) <= MAX_SEARCH_HITS:
            for entry in self.list(who, pending.pop())["entries"]:
                if entry["kind"] == "directory":
                    pending.append(entry["path"])
                    continue
                try:
                    lines = self.read(who, entry["path"])["content"].splitlines()
                except OIFError:
                    continue
                hits += [
                    {"path": entry["path"], "line": number, "text": line.strip()[:200]}
                    for number, line in enumerate(lines, 1)
                    if needle in line.casefold()
                ]
        return {"hits": hits[:MAX_SEARCH_HITS], "truncated": len(hits) > MAX_SEARCH_HITS}

    def skills(self, who: str) -> dict[str, Any]:
        """Every readable SKILL.md with the name and description of its front matter."""
        found: list[dict[str, Any]] = []
        pending = ["/"]
        # ponytail: walks the readable tree on each call; cache when brains get large.
        while pending and len(found) < MAX_DIRECTORY_CHILDREN:
            for entry in self.list(who, pending.pop())["entries"]:
                if entry["kind"] == "directory":
                    pending.append(entry["path"])
                elif entry["path"].endswith("/SKILL.md"):
                    try:
                        lines = self.read(who, entry["path"])["content"].splitlines()[:20]
                    except OIFError:
                        continue
                    fields = dict(line.split(":", 1) for line in lines if ":" in line)
                    found.append(
                        {
                            "path": entry["path"],
                            "name": fields.get("name", entry["path"].split("/")[-2]).strip(),
                            "description": fields.get("description", "").strip(),
                        }
                    )
        return {"skills": sorted(found, key=lambda skill: skill["path"])}
