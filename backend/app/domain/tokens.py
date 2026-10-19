"""Sign and check the session token (an HS256 JWT) that the session cookie carries."""

from datetime import datetime, timedelta
from typing import Final
from uuid import UUID

import jwt
from pydantic import ValidationError

from app.domain.errors import NotAuthenticated
from app.domain.types import SessionClaims

SESSION_LIFETIME: Final = timedelta(hours=8)
ALGORITHM: Final = "HS256"


def encode_session(user_id: UUID, *, now: datetime, secret: str) -> str:
    """Return a signed token for the user, issued at `now` and valid for `SESSION_LIFETIME`."""
    claims = {"sub": str(user_id), "iat": now, "exp": now + SESSION_LIFETIME}
    return jwt.encode(claims, secret, algorithm=ALGORITHM)


def decode_session(token: str, *, now: datetime, secret: str) -> SessionClaims:
    """Return the claims of a token signed with `secret` that has not expired at `now`.

    PyJWT's own time checks read the wall clock, so they are off and expiry is checked against `now`
    (https://pyjwt.readthedocs.io/en/stable/api.html#jwt.decode).

    Raises:
        NotAuthenticated: when the token is malformed, signed with another key or algorithm,
            lacks a claim, names no valid user id, or has expired.
    """
    try:
        payload = jwt.decode(
            token,
            secret,
            algorithms=[ALGORITHM],
            options={"verify_exp": False, "verify_iat": False, "require": ["sub", "iat", "exp"]},
        )
        claims = SessionClaims.model_validate(payload)
    except (jwt.InvalidTokenError, ValidationError) as error:
        raise NotAuthenticated from error
    if claims.expires_at <= now:
        raise NotAuthenticated
    return claims
