"""Values and helpers the live tests share."""

from typing import Final
from uuid import uuid4

# The stack's one published port, where nginx serves the SPA and proxies the API.
BASE_URL: Final = "http://localhost:8080"
PASSWORD: Final = "correct horse battery staple"


def unique_email() -> str:
    """Return an address no earlier run has registered, so tests never share an account."""
    return f"live-{uuid4().hex}@example.com"
