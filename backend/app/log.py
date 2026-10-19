"""JSON logging through a queue, so a slow stdout never blocks the event loop."""

import json
import logging
import sys
from contextvars import ContextVar
from datetime import UTC, datetime
from logging.handlers import QueueHandler, QueueListener
from queue import SimpleQueue
from typing import Final

from app.config import Settings

request_id_var: ContextVar[str | None] = ContextVar("request_id", default=None)
user_id_var: ContextVar[str | None] = ContextVar("user_id", default=None)

# Attributes every LogRecord has; anything else on a record came from the call's `extra`.
RECORD_ATTRIBUTES: Final = frozenset(vars(logging.makeLogRecord({}))) | {"message", "asctime"}
UVICORN_LOGGERS: Final = ("uvicorn", "uvicorn.error", "uvicorn.access")


class JsonFormatter(logging.Formatter):
    """Format a record as one JSON line with the request and user ids of the current context."""

    def format(self, record: logging.LogRecord) -> str:
        """Return the record as a single line of JSON, traceback included."""
        extra = {key: value for key, value in vars(record).items() if key not in RECORD_ATTRIBUTES}
        line = {
            "ts": datetime.fromtimestamp(record.created, UTC).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "msg": record.getMessage(),
            "request_id": request_id_var.get(),
            "user_id": user_id_var.get(),
            **extra,
        }
        exc = {"exc": self.formatException(record.exc_info)} if record.exc_info else {}
        return json.dumps(line | exc, default=str)


def configure_logging(settings: Settings) -> QueueListener:
    """Send every log line, uvicorn's included, through one queue to stdout as JSON, and start the writer thread.

    Calling it again replaces the previous setup, so lines are never written twice.
    The formatter sits on the `QueueHandler`, which formats on the calling thread, so the
    context variables are read in the request's own context
    (https://docs.python.org/3/library/logging.handlers.html#queuehandler).
    """
    root = logging.getLogger()
    for previous in [handler for handler in root.handlers if isinstance(handler, QueueHandler)]:
        if previous.listener is not None:
            previous.listener.stop()
        root.removeHandler(previous)

    queue: SimpleQueue[logging.LogRecord] = SimpleQueue()
    stdout = logging.StreamHandler(sys.stdout)
    stdout.setFormatter(logging.Formatter("%(message)s"))
    handler = QueueHandler(queue)
    handler.setFormatter(JsonFormatter())
    handler.listener = QueueListener(queue, stdout)
    root.addHandler(handler)
    root.setLevel(settings.log_level)

    for name in UVICORN_LOGGERS:
        uvicorn_logger = logging.getLogger(name)
        uvicorn_logger.handlers.clear()
        uvicorn_logger.propagate = True

    handler.listener.start()
    return handler.listener
