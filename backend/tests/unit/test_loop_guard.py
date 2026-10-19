import asyncio
import time

import pytest

from tests.support.loop_guard import blocked_loop_guard

pytestmark = pytest.mark.loop_guard_off


async def test_loop_guard_flags_a_callback_that_blocks_for_100_ms() -> None:
    with pytest.raises(AssertionError, match=r"Executing .* took 0\.1\d* seconds"):
        async with blocked_loop_guard(threshold=0.05):
            time.sleep(0.1)
            await asyncio.sleep(0)


async def test_loop_guard_passes_code_that_awaits() -> None:
    async with blocked_loop_guard(threshold=0.05):
        await asyncio.sleep(0.1)
