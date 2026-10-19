import asyncio
import gc
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


async def test_loop_guard_keeps_garbage_collection_out_of_the_timed_block() -> None:
    passes: list[str] = []

    def record(phase: str, info: dict[str, int]) -> None:
        passes.append(phase)

    gc.callbacks.append(record)
    try:
        async with blocked_loop_guard(threshold=0.05):
            # Enough new containers to start several automatic collections if the collector were on.
            kept = [[n] for n in range(100_000)]
            await asyncio.sleep(0)
            during_block = list(passes)
    finally:
        gc.callbacks.remove(record)
    assert len(kept) == 100_000
    assert during_block == []
