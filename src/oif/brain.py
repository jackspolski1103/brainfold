"""Shared brain: real folders and files with per-folder permissions.

Each folder may carry a `.oif.toml` with `description`, `start_here`, `read` and `write`.
Grants are member emails, `@group` or `*`. Read is intersected down the tree and denied
unless some ancestor grants it; write follows the nearest folder that declares it and is
denied by default. `/people/<alias>` is reserved: only its owner reads or writes it.
Dot-entries (metadata, `.git`) and symlinks are never visible to or writable by an agent.

Every public operation runs under one process lock, so comparing a version, writing and
committing to git are atomic with respect to other callers.
"""

from __future__ import annotations

import functools
import hashlib
import json
import os
import re
import subprocess
import threading
import tomllib
import unicodedata
from collections.abc import Callable, Mapping, Sequence
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from oif import OIFError

GRANT = re.compile(r"\*|@[a-z0-9][a-z0-9_-]{0,62}|[^@\s]+@[^@\s]+")
MAX_PATH_BYTES = 1024
MAX_DEPTH = 32
PAGE = 256  # entries per listing page
MAX_READ_BYTES = 65_536  # text returned by one read call
MAX_TEXT_BYTES = 1_048_576  # text file size writable and searchable over MCP
MAX_SEARCH_HITS = 50
PEOPLE = "people"
LEARNING = "<!-- oif:learning "
GIT_TIMEOUT = 20


def _unavailable() -> OIFError:
    # Same public error for an invalid path, wrong kind, absence or denial.
    return OIFError("unavailable", "The path is not available.")


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


def _fold(name: str) -> str:
    return unicodedata.normalize("NFC", name).casefold()


