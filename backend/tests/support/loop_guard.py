"""Catch code that blocks the event loop while a test runs."""

import asyncio
import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager


class _RecordCollector(logging.Handler):
    """Keep every record logged while it is attached."""

    def __init__(self) -> None:
        super().__init__()
        self.records: list[logging.LogRecord] = []

    def emit(self, record: logging.LogRecord) -> None:
        self.records.append(record)


@asynccontextmanager
async def blocked_loop_guard(threshold: float = 0.05) -> AsyncIterator[None]:
    """Fail when any loop callback inside the block runs for `threshold` seconds or longer.

    asyncio's debug mode logs each slow callback as "Executing ... took N seconds"
    (https://docs.python.org/3/library/asyncio-dev.html#debug-mode).

    Raises:
        AssertionError: listing every slow callback seen.
    """
    loop = asyncio.get_running_loop()
    previous_debug, previous_threshold = loop.get_debug(), loop.slow_callback_duration
    collector = _RecordCollector()
    asyncio_logger = logging.getLogger("asyncio")
    previous_level = asyncio_logger.level
    asyncio_logger.addHandler(collector)
    # The slow-callback line is a WARNING; a quieter configured level would drop it before the collector sees it.
    asyncio_logger.setLevel(logging.WARNING)
    loop.set_debug(True)
    loop.slow_callback_duration = threshold
    try:
        # The loop times a callback only if debug was on when it started, so begin the block in a new step.
        await asyncio.sleep(0)
        yield
    finally:
        loop.set_debug(previous_debug)
        loop.slow_callback_duration = previous_threshold
        asyncio_logger.removeHandler(collector)
        asyncio_logger.setLevel(previous_level)
    slow = [record.getMessage() for record in collector.records if record.msg.startswith("Executing")]
    if slow:
        raise AssertionError("the event loop was blocked:\n" + "\n".join(slow))
