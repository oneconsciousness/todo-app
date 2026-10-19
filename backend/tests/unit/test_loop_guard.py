import asyncio
import logging
import time

import pytest

from tests.support.loop_guard import blocked_loop_guard

pytestmark = pytest.mark.loop_guard_off


async def test_loop_guard_flags_a_callback_that_blocks_for_100_ms() -> None:
    with pytest.raises(AssertionError, match=r"Executing .* took 0\.1\d* seconds"):
        async with blocked_loop_guard(threshold=0.05):
            time.sleep(0.1)
            await asyncio.sleep(0)


async def test_loop_guard_flags_a_block_when_the_log_level_is_error() -> None:
    root = logging.getLogger()
    previous_level = root.level
    root.setLevel(logging.ERROR)
    try:
        with pytest.raises(AssertionError, match="the event loop was blocked"):
            async with blocked_loop_guard(threshold=0.05):
                time.sleep(0.1)
                await asyncio.sleep(0)
    finally:
        root.setLevel(previous_level)


async def test_loop_guard_passes_code_that_awaits() -> None:
    async with blocked_loop_guard(threshold=0.05):
        await asyncio.sleep(0.1)
