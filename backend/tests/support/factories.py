"""Build signed-in users through the real API."""

from collections.abc import AsyncIterator, Sequence
from contextlib import asynccontextmanager
from uuid import uuid4

from fastapi import FastAPI
from httpx import AsyncClient

from app.api.schemas import TaskRead
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


async def create_task(client: AsyncClient, title: str) -> TaskRead:
    """Create one task through the API; it lands at the top of the list."""
    response = await client.post("/api/v1/tasks", json={"title": title})
    response.raise_for_status()
    return TaskRead.model_validate(response.json())


async def create_tasks(client: AsyncClient, titles: Sequence[str]) -> list[TaskRead]:
    """Create one task per title, one after another, so the last title ends up at the top."""
    return [await create_task(client, title) for title in titles]