def _version(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _is_text(data: bytes) -> bool:
    if b"\x00" in data:
        return False
    try:
        data.decode("utf-8")
    except UnicodeDecodeError:
        return False
    return True


def _locked(method: Callable[..., Any]) -> Callable[..., Any]:
    @functools.wraps(method)
    def wrapper(self: Brain, *args: Any, **kwargs: Any) -> Any:
        with self._lock:
            try:
                return method(self, *args, **kwargs)
            except OSError:
                self._clean()
                raise OIFError("storage_error", "Storage failed. Try again later.") from None

    return wrapper


class Brain:
    def __init__(
        self,
        root: Path,
        groups: Callable[[], Mapping[str, Sequence[str]]],
        alias: Callable[[str], str | None] = lambda who: None,
        git: bool = True,
    ) -> None:
        self.groups = groups
        self.alias = alias
        self.root = root.resolve(strict=True)
        if not self.root.is_dir():
            raise OIFError("invalid_configuration", "The brain root is not a folder.")
        # ponytail: one lock for reads and writes; split when read throughput matters.
        self._lock = threading.RLock()
        self.unversioned = 0  # writes since start that git did not record
        self._clean()
        self.git = git and self._start_git()

    # --- paths and permissions ------------------------------------------------------

    def _real(self, path: str) -> Path:
        if not _canonical(path):
            raise _unavailable()
        parts = [part for part in path.split("/") if part]
        if any(part.startswith(".") for part in parts):
            raise _unavailable()
        if parts and _fold(parts[0]) == PEOPLE and parts[0] != PEOPLE:
            raise _unavailable()
        current = self.root
        for part in parts:
            # Names must match what is on disk exactly, so macOS and Linux behave alike.
            if current.is_dir():
                names = os.listdir(current)
                if part not in names and any(_fold(name) == _fold(part) for name in names):
                    raise _unavailable()
            current = current / part
        if current.resolve() != current:  # a symlink anywhere on the way
            raise _unavailable()
        return current

    def _parts(self, target: Path) -> tuple[str, ...]:
        return target.relative_to(self.root).parts

    def _path(self, target: Path) -> str:
        return "/" + "/".join(self._parts(target))

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
        parts = self._parts(target)
        folders = [self.root]
        for part in parts:
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
        if parts[:1] == (PEOPLE,):
            if len(parts) == 1:
                return read, False  # only the server creates personal folders
            owner = parts[1] == self.alias(who)
            return owner, owner  # absolute: no `.oif.toml` widens or narrows it
        return read, read and write

    def _writable(self, who: str, path: str) -> Path:
        target = self._real(path)
        read, write = self._access(who, target)
        if not read:
            raise _unavailable()
        if not write:
            raise OIFError("write_denied", "You do not have write permission on this path.")
        return target

    # --- git ------------------------------------------------------------------------

    def _git(self, *args: str, author: str = "oif") -> bool:
        env = {
            **os.environ,
            "GIT_CONFIG_GLOBAL": os.devnull,
            "GIT_CONFIG_NOSYSTEM": "1",
            "GIT_TERMINAL_PROMPT": "0",
        }
        command = ["git", "-C", str(self.root), "-c", f"user.name={author}"]
        command += ["-c", f"user.email={author}", "-c", "commit.gpgsign=false"]
        command += ["-c", f"core.hooksPath={os.devnull}", *args]
        try:
            return (
                subprocess.run(
                    command,
                    env=env,
                    stdin=subprocess.DEVNULL,
                    capture_output=True,
                    timeout=GIT_TIMEOUT,
                    check=False,
                ).returncode
                == 0
            )
        except (OSError, subprocess.TimeoutExpired):
            return False

    def _start_git(self) -> bool:
        if (self.root / ".git" / "index.lock").exists():
            raise OIFError(
                "invalid_configuration",
                "The brain's git repository is locked. If no git command is running there, "
                "remove .git/index.lock and start again.",
            )
        if not (self.root / ".git").exists() and not self._git("init", "-q"):
            return False  # git is not installed: the server works without history
        self._git("add", "-A")
        self._git("commit", "-q", "-m", "oif: record existing content")
        return self._git("rev-parse", "--git-dir")

    def _commit(self, who: str, message: str, *targets: Path) -> bool:
        """Record only these paths, never whatever a person has staged."""
        if not self.git:
            self.unversioned += 1
            return False
        paths = [str(target.relative_to(self.root)) for target in targets]
        self._git("add", "-A", "--", *paths)
        done = self._git("commit", "-q", "-m", f"{who}: {message}", "--", *paths, author=who)
        self.unversioned += not done
        return done

    def _baseline(self, target: Path) -> None:
        """Keep a hand edit or a crash leftover in history before changing the file."""
        if self.git and target.is_file():
            relative = str(target.relative_to(self.root))
            self._git("add", "--", relative)
            self._git("commit", "-q", "-m", f"oif: baseline {relative}", "--", relative)

    def _clean(self) -> None:
        for leftover in self.root.rglob(".*.oif-tmp"):
            if ".git" not in leftover.parts:
                leftover.unlink(missing_ok=True)

    def _store(self, target: Path, data: bytes) -> None:
        target.parent.mkdir(parents=True, exist_ok=True)
        temporary = target.with_name(f".{target.name}.oif-tmp")
        temporary.write_bytes(data)
        os.replace(temporary, target)

    # --- reading --------------------------------------------------------------------

    @_locked
    def list(self, who: str, path: str, manage: bool = False, offset: int = 0) -> dict[str, Any]:
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
                if child.is_symlink():
                    continue
                if not self._access(who, real)[0]:
                    # An administrator sees that personal folders exist, nothing inside them.
                    parts = self._parts(real)
                    if not manage or (len(parts) > 2 and parts[0] == PEOPLE):
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
        start = max(0, offset)
        result = {
            **({"read": meta.get("read"), "write": meta.get("write")} if manage else {}),
            "path": path,
            "description": meta.get("description", ""),
            "start_here": [f"{path.rstrip('/')}/{item}" for item in meta.get("start_here", [])],
            "can_write": write,
            "entries": entries[start : start + PAGE],
            "truncated": len(entries) > start + PAGE,
        }
        if path == "/" and (home := self.alias(who)):
            result["home"] = f"/{PEOPLE}/{home}"
        return result

    def _bytes(self, who: str, path: str) -> tuple[Path, bytes]:
        target = self._real(path)
        if not self._access(who, target)[0] or not target.is_file():
            raise _unavailable()
        return target, target.read_bytes()

    @_locked
    def read(
        self, who: str, path: str, offset: int = 0, limit: int | None = None
    ) -> dict[str, Any]:
        """Text comes back in line ranges of at most 64 KB; `version` covers the whole file."""
        _, data = self._bytes(who, path)
        result: dict[str, Any] = {"path": path, "version": _version(data), "size": len(data)}
        if len(data) > MAX_TEXT_BYTES or not _is_text(data):
            return result | {"kind": "binary"}
        lines = data.decode("utf-8").splitlines(keepends=True)
        start = max(0, offset)
        chosen: list[str] = []
        used = 0
        cut = False
        for line in lines[start : start + limit if limit else None]:
            room = MAX_READ_BYTES - used
            encoded = line.encode("utf-8")
            if len(encoded) > room:
                if not chosen:  # one line longer than the cap: cut it rather than return nothing
                    chosen.append(encoded[:room].decode("utf-8", "ignore"))
                    cut = True
                break
            chosen.append(line)
            used += len(encoded)
        end = start + len(chosen)
        return result | {
            "kind": "text",
            "content": "".join(chosen),
            "next_offset": end,
            "truncated": end < len(lines) or cut,
        }

    def _walk(self, who: str, path: str = "/") -> list[str]:
        """Every file the caller can read under a folder."""
        files: list[str] = []
        pending = [path]
        while pending:
            folder = pending.pop()
            offset = 0
            while True:
                page = self.list(who, folder, offset=offset)
                for entry in page["entries"]:
                    (pending if entry["kind"] == "directory" else files).append(entry["path"])
                if not page["truncated"]:
                    break
                offset += PAGE
        return sorted(files)

    @_locked
    def search(self, who: str, query: str, path: str = "/", offset: int = 0) -> dict[str, Any]:
        needle = query.casefold().strip()
        if not needle:
            raise OIFError("empty_query", "Provide text to search for.")
        hits: list[dict[str, Any]] = []
        skipped = 0
        # ponytail: linear scan of readable files; add an index when the brain grows.
        for file_path in self._walk(who, path):
            _, data = self._bytes(who, file_path)
            if len(data) > MAX_TEXT_BYTES or not _is_text(data):
                skipped += 1
                continue
            hits += [
                {"path": file_path, "line": number, "text": line.strip()[:200]}
                for number, line in enumerate(data.decode("utf-8").splitlines(), 1)
                if needle in line.casefold()
            ]
        start = max(0, offset)
        return {
            "hits": hits[start : start + MAX_SEARCH_HITS],
            "truncated": len(hits) > start + MAX_SEARCH_HITS,
            "skipped_files": skipped,
        }

    @_locked
    def skills(self, who: str) -> list[dict[str, Any]]:
        """Every readable, valid SKILL.md with the name and description of its front matter."""
        found = []
        # ponytail: walks the readable tree on each call; fine to a few thousand files.
        for path in self._walk(who):
            if path.endswith("/SKILL.md"):
                fields = _front_matter(self._bytes(who, path)[1])
                if fields:
                    found.append({"path": path, **fields})
        return found[:PAGE]

    @_locked
    def learnings(self, who: str, limit: int = 50) -> dict[str, Any]:
        """Newest entries of every readable LEARNINGS.md. Attribution is advisory."""
        entries = []
        for path in self._walk(who):
            if not path.endswith("/LEARNINGS.md"):
                continue
            data = self._bytes(who, path)[1]
            if len(data) > MAX_TEXT_BYTES or not _is_text(data):
                continue
            for block in data.decode("utf-8").split(LEARNING)[1:]:
                header, _, text = block.partition("-->")
                date, _, author = header.strip().partition(" ")
                entries.append({"path": path, "date": date, "author": author, "text": text.strip()})
        entries.sort(key=lambda entry: entry["date"], reverse=True)
        bounded = max(1, min(limit, 200))
        return {"learnings": entries[:bounded], "truncated": len(entries) > bounded}

    # --- writing --------------------------------------------------------------------

    def _check_version(self, target: Path, version: str | None) -> None:
        if not target.exists():
            if version is not None:
                raise OIFError("conflict", "The file no longer exists.")
            return
        if target.is_dir():
            raise _unavailable()
        current = _version(target.read_bytes())
        if version is None:
            raise OIFError(
                "already_exists", f"The file exists. Pass its version to replace it: {current}"
            )
        if version != current:
            raise OIFError("conflict", f"The file changed. Current version: {current}")

    def _put(self, who: str, target: Path, text: str, action: str) -> dict[str, Any]:
        try:
            data = text.encode("utf-8")
        except UnicodeEncodeError:
            raise OIFError("invalid_content", "The content is not valid text.") from None
        if len(data) > MAX_TEXT_BYTES:
            raise OIFError(
                "file_too_large", "Text files are limited to 1 MB. Split or rotate the file."
            )
        if target.name == "SKILL.md" and not _front_matter(data):
            raise OIFError(
                "invalid_skill",
                "A SKILL.md must start with front matter: a line '---', then 'name: ...' and "
                "'description: ...', then a line '---'.",
            )
        self._baseline(target)
        self._store(target, data)
        path = self._path(target)
        return {
            "path": path,
            "version": _version(data),
            "versioned": self._commit(who, f"{action} {path}", target),
        }

    @_locked
    def write(
        self, who: str, path: str, content: str, version: str | None = None
    ) -> dict[str, Any]:
        """Create a file, or replace one when `version` matches what the caller last read."""
        target = self._writable(who, path)
        if target == self.root:
            raise _unavailable()
        self._check_version(target, version)
        return self._put(who, target, content, "write")

    @_locked
    def edit(self, who: str, path: str, old: str, new: str) -> dict[str, Any]:
        """Replace one exact, unique fragment; the fragment itself guards against staleness."""
        target = self._writable(who, path)
        if not target.is_file() or not old:
            raise _unavailable()
        data = target.read_bytes()
        if len(data) > MAX_TEXT_BYTES or not _is_text(data):
            raise OIFError("invalid_edit", "Only text files can be edited.")
        text = data.decode("utf-8")
        count = text.count(old)
        if count != 1:
            reason = "was not found" if count == 0 else f"appears {count} times; make it unique"
            raise OIFError("invalid_edit", f"The fragment {reason}.")
        return self._put(who, target, text.replace(old, new), "edit")

    @_locked
    def append(self, who: str, path: str, content: str) -> dict[str, Any]:
        """Add to the end of a text file, creating it if missing. LEARNINGS.md is stamped."""
        target = self._writable(who, path)
        if target.is_dir() or target == self.root:
            raise _unavailable()
        data = target.read_bytes() if target.exists() else b""
        if not _is_text(data):
            raise OIFError("invalid_edit", "Only text files can be appended to.")
        text = data.decode("utf-8")
        if text and not text.endswith("\n"):
            text += "\n"
        if target.name == "LEARNINGS.md":
            stamp = datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")
            # A line that looks like a stamp inside the content must not split the entry.
            safe = content.replace(LEARNING, "<!-- oif-learning ")
            content = f"{LEARNING}{stamp} {who} -->\n{safe}"
        return self._put(who, target, text + content.rstrip("\n") + "\n", "append")

    @_locked
    def move(self, who: str, source: str, destination: str, version: str) -> dict[str, Any]:
        """Move a file. Folders move in phase 2 of the plan."""
        origin = self._writable(who, source)
        target = self._writable(who, destination)
        if origin.is_dir():
            raise OIFError("folder_not_movable", "Folders cannot be moved yet.")
        if not origin.is_file():
            raise _unavailable()
        if target.exists():
            raise OIFError("already_exists", "The destination already exists.")
        self._check_version(origin, version)
        if target.name == "SKILL.md" and not _front_matter(origin.read_bytes()):
            raise OIFError("invalid_skill", "The file is not a valid SKILL.md.")
        self._baseline(origin)
        target.parent.mkdir(parents=True, exist_ok=True)
        os.replace(origin, target)
        versioned = self._commit(who, f"move {source} to {destination}", origin, target)
        return {"path": destination, "version": version, "versioned": versioned}

    @_locked
    def delete(self, who: str, path: str, version: str) -> dict[str, Any]:
        """Delete a file. Until restore exists, only an administrator can recover it with git."""
        target = self._writable(who, path)
        if target.is_dir():
            raise OIFError("folder_not_movable", "Folders cannot be deleted yet.")
        if not target.is_file():
            raise _unavailable()
        self._check_version(target, version)
        self._baseline(target)
        target.unlink()
        return {"path": path, "versioned": self._commit(who, f"delete {path}", target)}

    # --- folders --------------------------------------------------------------------

    def _guide(
        self, who: str, target: Path, description: Any, start_here: Any, keep: dict[str, Any]
    ) -> dict[str, Any]:
        """Write a folder's guidance, keeping whatever access it declares."""
        valid = (
            isinstance(description, str)
            and isinstance(start_here, list)
            and all(
                isinstance(item, str)
                and not item.startswith("/")
                and _canonical(f"/{item}")
                and not any(part.startswith(".") for part in item.split("/"))
                for item in start_here
            )
        )
        if not valid:
            raise OIFError(
                "invalid_metadata",
                "The description must be text and start_here a list of paths relative to the "
                "folder.",
            )
        meta = {"description": description, "start_here": start_here, **keep}
        # ponytail: only the four known keys are kept; extend when the format grows.
        text = "".join(
            f"{key} = {json.dumps(value, ensure_ascii=False)}\n" for key, value in meta.items()
        )
        try:
            if tomllib.loads(text) != meta:
                raise ValueError
        except ValueError:
            raise OIFError("invalid_metadata", "The description is not valid.") from None
        target.mkdir(parents=True, exist_ok=True)
        self._baseline(target / ".oif.toml")
        self._store(target / ".oif.toml", text.encode("utf-8"))
        path = self._path(target)
        versioned = self._commit(who, f"describe {path}", target / ".oif.toml")
        return {"path": path, "versioned": versioned}

    @_locked
    def create_folder(
        self, who: str, path: str, description: str, start_here: list[str] | None = None
    ) -> dict[str, Any]:
        target = self._writable(who, path)
        if target.exists():
            raise OIFError("already_exists", "The path already exists.")
        return self._guide(who, target, description, start_here or [], {})

    @_locked
    def describe_folder(
        self, who: str, path: str, description: str, start_here: list[str] | None = None
    ) -> dict[str, Any]:
        """Agents change guidance only; `read` and `write` stay as an administrator set them."""
        target = self._writable(who, path)
        if not target.is_dir():
            raise _unavailable()
        meta = self._meta(target)
        keep = {key: meta[key] for key in ("read", "write") if key in meta}
        return self._guide(who, target, description, start_here or [], keep)

    @_locked
    def set_access(
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
        parts = self._parts(target)
        if not target.is_dir() or (parts[:1] == (PEOPLE,) and len(parts) > 1):
            raise _unavailable()  # personal folders belong to their owner, always
        grants = [*(read or []), *(write or [])]
        if not all(isinstance(item, str) and GRANT.fullmatch(item) for item in grants):
            raise OIFError("invalid_metadata", "The access lists are not valid.")
        keep = {
            key: value for key, value in (("read", read), ("write", write)) if value is not None
        }
        return self._guide(who, target, description, start_here, keep)

    @_locked
    def ensure_home(self, who: str) -> None:
        """Create the caller's personal folder on first use. Only the server does this."""
        alias = self.alias(who)
        if alias and not (self.root / PEOPLE / alias).is_dir():
            self._guide("oif", self.root / PEOPLE / alias, f"Private notes of {who}.", [], {})


def _front_matter(data: bytes) -> dict[str, str]:
    """`name` and `description` of a SKILL.md, or nothing if its front matter is invalid."""
    if not _is_text(data):
        return {}
    lines = [line.strip() for line in data.decode("utf-8").splitlines()]
    if not lines or lines[0] != "---" or "---" not in lines[1:]:
        return {}
    fields: dict[str, str] = {}
    for line in lines[1 : lines.index("---", 1)]:
        key, separator, value = line.partition(":")
        if separator:
            fields[key.strip()] = value.strip()
    if fields.get("name") and fields.get("description"):
        return {"name": fields["name"], "description": fields["description"]}
    return {}
