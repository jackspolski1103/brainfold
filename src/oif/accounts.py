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

from oif import OIFError

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


class User(NamedTuple):
    email: str
    role: str


def _digest(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


def _hash(password: str, salt: bytes) -> str:
    return hashlib.scrypt(password.encode(), salt=salt, n=2**14, r=8, p=1).hex()


def _email(value: Any) -> str:
    if not isinstance(value, str) or len(value) > 254 or not EMAIL.fullmatch(value.strip()):
        raise OIFError("email_invalido", "El email no es válido.")
    return value.strip().lower()


def _password(value: Any) -> str:
    if not isinstance(value, str) or not 10 <= len(value) <= 256:
        raise OIFError("contrasena_invalida", "La contraseña debe tener entre 10 y 256 caracteres.")
    salt = secrets.token_bytes(16)
    return f"{salt.hex()}:{_hash(value, salt)}"


def _unauthenticated() -> OIFError:
    return OIFError("no_autenticado", "La autenticación es obligatoria.")


class Accounts:
    def __init__(self, path: Path | str) -> None:
        self._db = sqlite3.connect(path, check_same_thread=False, isolation_level=None)
        self._db.executescript(SCHEMA)
        self._lock = threading.RLock()
        self._failures: dict[str, tuple[int, float]] = {}

    def _run(self, sql: str, *args: Any) -> list[tuple[Any, ...]]:
        with self._lock:
            return self._db.execute(sql, args).fetchall()

    # --- members -----------------------------------------------------------------

    def needs_setup(self) -> bool:
        return not self._run("SELECT 1 FROM users LIMIT 1")

    def setup(self, email: Any, password: Any) -> str:
        """The first account becomes the administrator; later accounts need an invite."""
        with self._lock:
            if not self.needs_setup():
                raise OIFError("ya_configurado", "El servidor ya tiene un administrador.")
            self._run(
                "INSERT INTO users VALUES (?, 'admin', ?, NULL)", _email(email), _password(password)
            )
        return _email(email)

    def invite(self, email: Any, role: Any) -> str:
        if role not in {"admin", "member"}:
            raise OIFError("rol_invalido", "El rol debe ser admin o member.")
        token = secrets.token_urlsafe(32)
        try:
            self._run(
                "INSERT INTO users VALUES (?, ?, NULL, ?)", _email(email), role, _digest(token)
            )
        except sqlite3.IntegrityError:
            raise OIFError("ya_existe", "Ya existe una cuenta con ese email.") from None
        return token

    def accept(self, invite: Any, password: Any) -> str:
        hashed = _password(password)
        with self._lock:
            rows = self._run("SELECT email FROM users WHERE invite = ?", _digest(str(invite)))
            if not rows:
                raise OIFError("invitacion_invalida", "La invitación no es válida o ya se usó.")
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
                raise OIFError("ultimo_admin", "No se puede quitar al único administrador.")
            self._run("DELETE FROM users WHERE email = ?", email)  # cascades to tokens, groups

    def groups(self) -> dict[str, list[str]]:
        result: dict[str, list[str]] = {}
        for name, email in self._run("SELECT grp, email FROM memberships ORDER BY grp, email"):
            result.setdefault(name, []).append(email)
        return result

    def set_group(self, name: str, members: Any) -> None:
        """Replace a group's members; an empty list deletes the group."""
        if not GROUP.fullmatch(name) or not isinstance(members, list):
            raise OIFError("grupo_invalido", "El nombre del grupo o sus miembros no son válidos.")
        with self._lock:
            try:
                self._run("BEGIN")
                self._run("DELETE FROM memberships WHERE grp = ?", name)
                for email in dict.fromkeys(members):
                    self._run("INSERT INTO memberships VALUES (?, ?)", name, email)
                self._run("COMMIT")
            except sqlite3.Error:
                self._run("ROLLBACK")
                raise OIFError("grupo_invalido", "Algún miembro no tiene cuenta.") from None

    # --- authentication ----------------------------------------------------------

    def login(self, email: Any, password: Any) -> str:
        email = str(email).strip().lower()
        failed = OIFError("credenciales_invalidas", "Email o contraseña incorrectos.")
        count, since = self._failures.get(email, (0, 0.0))
        if count >= MAX_FAILURES and time.time() - since < LOCK_SECONDS:
            raise OIFError("demasiados_intentos", "Demasiados intentos. Probá en un minuto.")
        rows = self._run("SELECT password FROM users WHERE email = ?", email)
        salt, _, expected = (rows[0][0] if rows and rows[0][0] else "00:").partition(":")
        # Hash even for unknown accounts so timing does not reveal which emails exist.
        supplied = _hash(str(password), bytes.fromhex(salt))
        if not expected or not hmac.compare_digest(supplied, expected):
            # ponytail: per-process counter; move to the database when running replicas.
            self._failures[email] = (count % MAX_FAILURES + 1, time.time())
            raise failed
        self._failures.pop(email, None)
        return self.issue(email, "session", "panel", SESSION_SECONDS)[1]

    def issue(self, email: str, kind: str, name: Any, ttl: float | None = None) -> tuple[int, str]:
        if not isinstance(name, str) or not 1 <= len(name.strip()) <= 80:
            raise OIFError("nombre_invalido", "El token necesita un nombre de hasta 80 caracteres.")
        token = f"oif_{secrets.token_urlsafe(32)}"
        now = time.time()
        with self._lock:
            self._run(
                "INSERT INTO tokens(digest, email, kind, name, created, expires) "
                "VALUES (?, ?, ?, ?, ?, ?)",
                *(_digest(token), email, kind, name.strip(), now, now + ttl if ttl else None),
            )
            return self._run("SELECT last_insert_rowid()")[0][0], token

    def authenticate(self, token: str | None) -> User:
        if not token:
            raise _unauthenticated()
        rows = self._run(
            "SELECT tokens.id, users.email, users.role FROM tokens JOIN users USING (email) "
            "WHERE digest = ? AND (expires IS NULL OR expires > ?)",
            *(_digest(token), time.time()),
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

    # --- activity ----------------------------------------------------------------

    def log(self, actor: str, action: str, path: str, ok: bool) -> None:
        self._run(
            "INSERT INTO activity(at, actor, action, path, ok) VALUES (?, ?, ?, ?, ?)",
            *(time.time(), actor, action, path[:1024], int(ok)),
        )

    def activity(self, limit: int = 200) -> list[dict[str, Any]]:
        return [
            {"at": at, "actor": actor, "action": action, "path": path, "ok": bool(ok)}
            for at, actor, action, path, ok in self._run(
                "SELECT at, actor, action, path, ok FROM activity ORDER BY id DESC LIMIT ?",
                max(1, min(limit, 1000)),
            )
        ]
