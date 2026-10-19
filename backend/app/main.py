"""Build the API app. uvicorn runs it as `app.main:create_app --factory`, so nothing is built at import time."""

import logging
import socket
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from logging.handlers import QueueListener

from fastapi import FastAPI

from app.api.errors import exception_handlers
from app.api.health import health_router
from app.api.router import api_router
from app.config import Settings
from app.db.engine import create_engine, create_sessionmaker
from app.log import configure_logging
from app.middleware import RequestContextMiddleware
from app.security.passwords import HASH_CONCURRENCY, Hasher

log = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    """Create the pool, the session factory and the hasher on start-up; close the pool and flush logs on shutdown.

    The engine opens no connection here, so a database that is down fails `/readyz`, not start-up.
    """
    settings: Settings = app.state.settings
    log_listener: QueueListener = app.state.log_listener
    engine = create_engine(settings)
    app.state.engine = engine
    app.state.sessionmaker = create_sessionmaker(engine)
    app.state.hasher = await Hasher.owasp(concurrency=HASH_CONCURRENCY)
    log.info("api ready", extra={"served_by": socket.gethostname()})
    try:
        yield
    finally:
        log.info("api shutting down")
        await engine.dispose()
        log_listener.stop()


def create_app(settings: Settings | None = None) -> FastAPI:
    """Build the app from `settings`, or from the environment when none are given."""
    settings = settings or Settings()
    log_listener = configure_logging(settings)
    app = FastAPI(
        title="todo-app API",
        docs_url="/api/docs",
        openapi_url="/api/openapi.json",
        redoc_url=None,
        lifespan=lifespan,
        exception_handlers=exception_handlers(),
    )
    app.state.settings = settings
    app.state.log_listener = log_listener
    app.add_middleware(RequestContextMiddleware)
    app.include_router(health_router)
    app.include_router(api_router)
    return app
