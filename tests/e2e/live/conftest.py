"""Shared fixtures for the live tests."""

from collections.abc import Iterator

import httpx
import pytest

from support import BASE_URL


@pytest.fixture
def client() -> Iterator[httpx.Client]:
    """Yield a client that talks to the stack the way the browser does: through nginx, from the app's origin."""
    with httpx.Client(base_url=BASE_URL, headers={"Origin": BASE_URL}, timeout=10.0) as live_client:
        yield live_client
