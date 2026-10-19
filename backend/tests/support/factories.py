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


async def create_tasks(client: AsyncClient, titles: Sequence[str]) -> list[TaskRead]:
    """Create one task per title, in order, through the API; each new task lands at the top of the list."""
    created = []
    for title in titles:
        response = await client.post("/api/v1/tasks", json={"title": title})
        response.raise_for_status()
        created.append(TaskRead.model_validate(response.json()))
    return created
