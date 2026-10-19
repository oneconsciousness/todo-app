"""Liveness and readiness probes, served at the root and never routed by the proxy."""

import asyncio
import logging
from typing import Final

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncEngine

from app.api.errors import DATABASE_ERRORS, HttpError, error_response
from app.api.schemas import ErrorEnvelope, ProbeStatus

log = logging.getLogger(__name__)

READINESS_TIMEOUT_SECONDS: Final = 1.0
NOT_READY: Final = HttpError(503, "not_ready", "The service cannot reach its database.")

health_router = APIRouter()


@health_router.get("/livez")
async def livez() -> ProbeStatus:
    """Answer from the event loop alone, so a live process always says so."""
    return ProbeStatus(status="alive")


@health_router.get("/readyz", response_model=ProbeStatus, responses={503: {"model": ErrorEnvelope}})
async def readyz(request: Request) -> ProbeStatus | JSONResponse:
    """Answer 200 only when the database runs a query within a second."""
    engine: AsyncEngine = request.app.state.engine
    try:
        async with asyncio.timeout(READINESS_TIMEOUT_SECONDS), engine.connect() as connection:
            await connection.execute(text("SELECT 1"))
    except (TimeoutError, *DATABASE_ERRORS) as error:
        log.warning(
            "not ready",
            extra={"where": "app.api.health.readyz", "why": type(error).__name__, "then": NOT_READY.status},
        )
        return error_response(NOT_READY)
    return ProbeStatus(status="ready")
