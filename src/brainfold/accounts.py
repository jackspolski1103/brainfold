"""Members, groups, tokens and activity in one SQLite file. One organization per server.

Passwords use scrypt; session, access and invite tokens are stored only as digests.
"""

from __future__ import annotations

import hashlib
import hmac
import re
import secrets
import sqlite3
import threading
import time
from pathlib import Path
from typing import Any, NamedTuple

from brainfold import BrainfoldError, short_name

EMAIL = re.compile(r"[^@\s]+@[^@\s]+")
GROUP = re.compile(r"[a-z0-9][a-z0-9_-]{0,62}")
SESSION_SECONDS = 7 * 24 * 3600
MAX_FAILURES = 5
LOCK_SECONDS = 60

SCHEMA = """
PRAGMA foreign_keys = ON;
CREATE TABLE IF NOT EXISTS users(
  email TEXT PRIMARY KEY, role TEXT NOT NULL, password TEXT, invite TEXT);
CREATE TABLE IF NOT EXISTS memberships(
  grp TEXT NOT NULL, email TEXT NOT NULL REFERENCES users ON DELETE CASCADE,
  PRIMARY KEY (grp, email));
CREATE TABLE IF NOT EXISTS tokens(
  id INTEGER PRIMARY KEY, digest TEXT UNIQUE NOT NULL,
  email TEXT NOT NULL REFERENCES users ON DELETE CASCADE,
  kind TEXT NOT NULL, name TEXT NOT NULL, created REAL NOT NULL, expires REAL, last_used REAL);
CREATE TABLE IF NOT EXISTS activity(
  id INTEGER PRIMARY KEY, at REAL NOT NULL, actor TEXT NOT NULL,
  action TEXT NOT NULL, path TEXT NOT NULL, ok INTEGER NOT NULL);
"""


# Additive migrations, applied in order; `PRAGMA user_version` records how many ran.
MIGRATIONS = (
    SCHEMA,
    """
ALTER TABLE users ADD COLUMN alias TEXT;
CREATE TABLE aliases(alias TEXT PRIMARY KEY, email TEXT NOT NULL);
ALTER TABLE activity ADD COLUMN versioned INTEGER;
""",
    """
ALTER TABLE users ADD COLUMN created REAL NOT NULL DEFAULT 0;
CREATE TABLE retired_groups(name TEXT PRIMARY KEY);
CREATE TABLE revisions(
  id INTEGER PRIMARY KEY, path TEXT NOT NULL, commit_id TEXT NOT NULL, author TEXT NOT NULL,
  at REAL NOT NULL, kind TEXT NOT NULL, readers TEXT NOT NULL, version TEXT);
CREATE INDEX revisions_path ON revisions(path);
""",
)


class User(NamedTuple):
    email: str
    role: str


