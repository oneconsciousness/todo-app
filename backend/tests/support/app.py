"""Run an app in-process and talk to it over httpx."""

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from asgi_lifespan import LifespanManager
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient


@asynccontextmanager
async def serving(app: FastAPI, *, raise_app_exceptions: bool = True) -> AsyncIterator[AsyncClient]:
    """Start the app's lifespan and yield a client that sends the app's own Origin.

    httpx's ASGITransport does not run the lifespan, so asgi-lifespan does
    (https://github.com/florimondmanca/asgi-lifespan).
    """
    transport = ASGITransport(app=app, raise_app_exceptions=raise_app_exceptions)
    origin = app.state.settings.app_origin
    async with (
        LifespanManager(app),
        AsyncClient(transport=transport, base_url="http://test", headers={"Origin": origin}) as client,
    ):
        yield client
