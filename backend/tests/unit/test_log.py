import contextvars
import json
import logging
from collections.abc import Iterator
from logging.handlers import QueueHandler, QueueListener

import pytest

from app.config import Settings
from app.log import configure_logging, request_id_var, user_id_var

SETTINGS = Settings(
    database_url="postgresql+asyncpg://todo:todo@localhost:5432/todo",
    jwt_secret="unit-test-signing-key-0123456789abcdef",
)
log = logging.getLogger("app.test_log")


@pytest.fixture(autouse=True)
def restore_root_logger() -> Iterator[None]:
    """Take the JSON queue handler off the root logger after each test."""
    yield
    root = logging.getLogger()
    for handler in [h for h in root.handlers if isinstance(h, QueueHandler)]:
        root.removeHandler(handler)


def read_json_lines(listener: QueueListener, capsys: pytest.CaptureFixture[str]) -> list[dict[str, object]]:
    """Flush the queue, then return the JSON lines this module's logger wrote to stdout."""
    listener.stop()
    lines = (json.loads(line) for line in capsys.readouterr().out.splitlines())
    return [line for line in lines if line["logger"] == log.name]


def test_json_line_carries_request_and_user_ids(capsys: pytest.CaptureFixture[str]) -> None:
    def log_inside_a_request() -> None:
        request_id_var.set("req-123")
        user_id_var.set("user-456")
        log.info("task listed")

    listener = configure_logging(SETTINGS)
    contextvars.copy_context().run(log_inside_a_request)
    [line] = read_json_lines(listener, capsys)
    assert (line["msg"], line["request_id"], line["user_id"]) == ("task listed", "req-123", "user-456")


def test_exception_and_traceback_stay_in_one_json_line(capsys: pytest.CaptureFixture[str]) -> None:
    listener = configure_logging(SETTINGS)
    try:
        raise RuntimeError("boom")
    except RuntimeError:
        log.exception("request failed")
    [line] = read_json_lines(listener, capsys)
    assert isinstance(line["exc"], str)
    assert "Traceback" in line["exc"]
    assert "RuntimeError: boom" in line["exc"]


def test_uvicorn_lines_reach_the_json_log_but_its_access_lines_do_not(capsys: pytest.CaptureFixture[str]) -> None:
    listener = configure_logging(SETTINGS)
    logging.getLogger("uvicorn.error").info("Application startup complete.")
    logging.getLogger("uvicorn.access").info('172.24.0.5:59126 - "GET /readyz HTTP/1.1" 200')
    listener.stop()
    loggers = [json.loads(line)["logger"] for line in capsys.readouterr().out.splitlines()]
    assert loggers == ["uvicorn.error"]
