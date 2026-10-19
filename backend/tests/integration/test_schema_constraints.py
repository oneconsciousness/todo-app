from uuid import uuid4

import pytest
from sqlalchemy import insert
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession

from app.db.models import User
from app.db.users import insert_user


@pytest.mark.parametrize(
    "email", ["no-at.example.com", "a@b@example.com", "a b@example.com", "@example.com", "a@example"]
)
async def test_database_rejects_a_malformed_email_inserted_directly(database_engine: AsyncEngine, email: str) -> None:
    with pytest.raises(IntegrityError, match="ck_users_email_shape"):
        async with database_engine.begin() as connection:
            await connection.execute(insert(User).values(id=uuid4(), email=email, password_hash="unused"))


async def test_a_constraint_failure_other_than_a_taken_email_is_not_reported_as_taken(
    database_engine: AsyncEngine,
) -> None:
    # Only the unique email index means "taken"; any other failure is a server bug and must surface as one.
    async with AsyncSession(database_engine) as session, session.begin():
        with pytest.raises(IntegrityError, match="ck_users_email_shape"):
            await insert_user(session, uuid4(), "no-at-sign.example.com", "unused")


async def test_database_accepts_an_internationalised_email(database_engine: AsyncEngine) -> None:
    async with database_engine.begin() as connection:
        result = await connection.execute(
            insert(User).values(id=uuid4(), email="josé@exämple.com", password_hash="unused")
        )
    assert result.rowcount == 1
