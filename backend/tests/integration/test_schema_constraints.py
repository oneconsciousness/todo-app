from uuid import uuid4

import pytest
from sqlalchemy import insert
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncEngine

from app.db.models import User


@pytest.mark.parametrize(
    "email", ["no-at.example.com", "a@b@example.com", "a b@example.com", "@example.com", "a@example"]
)
async def test_database_rejects_a_malformed_email_inserted_directly(database_engine: AsyncEngine, email: str) -> None:
    with pytest.raises(IntegrityError, match="ck_users_email_shape"):
        async with database_engine.begin() as connection:
            await connection.execute(insert(User).values(id=uuid4(), email=email, password_hash="unused"))


async def test_database_accepts_an_internationalised_email(database_engine: AsyncEngine) -> None:
    async with database_engine.begin() as connection:
        result = await connection.execute(
            insert(User).values(id=uuid4(), email="josé@exämple.com", password_hash="unused")
        )
    assert result.rowcount == 1
