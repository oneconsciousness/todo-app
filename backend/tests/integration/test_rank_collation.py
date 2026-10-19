from uuid import UUID, uuid4

import pytest
from sqlalchemy import insert, select
from sqlalchemy.ext.asyncio import AsyncEngine

from app.db.models import Task, User
from tests.support.ranks import seeded_ranks

KEYS = seeded_ranks(500, seed=20261019)


@pytest.fixture
async def owner_of_ranked_tasks(database_engine: AsyncEngine) -> UUID:
    """Store one user's tasks under the seeded keys, and return the user's id."""
    owner = uuid4()
    async with database_engine.begin() as connection:
        await connection.execute(insert(User).values(id=owner, email="ranks@example.com", password_hash="unused"))
        await connection.execute(
            insert(Task),
            [{"id": uuid4(), "owner_id": owner, "title": f"Task {n}", "rank": key} for n, key in enumerate(KEYS)],
        )
    return owner


async def test_postgres_sorts_ranks_like_python(database_engine: AsyncEngine, owner_of_ranked_tasks: UUID) -> None:
    query = select(Task.rank).where(Task.owner_id == owner_of_ranked_tasks).order_by(Task.rank)
    async with database_engine.connect() as connection:
        stored_order = (await connection.scalars(query)).all()
    assert stored_order == sorted(KEYS)


async def test_a_locale_collation_would_misorder_ranks(
    database_engine: AsyncEngine, owner_of_ranked_tasks: UUID
) -> None:
    query = select(Task.rank).where(Task.owner_id == owner_of_ranked_tasks).order_by(Task.rank.collate("und-x-icu"))
    async with database_engine.connect() as connection:
        locale_order = (await connection.scalars(query)).all()
    assert locale_order != sorted(KEYS)
