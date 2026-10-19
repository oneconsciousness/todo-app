"""Each test fires its requests together, so Postgres sees them as separate, concurrent transactions.

Every request gets its own session and pooled connection, so N requests started in one TaskGroup are N
transactions racing in the database, exactly as they would from N browser tabs.
"""

import asyncio
import random
from collections.abc import Coroutine, Sequence
from typing import Any
from uuid import UUID

from fastapi import FastAPI
from httpx import AsyncClient, Response
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession

from app.api.schemas import TaskList, TaskRead
from app.db import tasks as task_rows
from app.db.models import User
from tests.support.app import client_for
from tests.support.factories import PASSWORD, create_tasks, signed_in_client

TASKS = "/api/v1/tasks"
# A request blocked behind another user's order lock would wait this long before the test gives up.
UNBLOCKED_WITHIN_SECONDS = 2


async def all_at_once(requests: Sequence[Coroutine[Any, Any, Response]]) -> list[Response]:
    """Start every request together and return their responses in the same order."""
    async with asyncio.TaskGroup() as group:
        running = [group.create_task(request) for request in requests]
    return [task.result() for task in running]


async def listed(client: AsyncClient) -> list[TaskRead]:
    """Return the signed-in user's tasks as listed."""
    return TaskList.model_validate((await client.get(TASKS)).json()).items


def assert_ranks_unique_and_in_order(items: Sequence[TaskRead]) -> None:
    """Check no two tasks share a rank and the list comes back in rank order."""
    ranks = [item.rank for item in items]
    assert len(set(ranks)) == len(ranks)
    assert ranks == sorted(ranks)


def random_moves(task_ids: Sequence[UUID], count: int, seed: int) -> list[tuple[UUID, UUID | None]]:
    """Return `count` moves: each a task and the task to put it after (or None for the top), never itself."""
    generator = random.Random(seed)
    tasks = [generator.choice(task_ids) for _ in range(count)]
    return [(task, generator.choice([None, *(other for other in task_ids if other != task)])) for task in tasks]


def move(client: AsyncClient, task_id: UUID, after_id: UUID | None) -> Coroutine[Any, Any, Response]:
    """Build the request that moves a task."""
    return client.put(f"{TASKS}/{task_id}/position", json={"afterId": str(after_id) if after_id else None})


async def test_race_twenty_signups_with_one_email_yield_one_201(
    client: AsyncClient, database_engine: AsyncEngine
) -> None:
    # The same address, in twenty different letter cases.
    emails = [
        "".join(ch.upper() if n >> i & 1 else ch for i, ch in enumerate("racer")) + "@example.com" for n in range(20)
    ]
    responses = await all_at_once(
        [client.post("/api/v1/auth/register", json={"email": e, "password": PASSWORD}) for e in emails]
    )
    async with database_engine.connect() as connection:
        accounts = await connection.scalar(select(func.count()).select_from(User))
    assert sorted(response.status_code for response in responses) == [201] + [409] * 19
    assert accounts == 1


async def test_race_fifty_concurrent_moves_keep_ranks_unique(app: FastAPI) -> None:
    async with signed_in_client(app) as client:
        tasks = await create_tasks(client, [f"task {n}" for n in range(10)])
        task_ids = [task.id for task in tasks]
        responses = await all_at_once([move(client, task, after) for task, after in random_moves(task_ids, 50, seed=1)])
        items = await listed(client)
    assert [response.status_code for response in responses] == [200] * 50
    assert {item.id for item in items} == set(task_ids)
    assert_ranks_unique_and_in_order(items)


async def test_race_creates_and_moves_together_keep_ranks_unique(app: FastAPI) -> None:
    async with signed_in_client(app) as client:
        tasks = await create_tasks(client, [f"task {n}" for n in range(10)])
        moves = [move(client, task, after) for task, after in random_moves([task.id for task in tasks], 30, seed=2)]
        creates = [client.post(TASKS, json={"title": f"new {n}"}) for n in range(20)]
        responses = await all_at_once([*creates, *moves])
        items = await listed(client)
    assert all(200 <= response.status_code < 300 for response in responses)
    assert len(items) == 30
    assert_ranks_unique_and_in_order(items)


async def test_race_other_users_are_never_blocked_by_the_order_lock(app: FastAPI, database_engine: AsyncEngine) -> None:
    async with signed_in_client(app) as ada, client_for(app) as bob:
        ada_id = UUID((await ada.get("/api/v1/auth/me")).json()["id"])
        await bob.post("/api/v1/auth/register", json={"email": "bob@example.com", "password": PASSWORD})
        async with AsyncSession(database_engine) as session, session.begin():
            # Hold Ada's order lock, as one of her creates or moves would, until this block ends.
            await task_rows.lock_task_order(session, ada_id)
            async with asyncio.timeout(UNBLOCKED_WITHIN_SECONDS):
                response = await bob.post(TASKS, json={"title": "Bob is not kept waiting"})
    assert response.status_code == 201


async def test_race_two_patches_on_one_version_yield_one_412(app: FastAPI) -> None:
    async with signed_in_client(app) as client:
        [task] = await create_tasks(client, ["Buy milk"])
        path = f"{TASKS}/{task.id}"
        edits = [
            client.patch(path, json={"title": title}, headers={"If-Match": '"1"'}) for title in ("tab one", "tab two")
        ]
        responses = await all_at_once(edits)
        final = (await client.get(path)).json()
    assert sorted(response.status_code for response in responses) == [200, 412]
    assert final["version"] == 2
