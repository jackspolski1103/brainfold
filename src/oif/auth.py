"""Explicit development-only authentication; not an OIDC implementation."""

from __future__ import annotations

import hashlib
import hmac
import json
import os
import re
from collections.abc import Mapping

from oif.domain import OIFError


class DevelopmentTokenAuth:
    """Only token digests are retained. Identity comes from trusted server mapping."""

    def __init__(self, tokens: Mapping[str, str]):
        if not tokens or any(not token or not principal for token, principal in tokens.items()):
            raise OIFError("configuracion_invalida", "Falta configurar identidad de desarrollo.")
        self._tokens = tuple(
            (hashlib.sha256(token.encode()).digest(), principal)
            for token, principal in tokens.items()
        )

    @classmethod
    def from_env(cls, environ: Mapping[str, str] | None = None) -> DevelopmentTokenAuth:
        source = os.environ if environ is None else environ
        try:
            mapping = json.loads(source.get("OIF_IDENTITY_ENV_MAP", "{}"))
            if not isinstance(mapping, dict) or not mapping:
                raise ValueError
            tokens: dict[str, str] = {}
            for principal_id, variable in mapping.items():
                if not isinstance(principal_id, str) or not isinstance(variable, str):
                    raise ValueError
                if re.fullmatch(r"OIF_TOKEN_[A-Z0-9_]+", variable) is None:
                    raise ValueError
                token = source.get(variable, "")
                if not token or token in tokens:
                    raise ValueError
                tokens[token] = principal_id
            return cls(tokens)
        except (ValueError, TypeError):
            raise OIFError(
                "configuracion_invalida", "La identidad de desarrollo no está configurada."
            ) from None

    def authenticate(self, authorization: str | None) -> str:
        if authorization is None:
            raise self._unauthorized()
        scheme, separator, token = authorization.partition(" ")
        if scheme.lower() != "bearer" or not separator or not token or " " in token:
            raise self._unauthorized()
        supplied = hashlib.sha256(token.encode()).digest()
        principal: str | None = None
        for expected, identity in self._tokens:
            if hmac.compare_digest(expected, supplied):
                principal = identity
        if principal is None:
            raise self._unauthorized()
        return principal

    @staticmethod
    def _unauthorized() -> OIFError:
        return OIFError("no_autenticado", "La autenticación es obligatoria.")
