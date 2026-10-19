"""Sign-up, sign-in, sign-out and the current user."""

from datetime import UTC, datetime
from typing import Final
from uuid import UUID

from fastapi import APIRouter, Response, status

from app.api.deps import SESSION_COOKIE, CurrentUserDep, HasherDep, SessionDep, SettingsDep
from app.api.schemas import Credentials, ErrorEnvelope, UserRead
from app.config import Settings
from app.domain.tokens import SESSION_LIFETIME, encode_session
from app.services import auth as auth_service

COOKIE_PATH: Final = "/api"

auth_router = APIRouter(prefix="/auth", tags=["auth"])


def set_session_cookie(response: Response, user_id: UUID, settings: Settings) -> None:
    """Attach a fresh session cookie: readable only by the server, sent only to the API, never cross-site."""
    token = encode_session(user_id, now=datetime.now(UTC), secret=settings.jwt_secret.get_secret_value())
    response.set_cookie(
        SESSION_COOKIE,
        token,
        max_age=int(SESSION_LIFETIME.total_seconds()),
        path=COOKIE_PATH,
        secure=settings.cookie_secure,
        httponly=True,
        samesite="strict",
    )


@auth_router.post(
    "/register",
    status_code=status.HTTP_201_CREATED,
    responses={400: {"model": ErrorEnvelope}, 409: {"model": ErrorEnvelope}},
)
async def register(
    credentials: Credentials, response: Response, session: SessionDep, hasher: HasherDep, settings: SettingsDep
) -> UserRead:
    """Create an account and sign it in."""
    user = await auth_service.register(session, hasher, credentials)
    set_session_cookie(response, user.id, settings)
    response.headers["Location"] = "/api/v1/auth/me"
    return UserRead.model_validate(user, from_attributes=True)


@auth_router.post("/login", responses={400: {"model": ErrorEnvelope}, 401: {"model": ErrorEnvelope}})
async def login(
    credentials: Credentials, response: Response, session: SessionDep, hasher: HasherDep, settings: SettingsDep
) -> UserRead:
    """Sign in with email and password."""
    user = await auth_service.authenticate(session, hasher, credentials)
    set_session_cookie(response, user.id, settings)
    return UserRead.model_validate(user, from_attributes=True)


@auth_router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
async def logout(response: Response, settings: SettingsDep) -> None:
    """Clear the session cookie; this needs no session, so signing out never fails."""
    response.delete_cookie(
        SESSION_COOKIE, path=COOKIE_PATH, secure=settings.cookie_secure, httponly=True, samesite="strict"
    )


@auth_router.get("/me", responses={401: {"model": ErrorEnvelope}})
async def me(claims: CurrentUserDep, session: SessionDep) -> UserRead:
    """Return the signed-in user."""
    user = await auth_service.current_user(session, claims.user_id)
    return UserRead.model_validate(user, from_attributes=True)
