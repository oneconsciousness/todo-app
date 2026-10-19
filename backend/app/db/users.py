"""Queries on the users table."""

from uuid import UUID

from asyncpg import UniqueViolationError
from sqlalchemy import insert, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import User
from app.domain.errors import EmailTaken
from app.domain.types import UserRecord


def is_email_taken(error: IntegrityError) -> bool:
    """Tell a duplicate email apart from any other constraint failure, which stays a server error."""
    # SQLAlchemy keeps asyncpg's own exception, which names the constraint, as the cause.
    cause = error.orig.__cause__ if error.orig is not None else None
    if not isinstance(cause, UniqueViolationError):
        return False
    constraint: object = cause.constraint_name
    return constraint == "uq_users_email"


async def insert_user(session: AsyncSession, user_id: UUID, email: str, password_hash: str) -> UserRecord:
    """Insert a user and return the stored row.

    Raises:
        EmailTaken: when the unique email index already holds this address, in any letter case.
    """
    statement = insert(User).values(id=user_id, email=email, password_hash=password_hash).returning(User)
    try:
        user = (await session.scalars(statement)).one()
    except IntegrityError as error:
        if is_email_taken(error):
            raise EmailTaken from error
        raise
    return UserRecord.model_validate(user)


async def find_user_by_email(session: AsyncSession, email: str) -> UserRecord | None:
    """Return the user with this email, compared without regard to letter case, or `None`."""
    user = await session.scalar(select(User).where(User.email == email))
    return UserRecord.model_validate(user) if user is not None else None


async def get_user(session: AsyncSession, user_id: UUID) -> UserRecord | None:
    """Return the user with this id, or `None`."""
    user = await session.get(User, user_id)
    return UserRecord.model_validate(user) if user is not None else None
