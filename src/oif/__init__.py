"""OIF: a shared, permissioned brain of folders and files for any agent harness."""

import hashlib
import re

__version__ = "0.1.0"


def short_name(text: str, key: str, length: int) -> str:
    """A readable, stable identifier: sanitized text plus a digest of what makes it unique."""
    base = re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-") or "x"
    return f"{base}-{hashlib.sha256(key.encode()).hexdigest()[:length]}"


class OIFError(Exception):
    """A safe, classified error; its message may be returned to the user or model."""

    def __init__(self, code: str, message: str):
        super().__init__(message)
        self.code = code
        self.message = message
