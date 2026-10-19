"""Sign-up, sign-in and the current user. Each use case opens its one transaction itself."""

import logging
from typing import Final
from uuid import UUID, uuid4

from sqlalchemy.ext.asyncio import AsyncSession

from app.api.schemas import Credentials
from app.db.users import find_user_by_email, get_user, insert_user
from app.domain.errors import InvalidCredentials, NotAuthenticated
from app.domain.types import UserRecord
from app.security.passwords import Hasher

log = logging.getLogger(__name__)

# The hash of a random value nobody knows. Checking a password against it for an unknown email
# costs the same as a real check, so response time does not reveal which emails have accounts.
DUMMY_HASH: Final = "$argon2id$v=19$m=19456,t=2,p=1$COS/m1E55HOrmFZrv2XgLA$DLIezVqc3Aa8H/vWqPfm8NRDDhwrcNfJQ0+hLyYKG7I"


async def register(session: AsyncSession, hasher: Hasher, credentials: Credentials) -> UserRecord:
    """Create an account.

    The password is hashed before the transaction opens, so no pooled connection waits on a hash.

    Raises:
        EmailTaken: when the email already has an account.
    """
    password_hash = await hasher.hash(credentials.password)
    async with session.begin():
        return await insert_user(session, uuid4(), credentials.email, password_hash)


async def authenticate(session: AsyncSession, hasher: Hasher, credentials: Credentials) -> UserRecord:
    """Return the user whose email and password match.

    The lookup's transaction ends before the hash check, so the connection is back in the pool
    while the password is checked.

    Raises:
        InvalidCredentials: for an unknown email or a wrong password, alike.
    """
    async with session.begin():
        user = await find_user_by_email(session, credentials.email)
    if user is None:
        await hasher.verify(DUMMY_HASH, credentials.password)
        log.warning("sign-in refused", extra={"where": "app.services.auth.authenticate", "reason": "unknown_email"})
        raise InvalidCredentials
    if not await hasher.verify(user.password_hash, credentials.password):
        log.warning(
            "sign-in refused",
            extra={"where": "app.services.auth.authenticate", "reason": "wrong_password", "user_id": str(user.id)},
        )
        raise InvalidCredentials
    return user


async def current_user(session: AsyncSession, user_id: UUID) -> UserRecord:
    """Return the user a valid session names.

    Raises:
        NotAuthenticated: when that account no longer exists.
    """
    async with session.begin():
        user = await get_user(session, user_id)
    if user is None:
        raise NotAuthenticated
    return user
