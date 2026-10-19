import logging
import re
import socket

import pytest
from fastapi import FastAPI
from httpx import AsyncClient

from tests.support.app import serving

GENERATED_REQUEST_ID = re.compile(r"[0-9a-f]{32}")


async def test_a_valid_request_id_is_echoed(client: AsyncClient) -> None:
    response = await client.get("/livez", headers={"X-Request-ID": "trace-123_ab.c"})
    assert response.headers["X-Request-ID"] == "trace-123_ab.c"


@pytest.mark.parametrize("sent", [None, "has spaces", "x" * 65], ids=["missing", "bad-characters", "too-long"])
async def test_a_missing_or_invalid_request_id_is_replaced(client: AsyncClient, sent: str | None) -> None:
    headers = {"X-Request-ID": sent} if sent is not None else {}
    response = await client.get("/livez", headers=headers)
    assert GENERATED_REQUEST_ID.fullmatch(response.headers["X-Request-ID"])


async def test_responses_name_the_replica(client: AsyncClient) -> None:
    response = await client.get("/livez")
    assert response.headers["X-Served-By"] == socket.gethostname()


async def test_api_responses_are_not_cached(client: AsyncClient) -> None:
    response = await client.get("/api/openapi.json")
    assert response.headers["Cache-Control"] == "no-store"


async def test_unhandled_error_returns_500_envelope_and_logs_the_traceback(
    app: FastAPI, caplog: pytest.LogCaptureFixture
) -> None:
    async def explode() -> None:
        raise RuntimeError("boom")

    app.add_api_route("/api/v1/test-only/explode", explode)
    async with serving(app, raise_app_exceptions=False) as client:
        response = await client.get("/api/v1/test-only/explode")
    assert response.status_code == 500
    assert response.json()["error"]["code"] == "internal_error"
    assert "boom" not in response.text
    [record] = [r for r in caplog.records if r.levelno == logging.ERROR and r.exc_info]
    assert record.exc_info is not None
    assert isinstance(record.exc_info[1], RuntimeError)


async def test_unknown_route_returns_404_envelope(client: AsyncClient) -> None:
    response = await client.get("/api/v1/no-such-thing")
    assert response.status_code == 404
    assert response.json()["error"]["code"] == "not_found"
