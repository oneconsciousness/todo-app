"""Values and helpers the live tests share."""

import os
from typing import Final
from uuid import uuid4

# The stack's front door: compose's port by default, or the cluster's (https://localhost:8443) on k3d.
BASE_URL: Final = os.environ.get("BASE_URL", "http://localhost:8080")
# How many API replicas sit behind it: two in compose, three on k3d.
API_REPLICAS: Final = int(os.environ.get("API_REPLICAS", "2"))
PASSWORD: Final = "correct horse battery staple"


def unique_email() -> str:
    """Return an address no earlier run has registered, so tests never share an account."""
    return f"live-{uuid4().hex}@example.com"
