"""OIF: a shared, permissioned brain of folders and files for any agent harness."""

__version__ = "0.1.0"


class OIFError(Exception):
    """A safe, classified error; its message may be returned to the user or model."""

    def __init__(self, code: str, message: str):
        super().__init__(message)
        self.code = code
        self.message = message