def _digest(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


def _hash(password: str, salt: bytes) -> str:
    return hashlib.scrypt(password.encode(), salt=salt, n=2**14, r=8, p=1).hex()


def _email(value: Any) -> str:
    if not isinstance(value, str) or len(value) > 254 or not EMAIL.fullmatch(value.strip()):
        raise BrainfoldError("invalid_email", "The email is not valid.")
    return value.strip().lower()


def _password(value: Any) -> str:
    if not isinstance(value, str) or not 10 <= len(value) <= 256:
        raise BrainfoldError("invalid_password", "The password must be 10 to 256 characters long.")
    salt = secrets.token_bytes(16)
    return f"{salt.hex()}:{_hash(value, salt)}"


def _unauthenticated() -> BrainfoldError:
    return BrainfoldError("unauthenticated", "Authentication is required.")


class Accounts:
    def __init__(self, path: Path | str) -> None:
        self._db = sqlite3.connect(path, check_same_thread=False, isolation_level=None)
        self._lock = threading.RLock()
        self._failures: dict[str, tuple[int, float]] = {}
        applied = self._db.execute("PRAGMA user_version").fetchone()[0]
        for number, migration in enumerate(MIGRATIONS[applied:], applied + 1):
            self._db.executescript(migration)
            self._db.execute(f"PRAGMA user_version = {number}")
        self._db.execute("PRAGMA foreign_keys = ON")
        for (email,) in self._run("SELECT email FROM users WHERE alias IS NULL"):
            self._assign_alias(email)

    def _run(self, sql: str, *args: Any) -> list[tuple[Any, ...]]:
        with self._lock:
            return self._db.execute(sql, args).fetchall()

    # --- members -----------------------------------------------------------------

    def _assign_alias(self, email: str) -> None:
        """Name of the personal folder. Rows in `aliases` are never deleted, so an alias
        freed by removing a member is never handed to anyone else, not even the same email."""
        attempt = 0
        while True:
            alias = short_name(email.split("@")[0], f"{email}#{attempt}", 4 + attempt)
            try:
                self._run("INSERT INTO aliases VALUES (?, ?)", alias, email)
                break
            except sqlite3.IntegrityError:
                attempt += 1
        self._run("UPDATE users SET alias = ? WHERE email = ?", alias, email)

    def alias(self, email: str) -> str | None:
        rows = self._run("SELECT alias FROM users WHERE email = ?", email)
        return rows[0][0] if rows else None

    def needs_setup(self) -> bool:
        return not self._run("SELECT 1 FROM users LIMIT 1")

    def setup(self, email: Any, password: Any) -> str:
        """The first account becomes the administrator; later accounts need an invite."""
        with self._lock:
            if not self.needs_setup():
                raise BrainfoldError("already_set_up", "The server already has an administrator.")
            self._run(
                "INSERT INTO users(email, role, password, created) VALUES (?, 'admin', ?, ?)",
                *(_email(email), _password(password), time.time()),
            )
            self._assign_alias(_email(email))
        return _email(email)

    def invite(self, email: Any, role: Any) -> str:
        if role not in {"admin", "member"}:
            raise BrainfoldError("invalid_role", "The role must be admin or member.")
        token = secrets.token_urlsafe(32)
        try:
            with self._lock:
                self._run(
                    "INSERT INTO users(email, role, invite, created) VALUES (?, ?, ?, ?)",
                    *(_email(email), role, _digest(token), time.time()),
                )
                self._assign_alias(_email(email))
        except sqlite3.IntegrityError:
            raise BrainfoldError(
                "already_exists", "An account with that email already exists."
            ) from None
        return token

    def accept(self, invite: Any, password: Any) -> str:
        hashed = _password(password)
        with self._lock:
            rows = self._run("SELECT email FROM users WHERE invite = ?", _digest(str(invite)))
            if not rows:
                raise BrainfoldError(
                    "invalid_invite", "The invite is not valid or was already used."
                )
            self._run(
                "UPDATE users SET password = ?, invite = NULL WHERE email = ?", hashed, rows[0][0]
            )
        return rows[0][0]

    def users(self) -> list[dict[str, Any]]:
        groups = self.groups()
        return [
            {
                "email": email,
                "role": role,
                "pending": pending == 1,
                "groups": sorted(name for name, members in groups.items() if email in members),
            }
            for email, role, pending in self._run(
                "SELECT email, role, password IS NULL FROM users ORDER BY email"
            )
        ]

    def remove_user(self, email: str) -> None:
        with self._lock:
            admins = [row[0] for row in self._run("SELECT email FROM users WHERE role = 'admin'")]
            if admins == [email]:
                raise BrainfoldError("last_admin", "The only administrator cannot be removed.")
            self._run("DELETE FROM users WHERE email = ?", email)  # cascades to tokens, groups

    def groups(self) -> dict[str, list[str]]:
        result: dict[str, list[str]] = {}
        for name, email in self._run("SELECT grp, email FROM memberships ORDER BY grp, email"):
            result.setdefault(name, []).append(email)
        return result

    def set_group(self, name: str, members: Any) -> None:
        """Replace a group's members; an empty list deletes the group."""
        if not GROUP.fullmatch(name) or not isinstance(members, list):
            raise BrainfoldError("invalid_group", "The group name or its members are not valid.")
        with self._lock:
            if self._run("SELECT 1 FROM retired_groups WHERE name = ?", name):
                # Old revisions name this group; new members must not inherit its history.
                raise BrainfoldError("invalid_group", "That group name was retired. Pick another.")
            if not members and name in self.groups():
                self._run("INSERT INTO retired_groups VALUES (?)", name)
            try:
                self._run("BEGIN")
                self._run("DELETE FROM memberships WHERE grp = ?", name)
                for email in dict.fromkeys(members):
                    self._run("INSERT INTO memberships VALUES (?, ?)", name, email)
                self._run("COMMIT")
            except sqlite3.Error:
                self._run("ROLLBACK")
                raise BrainfoldError("invalid_group", "A member has no account.") from None

    # --- authentication ----------------------------------------------------------

    def login(self, email: Any, password: Any, address: str = "") -> str:
        """`address` is the client's address: one attacker cannot lock an account for all."""
        email = str(email).strip().lower()
        failed = BrainfoldError("invalid_credentials", "Wrong email or password.")
        key = f"{email}|{address}"
        count, since = self._failures.get(key, (0, 0.0))
        if count >= MAX_FAILURES and time.time() - since < LOCK_SECONDS:
            raise BrainfoldError("too_many_attempts", "Too many attempts. Try again in a minute.")
        rows = self._run("SELECT password FROM users WHERE email = ?", email)
        salt, _, expected = (rows[0][0] if rows and rows[0][0] else "00:").partition(":")
        # Hash even for unknown accounts so timing does not reveal which emails exist.
        supplied = _hash(str(password), bytes.fromhex(salt))
        if not expected or not hmac.compare_digest(supplied, expected):
            # ponytail: per-process counter; move to the database when running replicas.
            self._failures[key] = (count % MAX_FAILURES + 1, time.time())
            raise failed
        self._failures.pop(key, None)
        return self.issue(email, "session", "panel", SESSION_SECONDS)[1]

    def issue(self, email: str, kind: str, name: Any, ttl: float | None = None) -> tuple[int, str]:
        if not isinstance(name, str) or not 1 <= len(name.strip()) <= 80:
            raise BrainfoldError("invalid_name", "The token needs a name of up to 80 characters.")
        token = f"brainfold_{secrets.token_urlsafe(32)}"
        now = time.time()
        with self._lock:
            self._run(
                "INSERT INTO tokens(digest, email, kind, name, created, expires) "
                "VALUES (?, ?, ?, ?, ?, ?)",
                *(_digest(token), email, kind, name.strip(), now, now + ttl if ttl else None),
            )
            return self._run("SELECT last_insert_rowid()")[0][0], token

    def authenticate(self, token: str | None, kind: str) -> User:
        """`kind` keeps the two credentials apart: a harness `access` token never opens the
        panel API, and a panel `session` never acts as a harness."""
        if not token:
            raise _unauthenticated()
        rows = self._run(
            "SELECT tokens.id, users.email, users.role FROM tokens JOIN users USING (email) "
            "WHERE digest = ? AND kind = ? AND (expires IS NULL OR expires > ?)",
            *(_digest(token), kind, time.time()),
        )
        if not rows:
            raise _unauthenticated()
        self._run("UPDATE tokens SET last_used = ? WHERE id = ?", time.time(), rows[0][0])
        return User(rows[0][1], rows[0][2])

    def logout(self, token: str | None) -> None:
        self._run("DELETE FROM tokens WHERE digest = ?", _digest(token or ""))

    def tokens(self, email: str) -> list[dict[str, Any]]:
        return [
            {"id": identifier, "name": name, "created": created, "last_used": last_used}
            for identifier, name, created, last_used in self._run(
                "SELECT id, name, created, last_used FROM tokens "
                "WHERE email = ? AND kind = 'access' ORDER BY id",
                email,
            )
        ]

    def revoke(self, email: str, token_id: int) -> None:
        self._run("DELETE FROM tokens WHERE id = ? AND email = ?", token_id, email)

    # --- revisions (the brain's journal) -----------------------------------------

    def add_revision(
        self, path: str, commit: str, author: str, kind: str, readers: str, version: str | None
    ) -> None:
        self._run(
            "INSERT INTO revisions(path, commit_id, author, at, kind, readers, version) "
            "VALUES (?, ?, ?, ?, ?, ?, ?)",
            *(path, commit, author, time.time(), kind, readers, version),
        )

    def revisions(self, path: str) -> list[dict[str, Any]]:
        keys = ("id", "commit", "author", "at", "kind", "readers", "version")
        rows = self._run(
            "SELECT id, commit_id, author, at, kind, readers, version FROM revisions "
            "WHERE path = ? ORDER BY id",
            path,
        )
        return [dict(zip(keys, row, strict=True)) for row in rows]

    def created(self, email: str) -> float:
        rows = self._run("SELECT created FROM users WHERE email = ?", email)
        return rows[0][0] if rows else float("inf")

    # --- activity ----------------------------------------------------------------

    def log(
        self, actor: str, action: str, path: str, ok: bool, versioned: bool | None = None
    ) -> None:
        """`versioned` is false when a change was saved but git did not record it."""
        self._run(
            "INSERT INTO activity(at, actor, action, path, ok, versioned) "
            "VALUES (?, ?, ?, ?, ?, ?)",
            *(time.time(), actor, action, path[:1024], int(ok), versioned),
        )

    def healthy(self) -> bool:
        try:
            return self._run("SELECT 1") == [(1,)]
        except sqlite3.Error:
            return False

    def activity(self, limit: int = 200) -> list[dict[str, Any]]:
        return [
            {
                "at": at,
                "actor": actor,
                "action": action,
                "path": path,
                "ok": bool(ok),
                "versioned": None if versioned is None else bool(versioned),
            }
            for at, actor, action, path, ok, versioned in self._run(
                "SELECT at, actor, action, path, ok, versioned FROM activity "
                "ORDER BY id DESC LIMIT ?",
                max(1, min(limit, 1000)),
            )
        ]
