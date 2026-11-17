"""Shared brain: real folders and files with per-folder permissions.

Each folder may carry a `.brainfold.toml` with `description`, `start_here`, `read` and `write`.
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
import shlex
import subprocess
import sys
import threading
import time
import tomllib
import unicodedata
from collections.abc import Callable, Mapping, Sequence
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from brainfold import BrainfoldError

GRANT = re.compile(r"\*|@[a-z0-9][a-z0-9_-]{0,62}|[^@\s]+@[^@\s]+")
MAX_PATH_BYTES = 1024
MAX_DEPTH = 32
MAX_NAME_BYTES = 240  # leaves room for the temporary name a write gives the file
PAGE = 256  # entries per listing page
MAX_READ_BYTES = 65_536  # text returned by one read call
MAX_TEXT_BYTES = 1_048_576  # text file size writable and searchable over MCP
MAX_SEARCH_HITS = 50
PEOPLE = "people"
LEARNING = "<!-- brainfold:learning "
GIT_TIMEOUT = 20


def _unavailable() -> BrainfoldError:
    # Same public error for an invalid path, wrong kind, absence or denial.
    return BrainfoldError("unavailable", "The path is not available.")


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
        part not in {"", ".", ".."} and len(part.encode("utf-8")) <= MAX_NAME_BYTES
        for part in parts
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


def _tidy(path: Any) -> Any:
    """Accept the path forms agents send: no leading slash, or one trailing slash."""
    if not isinstance(path, str):
        return path
    if not path.startswith("/"):
        path = f"/{path}"
    return path[:-1] if len(path) > 1 and path.endswith("/") and not path.endswith("//") else path


def _locked(method: Callable[..., Any]) -> Callable[..., Any]:
    names = method.__code__.co_varnames[1 : method.__code__.co_argcount]
    paths = {"path", "source", "destination"}

    @functools.wraps(method)
    def wrapper(self: Brain, *args: Any, **kwargs: Any) -> Any:
        args = (
            tuple(
                _tidy(value) if name in paths else value
                for name, value in zip(names, args, strict=False)
            )
            + args[len(names) :]
        )
        kwargs = {key: _tidy(value) if key in paths else value for key, value in kwargs.items()}
        with self._lock:
            try:
                return method(self, *args, **kwargs)
            except OSError:
                self._clean(uploads=False)
                raise BrainfoldError("storage_error", "Storage failed. Try again later.") from None

    return wrapper


class Brain:
    def __init__(
        self,
        root: Path,
        groups: Callable[[], Mapping[str, Sequence[str]]],
        alias: Callable[[str], str | None] = lambda who: None,
        git: bool = True,
        journal: Any = None,
        max_file_bytes: int = 25 * 1024 * 1024,
        mirror: str | None = None,
        ssh: str | None = None,
    ) -> None:
        self.mirror = mirror  # git remote that receives every change, as an off-site copy
        self.ssh = ssh  # ssh command git uses to reach it
        self.mirror_state = "off"
        self._changed = threading.Event()
        self.groups = groups
        self.alias = alias
        self.journal = journal  # revision records: add_revision, revisions, created
        self.max_file_bytes = max_file_bytes
        self.root = root.resolve(strict=True)
        if not self.root.is_dir():
            raise BrainfoldError("invalid_configuration", "The brain root is not a folder.")
        # ponytail: one lock for reads and writes; split when read throughput matters.
        self._lock = threading.RLock()
        self.unversioned = 0  # writes since start that git did not record
        self._clean(uploads=True)
        self.git = git and self._start_git()
        if self.mirror and self.git:
            self.mirror_state = "pending"
            self._changed.set()
            threading.Thread(target=self._mirror_changes, daemon=True).start()

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
            return tomllib.loads((directory / ".brainfold.toml").read_text("utf-8"))
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
        if parts[:1] == (PEOPLE,) and len(parts) > 1:
            # Absolute: no `.brainfold.toml`, not even the root's, widens or narrows it.
            owner = parts[1] == self.alias(who)
            return owner, owner
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
        if parts == (PEOPLE,):
            return read, False  # only the server creates personal folders
        return read, read and write

    def _writable(self, who: str, path: str) -> Path:
        target = self._real(path)
        read, write = self._access(who, target)
        if not read:
            # A hidden folder answers like a missing one: with what the nearest folder the
            # caller can see says about a new path there.
            seen = target.parent
            while seen != self.root and not (seen.is_dir() and self._access(who, seen)[0]):
                seen = seen.parent
            hidden = self._parts(target)[:1] != (PEOPLE,) and target != self.root
            if not (hidden and self._access(who, seen) == (True, False)):
                raise _unavailable()
        if not write:
            raise BrainfoldError("write_denied", "You do not have write permission on this path.")
        if any(above.is_file() for above in target.parents):
            raise _unavailable()  # a file is not a folder to write into
        return target

    # --- git ------------------------------------------------------------------------

    MIRROR_RETRY = 30  # seconds before the first retry; doubles up to 16 times that

    def _mirror_changes(self) -> None:
        """Push after every change, outside the brain lock. Never forces: if the mirror
        holds history this brain lacks, the state stays `failing` for a person to look at.
        A failed push is retried on its own, and git's reason goes to the server's output
        (never to `/api/health`, which is public and must not show the mirror's address)."""
        delay, reported = self.MIRROR_RETRY, ""
        while True:
            self._changed.wait()
            self._changed.clear()
            if self.mirror_state == "ok":
                self.mirror_state = "pending"
            done = self._git_run(
                "push", "--quiet", self.mirror or "", "HEAD:refs/heads/main", wait=120
            )
            if done is not None and done.returncode == 0:
                delay, reported = self.MIRROR_RETRY, ""
                if not self._changed.is_set():
                    self.mirror_state = "ok"
                continue
            self.mirror_state = "failing"
            lines = done.stderr.decode(errors="replace").strip().splitlines() if done else []
            telling = [line for line in lines if re.search("fatal:|error:|rejected", line)]
            reason = ((telling or lines or ["git did not answer in time"])[0]).replace(
                self.mirror or "", "the mirror"
            )
            if reason != reported:  # once per cause, not once per retry
                print(f"Mirror push failed, retrying: {reason}", file=sys.stderr, flush=True)
                reported = reason
            time.sleep(delay)
            delay = min(delay * 2, self.MIRROR_RETRY * 16)
            self._changed.set()

    @staticmethod
    def restore_from_mirror(root: Path, mirror: str, ssh: str | None) -> bool:
        """Fill an empty brain folder from its mirror, for a new or replaced volume."""
        if any(root.iterdir()):
            return False
        env = {
            **os.environ,
            "GIT_TERMINAL_PROMPT": "0",
            **({"GIT_SSH_COMMAND": ssh} if ssh else {}),
        }
        try:
            done = subprocess.run(
                ["git", "clone", "--quiet", "--branch", "main", mirror, str(root)],
                env=env,
                stdin=subprocess.DEVNULL,
                capture_output=True,
                timeout=300,
                check=False,
            )
        except (OSError, subprocess.TimeoutExpired):
            return False
        return done.returncode == 0 and any(entry.name != ".git" for entry in root.iterdir())

    def _git_output(
        self, *args: str, author: str = "brainfold", wait: int = GIT_TIMEOUT
    ) -> bytes | None:
        done = self._git_run(*args, author=author, wait=wait)
        return done.stdout if done and done.returncode == 0 else None

    def _git_run(
        self, *args: str, author: str = "brainfold", wait: int = GIT_TIMEOUT
    ) -> subprocess.CompletedProcess[bytes] | None:
        """Run git with no user configuration, hooks, signing or prompt, and a time limit."""
        env = {
            **os.environ,
            "GIT_CONFIG_GLOBAL": os.devnull,
            "GIT_CONFIG_NOSYSTEM": "1",
            "GIT_TERMINAL_PROMPT": "0",
            **({"GIT_SSH_COMMAND": self.ssh} if self.ssh else {}),
        }
        command = ["git", "-C", str(self.root), "-c", f"user.name={author}"]
        command += ["-c", f"user.email={author}", "-c", "commit.gpgsign=false"]
        command += ["-c", f"core.hooksPath={os.devnull}", *args]
        try:
            return subprocess.run(
                command,
                env=env,
                stdin=subprocess.DEVNULL,
                capture_output=True,
                timeout=wait,
                check=False,
            )
        except (OSError, subprocess.TimeoutExpired):
            return None

    def _git(self, *args: str, author: str = "brainfold", wait: int = GIT_TIMEOUT) -> bool:
        return self._git_output(*args, author=author, wait=wait) is not None

    def _start_git(self) -> bool:
        if (self.root / ".git" / "index.lock").exists():
            raise BrainfoldError(
                "invalid_configuration",
                "The brain's git repository is locked. If no git command is running there, "
                "remove .git/index.lock and start again.",
            )
        if not (self.root / ".git").exists() and not self._git("init", "-q"):
            return False  # git is not installed: the server works without history
        self._git("add", "-A")
        self._git("commit", "-q", "-m", "brainfold: record existing content")
        return self._git("rev-parse", "--git-dir")

    def _commit(self, who: str, message: str, *targets: Path) -> bool:
        """Record only these paths, never whatever a person has staged."""
        if not self.git:
            self.unversioned += 1
            return False
        paths = [str(target.relative_to(self.root)) for target in targets]
        self._git("add", "-A", "--", *paths)
        if self._git("diff", "--cached", "--quiet", "--", *paths):
            return True  # identical content is already in history
        done = self._git("commit", "-q", "-m", f"{who}: {message}", "--", *paths, author=who)
        self.unversioned += not done
        self._changed.set()
        return done

    def _snapshot(self, target: Path) -> str:
        """Who could read this path right now: stored with each revision."""
        parts = self._parts(target)
        if parts[:1] == (PEOPLE,) and len(parts) > 1:
            return json.dumps({"owner": parts[1]})
        folders = [self.root]
        for part in parts:
            if (folders[-1] / part).is_dir():
                folders.append(folders[-1] / part)
        reads = [meta["read"] for meta in map(self._meta, folders) if "read" in meta]
        return json.dumps({"reads": reads})

    def _record(self, author: str, records: Sequence[tuple[Path, str, str | None, str]]) -> None:
        commit = self._git_output("rev-parse", "HEAD") if self.journal and self.git else None
        if commit:
            for target, kind, version, readers in records:
                self.journal.add_revision(
                    self._path(target), commit.decode().strip(), author, kind, readers, version
                )

    def _save(
        self, who: str, message: str, records: Sequence[tuple[Path, str, str | None]]
    ) -> bool:
        """Commit a change and, only if git kept it, add its revision records."""
        snapshots = [(*record, self._snapshot(record[0])) for record in records]
        done = self._commit(who, message, *(record[0] for record in records))
        if done:
            self._record(who, snapshots)
        return done

    def _baseline(self, target: Path) -> None:
        """Before changing a file, make sure its current content is in history: a hand
        edit, a crash leftover, or a file that predates the revision records."""
        if not (self.git and target.is_file()):
            return
        relative = str(target.relative_to(self.root))
        self._git("add", "--", relative)
        self._git("commit", "-q", "-m", f"brainfold: baseline {relative}", "--", relative)
        if self.journal and target.name != ".brainfold.toml":
            current = _version(target.read_bytes())
            rows = self.journal.revisions(self._path(target))
            if not rows or rows[-1]["version"] != current:
                self._record("brainfold", [(target, "baseline", current, self._snapshot(target))])

    def _clean(self, uploads: bool) -> None:
        """Remove leftover temporary files. Uploads are received outside the lock, so
        while the server runs theirs belong to requests still in flight: only a start
        removes them."""
        for leftover in self.root.rglob(".*.brainfold-tmp"):
            in_flight = leftover.name.startswith(".upload-") and not uploads
            if ".git" not in leftover.parts and not in_flight:
                leftover.unlink(missing_ok=True)

    def _fresh(self, target: Path) -> dict[str, Any]:
        """What to tell the caller about the folders this write is about to create."""
        missing, folder = [], target.parent
        while not folder.exists():
            missing.append(self._path(folder))
            folder = folder.parent
        if not missing:
            return {}
        return {
            "new_folders": missing[::-1],
            "note": "These folders were created without a description. Call describe_folder "
            "on each so whoever arrives next finds their way.",
        }

    def _store(self, target: Path, data: bytes) -> None:
        target.parent.mkdir(parents=True, exist_ok=True)
        temporary = target.with_name(f".{target.name}.brainfold-tmp")
        temporary.write_bytes(data)
        os.replace(temporary, target)

    # --- reading --------------------------------------------------------------------

    @_locked
    def list(self, who: str, path: str, manage: bool = False, offset: int = 0) -> dict[str, Any]:
        """`manage` shows an administrator every folder and its grants, not file content."""
        target = self._real(path)
        read, write = self._access(who, target)
        parts = self._parts(target)
        if parts[:1] == (PEOPLE,) and len(parts) > 1:
            manage = False  # a personal folder is its owner's, also for administrators
        if not (read or manage) or not target.is_dir():
            home = self.alias(who)
            if target == self.root and home and (self.root / PEOPLE / home).is_dir():
                # Someone who cannot read the root still has to find their own folder.
                own = f"/{PEOPLE}/{home}"
                return {
                    "path": "/",
                    "description": "",
                    "start_here": [],
                    "can_write": False,
                    "entries": [{"path": own, "kind": "directory"}],
                    "truncated": False,
                    "home": own,
                }
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
                elif read:  # an administrator who only manages sees names, nothing more
                    entry["size"] = child.stat().st_size
                    about = meta.get("files")
                    if isinstance(about, dict) and isinstance(about.get(child.name), str):
                        entry["description"] = about[child.name]
            except BrainfoldError:
                continue
            entries.append(entry)
        start = max(0, offset)
        result = {
            **(
                {
                    "read": meta.get("read"),
                    "write": meta.get("write"),
                    "guide": meta.get("start_here", []),
                }
                if manage
                else {}
            ),
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
        readable = self._access(who, target)[0]
        if readable and target.is_dir():
            raise BrainfoldError("unavailable", "That path is a folder. Use list to see inside it.")
        if not readable or not target.is_file():
            raise _unavailable()
        return target, target.read_bytes()

    @_locked
    def read(
        self, who: str, path: str, offset: int = 0, limit: int | None = None
    ) -> dict[str, Any]:
        """Text comes back in line ranges of at most 64 KB; `version` covers the whole file."""
        _, data = self._bytes(who, path)
        result: dict[str, Any] = {"path": path, "version": _version(data), "size": len(data)}
        # Quoted: the name was chosen by whoever stored the file.
        fetch = shlex.join(["brainfold", "get", path, f"./{path.rsplit('/', 1)[-1]}"])
        if len(data) > MAX_TEXT_BYTES or not _is_text(data):
            return result | {"kind": "binary", "fetch": fetch}
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
        result |= {
            "kind": "text",
            "content": "".join(chosen),
            "next_offset": end,
            "truncated": end < len(lines) or cut,
        }
        if cut:  # offsets are lines, so the rest of this one cannot be asked for
            result |= {
                "note": f"Line {end} is longer than one read and was cut; next_offset skips "
                "the rest of it. Get the whole file with the fetch command.",
                "fetch": fetch,
            }
        return result

    def _readable(self, who: str) -> list[str]:
        """Every file the caller can read; nothing if they cannot even read the root."""
        try:
            return self._walk(who)
        except BrainfoldError:
            return []

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
            raise BrainfoldError("empty_query", "Provide text to search for.")
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
        for path in self._readable(who):
            if path.endswith("/SKILL.md"):
                fields = _front_matter(self._bytes(who, path)[1])
                if fields:
                    found.append({"path": path, **fields})
        return found[:PAGE]

    @_locked
    def learnings(self, who: str, limit: int = 50) -> dict[str, Any]:
        """Newest entries of every readable LEARNINGS.md. Attribution is advisory."""
        entries = []
        for path in self._readable(who):
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
                raise BrainfoldError("conflict", "The file no longer exists.")
            return
        if target.is_dir():
            raise _unavailable()
        current = _version(target.read_bytes())
        if version is None:
            raise BrainfoldError(
                "already_exists", f"The file exists. Pass its version to replace it: {current}"
            )
        if version != current:
            raise BrainfoldError("conflict", f"The file changed. Current version: {current}")

    def _put(self, who: str, target: Path, text: str, action: str) -> dict[str, Any]:
        try:
            data = text.encode("utf-8")
        except UnicodeEncodeError:
            raise BrainfoldError("invalid_content", "The content is not valid text.") from None
        if len(data) > MAX_TEXT_BYTES:
            raise BrainfoldError(
                "file_too_large", "Text files are limited to 1 MB. Split or rotate the file."
            )
        if target.name == "SKILL.md" and not _front_matter(data):
            raise BrainfoldError(
                "invalid_skill",
                "A SKILL.md must start with front matter: a line '---', then 'name: ...' and "
                "'description: ...', then a line '---'.",
            )
        fresh = self._fresh(target)
        self._baseline(target)
        self._store(target, data)
        path = self._path(target)
        version = _version(data)
        versioned = self._save(who, f"{action} {path}", [(target, action, version)])
        return {"path": path, "version": version, "versioned": versioned} | fresh

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
            raise BrainfoldError("invalid_edit", "Only text files can be edited.")
        text = data.decode("utf-8")
        count = text.count(old)
        if count != 1:
            reason = "was not found" if count == 0 else f"appears {count} times; make it unique"
            raise BrainfoldError("invalid_edit", f"The fragment {reason}.")
        return self._put(who, target, text.replace(old, new), "edit")

    @_locked
    def append(self, who: str, path: str, content: str) -> dict[str, Any]:
        """Add to the end of a text file, creating it if missing. LEARNINGS.md is stamped."""
        target = self._writable(who, path)
        if target.is_dir() or target == self.root:
            raise _unavailable()
        data = target.read_bytes() if target.exists() else b""
        if not _is_text(data):
            raise BrainfoldError("invalid_edit", "Only text files can be appended to.")
        text = data.decode("utf-8")
        if text and not text.endswith("\n"):
            text += "\n"
        if target.name == "LEARNINGS.md":
            stamp = datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")
            # A line that looks like a stamp inside the content must not split the entry.
            safe = content.replace(LEARNING, "<!-- brainfold-learning ")
            content = f"{LEARNING}{stamp} {who} -->\n{safe}"
        return self._put(who, target, text + content.rstrip("\n") + "\n", "append")

    def _movable(self, folder: Path) -> list[Path]:
        """Files of a folder an agent may move: nothing hidden, nothing with declared access."""
        parts = self._parts(folder)
        if not parts or parts[0] == PEOPLE and len(parts) <= 2:
            raise BrainfoldError("folder_not_movable", "This folder cannot be moved.")
        files = []
        for entry in folder.rglob("*"):
            if entry.name == ".DS_Store":
                entry.unlink()
            elif entry.is_symlink() or (
                entry.name.startswith(".") and entry.name != ".brainfold.toml"
            ):
                raise BrainfoldError("folder_not_movable", "This folder cannot be moved.")
            elif entry.is_file() and entry.name != ".brainfold.toml":
                files.append(entry)
        for holder in (folder, *(entry for entry in folder.rglob("*") if entry.is_dir())):
            if {"read", "write"} & self._meta(holder).keys():
                raise BrainfoldError("folder_not_movable", "This folder cannot be moved.")
        return files

    @_locked
    def move(
        self, who: str, source: str, destination: str, version: str | None = None
    ) -> dict[str, Any]:
        """Move a file (with its `version`) or a whole folder. A folder moves only if it
        holds nothing hidden and no access declared by an administrator. History does not
        follow a move: each file starts a new history at its new path."""
        origin = self._writable(who, source)
        target = self._writable(who, destination)
        if target.exists():
            raise BrainfoldError("already_exists", "The destination already exists.")
        if origin.is_dir():
            if target.is_relative_to(origin):
                raise BrainfoldError("folder_not_movable", "A folder cannot move into itself.")
            files = self._movable(origin)
            for file in files:
                self._baseline(file)
            leaving = [(file, "move_out", None, self._snapshot(file)) for file in files]
            target.parent.mkdir(parents=True, exist_ok=True)
            os.replace(origin, target)
            arriving = [target / file.relative_to(origin) for file in files]
            versioned = self._commit(who, f"move {source} to {destination}", origin, target)
            if versioned:
                self._record(who, leaving)
                self._record(
                    who,
                    [
                        (file, "move_in", _version(file.read_bytes()), self._snapshot(file))
                        for file in arriving
                    ],
                )
            return {"path": destination, "versioned": versioned}
        if not origin.is_file() and (origin.exists() or version is None):
            raise _unavailable()
        if version is None:
            raise BrainfoldError("conflict", "Pass the version of the file you are moving.")
        self._check_version(origin, version)
        if target.name == "SKILL.md" and not _front_matter(origin.read_bytes()):
            raise BrainfoldError("invalid_skill", "The file is not a valid SKILL.md.")
        self._baseline(origin)
        leaving = [(origin, "move_out", None, self._snapshot(origin))]
        described = self._meta(origin.parent).get("files")
        about = described.get(origin.name) if isinstance(described, dict) else None
        target.parent.mkdir(parents=True, exist_ok=True)
        os.replace(origin, target)
        versioned = self._commit(who, f"move {source} to {destination}", origin, target)
        if versioned:
            self._record(who, [*leaving, (target, "move_in", version, self._snapshot(target))])
        if about:
            self._about(who, origin, None)
            self._about(who, target, about)
        return {"path": destination, "version": version, "versioned": versioned}

    @_locked
    def delete(self, who: str, path: str, version: str | None = None) -> dict[str, Any]:
        """Delete a file (with its `version`) or an empty folder. A deleted file can be
        brought back with restore; a folder must be emptied file by file first."""
        target = self._writable(who, path)
        if target.is_dir():
            meta = target / ".brainfold.toml"
            if target == self.root or {"read", "write"} & self._meta(target).keys():
                raise BrainfoldError("forbidden", "Only an administrator can delete this folder.")
            (target / ".DS_Store").unlink(missing_ok=True)
            if any(entry.name != ".brainfold.toml" for entry in target.iterdir()):
                raise BrainfoldError("folder_not_empty", "Delete or move what is inside it first.")
            self._movable(target)  # personal folders themselves stay
            meta.unlink(missing_ok=True)
            target.rmdir()
            return {"path": path, "versioned": self._commit(who, f"delete {path}", meta)}
        if not target.is_file() and (target.exists() or version is None):
            raise _unavailable()
        if version is None:
            raise BrainfoldError("conflict", "Pass the version of the file you are deleting.")
        self._check_version(target, version)
        self._baseline(target)
        snapshot = self._snapshot(target)
        target.unlink()
        versioned = self._commit(who, f"delete {path}", target)
        if versioned:
            self._record(who, [(target, "delete", None, snapshot)])
        self._about(who, target, None)
        return {"path": path, "versioned": versioned}

    # --- binary files ---------------------------------------------------------------

    @_locked
    def download(self, who: str, path: str) -> tuple[bytes, str]:
        data = self._bytes(who, path)[1]
        return data, _version(data)

    @_locked
    def put_file(self, who: str, path: str, source: Path, version: str | None) -> dict[str, Any]:
        """Store an uploaded file of any type. `source` is a temporary file in the root."""
        target = self._writable(who, path)
        if target.is_dir() or target == self.root:
            raise _unavailable()
        if source.stat().st_size > self.max_file_bytes:
            raise BrainfoldError("file_too_large", "The file exceeds the upload limit.")
        self._check_version(target, version)
        data = source.read_bytes()
        if target.name == "SKILL.md" and not _front_matter(data):
            raise BrainfoldError("invalid_skill", "The file is not a valid SKILL.md.")
        fresh = self._fresh(target)
        self._baseline(target)
        target.parent.mkdir(parents=True, exist_ok=True)
        os.replace(source, target)
        digest = _version(data)
        versioned = self._save(who, f"upload {path}", [(target, "upload", digest)])
        result = {"path": path, "version": digest, "size": len(data), "versioned": versioned}
        return result | fresh

    # --- history --------------------------------------------------------------------

    def _visible(self, who: str, path: str) -> list[dict[str, Any]]:
        """Revisions of a path the caller may see: they could read it then and can now."""
        target = self._real(path)
        read, write = self._access(who, target)
        allowed = read if target.is_file() else read and write and target.parent.is_dir()
        if not (self.journal and self.git and allowed) or target.is_dir():
            return []
        visible = []
        for row in self.journal.revisions(path):
            snapshot = json.loads(row["readers"])
            if "owner" in snapshot:
                seen = snapshot["owner"] == self.alias(who)
            else:
                # A direct email grant older than the account belongs to a previous holder.
                young = row["at"] < self.journal.created(who)
                seen = bool(snapshot["reads"]) and all(
                    self._granted(who, [g for g in grants if not (young and g == who)])
                    for grants in snapshot["reads"]
                )
            if seen:
                visible.append(row)
        return visible

    @_locked
    def history(self, who: str, path: str) -> dict[str, Any]:
        """Who changed this path and when. No content, no other paths, no following moves."""
        rows = self._visible(who, path)
        if not rows:
            raise BrainfoldError("no_history", "There is no history you can see for this path.")
        return {
            "path": path,
            "revisions": [
                {
                    "revision": row["id"],
                    "author": row["author"],
                    "date": datetime.fromtimestamp(row["at"], UTC).strftime("%Y-%m-%dT%H:%M:%SZ"),
                    "change": row["kind"],
                }
                for row in rows
            ],
        }

    @_locked
    def restore(
        self, who: str, path: str, revision: int, version: str | None = None
    ) -> dict[str, Any]:
        """Bring a file back to how it was after one of its revisions."""
        target = self._writable(who, path)
        row = next((row for row in self._visible(who, path) if row["id"] == revision), None)
        if row is None or row["kind"] in {"delete", "move_out"} or not target.parent.is_dir():
            raise BrainfoldError("no_history", "That revision cannot be restored.")
        self._check_version(target, version)
        relative = str(target.relative_to(self.root))
        data = self._git_output("show", f"{row['commit']}:{relative}")
        if data is None:  # someone rewrote the repository's history
            raise BrainfoldError("no_history", "That revision is no longer in the repository.")
        if target.name == "SKILL.md" and not _front_matter(data):
            raise BrainfoldError("invalid_skill", "That revision is not a valid SKILL.md.")
        self._baseline(target)
        self._store(target, data)
        digest = _version(data)
        versioned = self._save(who, f"restore {path}", [(target, "restore", digest)])
        return {"path": path, "version": digest, "versioned": versioned}

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
            raise BrainfoldError(
                "invalid_metadata",
                "The description must be text and start_here a list of paths relative to the "
                "folder.",
            )
        keep = dict(keep)
        files = keep.pop("files", None)
        if files is None and target.is_dir():
            files = self._meta(target).get("files")
        # The description of a file that is gone goes with it.
        files = {
            name: about
            for name, about in (files if isinstance(files, dict) else {}).items()
            if (target / name).is_file()
        }
        meta = {"description": description, "start_here": start_here, **keep}
        # ponytail: only the known keys are kept; extend when the format grows.
        text = "".join(
            f"{key} = {json.dumps(value, ensure_ascii=False)}\n" for key, value in meta.items()
        )
        if files:
            meta["files"] = files
            quoted = functools.partial(json.dumps, ensure_ascii=False)
            text += "\n[files]\n" + "".join(
                f"{quoted(name)} = {quoted(about)}\n" for name, about in files.items()
            )
        try:
            if tomllib.loads(text) != meta:
                raise ValueError
        except ValueError:
            raise BrainfoldError("invalid_metadata", "The description is not valid.") from None
        target.mkdir(parents=True, exist_ok=True)
        self._baseline(target / ".brainfold.toml")
        self._store(target / ".brainfold.toml", text.encode("utf-8"))
        path = self._path(target)
        versioned = self._commit(who, f"describe {path}", target / ".brainfold.toml")
        return {"path": path, "versioned": versioned}

    @_locked
    def create_folder(
        self, who: str, path: str, description: str, start_here: list[str] | None = None
    ) -> dict[str, Any]:
        target = self._writable(who, path)
        if target.exists():
            raise BrainfoldError("already_exists", "The path already exists.")
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

    def _about(self, who: str, target: Path, text: str | None) -> bool:
        """Set, or with `None` drop, the one-line description of a file. Nothing is
        written when there is nothing to change."""
        folder = target.parent
        meta = self._meta(folder)
        files = dict(meta["files"]) if isinstance(meta.get("files"), dict) else {}
        if files.get(target.name) == text:
            return True
        if text:
            files[target.name] = text
        else:
            files.pop(target.name, None)
        keep = {key: meta[key] for key in ("read", "write") if key in meta} | {"files": files}
        guide = meta.get("description", ""), meta.get("start_here", [])
        return self._guide(who, folder, *guide, keep)["versioned"]

    @_locked
    def describe_file(self, who: str, path: str, description: str) -> dict[str, Any]:
        """One line about a file, shown next to it in listings. Empty text removes it."""
        target = self._writable(who, path)
        if not target.is_file():
            raise _unavailable()
        if not isinstance(description, str) or len(description) > 300 or "\n" in description:
            raise BrainfoldError(
                "invalid_metadata", "The description must be one line of at most 300 characters."
            )
        text = description.strip()
        return {"path": path, "description": text, "versioned": self._about(who, target, text)}

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
            raise BrainfoldError("invalid_metadata", "The access lists are not valid.")
        # Accounts are stored in lower case: "Ana@Example.com" must grant ana@example.com.
        read, write = (
            None if grant is None else [g.lower() for g in grant] for grant in (read, write)
        )
        keep = {
            key: value for key, value in (("read", read), ("write", write)) if value is not None
        }
        return self._guide(who, target, description, start_here, keep)

    @_locked
    def forget(self, who: str, email: str) -> None:
        """Take a removed member out of every access list, so the same address invited
        again starts with nothing. `who` is the administrator who removed them."""
        for file in sorted(self.root.rglob(".brainfold.toml")):
            if ".git" in self._parts(file):
                continue
            try:
                meta = self._meta(file.parent)
                lists = {key: meta[key] for key in ("read", "write") if key in meta}
                kept = {
                    key: [grant for grant in value if grant != email]
                    for key, value in lists.items()
                }
                if kept != lists:
                    guide = meta.get("description", ""), meta.get("start_here", [])
                    self._guide(who, file.parent, *guide, kept)
            except (BrainfoldError, TypeError):
                continue  # metadata written by hand that is not valid already denies

    @_locked
    def ensure_home(self, who: str) -> None:
        """Create the caller's personal folder on first use. Only the server does this."""
        alias = self.alias(who)
        if alias and not (self.root / PEOPLE / ".brainfold.toml").is_file():
            about = "Personal folders, created by the server; each person sees only their own."
            self._guide("brainfold", self.root / PEOPLE, about, [], {})
        if alias and not (self.root / PEOPLE / alias).is_dir():
            self._guide("brainfold", self.root / PEOPLE / alias, f"Private notes of {who}.", [], {})


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
