import os
from collections.abc import AsyncIterator

import pytest
from hypothesis import settings

from tests.support.loop_guard import blocked_loop_guard

settings.register_profile("dev", max_examples=200)
settings.register_profile("ci", max_examples=1000)
settings.load_profile(os.environ.get("HYPOTHESIS_PROFILE", "dev"))


@pytest.fixture(autouse=True)
async def loop_guard(request: pytest.FixtureRequest) -> AsyncIterator[None]:
    """Fail any test during which a callback blocked the event loop for 50 ms or more."""
    if request.node.get_closest_marker("loop_guard_off"):
        yield
        return
    async with blocked_loop_guard(threshold=0.05):
        yield
