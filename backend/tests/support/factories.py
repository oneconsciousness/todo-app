"""Build signed-in users through the real API."""

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from uuid import uuid4

from fastapi import FastAPI
from httpx import AsyncClient

from tests.support.app import client_for

PASSWORD = "correct horse battery staple"


@asynccontextmanager
async def signed_in_client(app: FastAPI, email: str | None = None) -> AsyncIterator[AsyncClient]:
    """Register a fresh user on a running app and yield a client that keeps its session cookie."""
    async with client_for(app) as client:
        response = await client.post(
            "/api/v1/auth/register", json={"email": email or f"user-{uuid4().hex}@example.com", "password": PASSWORD}
        )
        response.raise_for_status()
        yield client
