"""Request dependencies: settings, the session, the hasher, the signed-in user and the Origin guard."""

import logging
from collections.abc import AsyncIterator
from datetime import UTC, datetime
from typing import Annotated, Final

from fastapi import Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.config import Settings
from app.domain.errors import ForbiddenOrigin, NotAuthenticated
from app.domain.tokens import decode_session
from app.domain.types import SessionClaims
from app.log import user_id_var
from app.security.passwords import Hasher

log = logging.getLogger(__name__)

SESSION_COOKIE: Final = "session"
SAFE_METHODS: Final = frozenset({"GET", "HEAD", "OPTIONS"})


def get_settings(request: Request) -> Settings:
    """Return the settings the app was built with."""
    settings: Settings = request.app.state.settings
    return settings


def get_hasher(request: Request) -> Hasher:
    """Return the app's password hasher, whose semaphore caps hashing per process."""
    hasher: Hasher = request.app.state.hasher
    return hasher


async def get_session(request: Request) -> AsyncIterator[AsyncSession]:
    """Yield one session for this request; its connection goes back to the pool when the session closes."""
    sessionmaker: async_sessionmaker[AsyncSession] = request.app.state.sessionmaker
    async with sessionmaker() as session:
        yield session


SettingsDep = Annotated[Settings, Depends(get_settings)]
HasherDep = Annotated[Hasher, Depends(get_hasher)]
# scope="function" closes the session before the response is sent, not after
# (https://fastapi.tiangolo.com/tutorial/dependencies/dependencies-with-yield/).
SessionDep = Annotated[AsyncSession, Depends(get_session, scope="function")]


async def get_current_user(request: Request, settings: SettingsDep) -> SessionClaims:
    """Return the claims of the request's session cookie, with no database lookup.

    It also sets the user id for the logs. It is async so it runs in the request's own task,
    where the middleware's access line can read that id.

    Raises:
        NotAuthenticated: when the cookie is missing, invalid or expired.
    """
    token = request.cookies.get(SESSION_COOKIE)
    if token is None:
        log.warning("not authenticated", extra={"where": "app.api.deps.get_current_user", "reason": "no_cookie"})
        raise NotAuthenticated
    try:
        claims = decode_session(token, now=datetime.now(UTC), secret=settings.jwt_secret.get_secret_value())
    except NotAuthenticated:
        log.warning("not authenticated", extra={"where": "app.api.deps.get_current_user", "reason": "bad_token"})
        raise
    user_id_var.set(str(claims.user_id))
    return claims


CurrentUserDep = Annotated[SessionClaims, Depends(get_current_user)]


async def require_trusted_origin(request: Request, settings: SettingsDep) -> None:
    """Refuse a write whose Origin header names another site, including the literal `null`.

    Browsers always send Origin on a write (https://fetch.spec.whatwg.org/#append-a-request-origin-header),
    so a write without one comes from a script, which cannot ride a user's cookie.

    Raises:
        ForbiddenOrigin: when a write's Origin is present and is not the app's own.
    """
    origin = request.headers.get("origin")
    if request.method not in SAFE_METHODS and origin is not None and origin != settings.app_origin:
        log.warning(
            "write from another origin refused",
            extra={"where": "app.api.deps.require_trusted_origin", "origin": origin, "then": 403},
        )
        raise ForbiddenOrigin
