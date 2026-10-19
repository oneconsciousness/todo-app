"""Sign and check the session token (an HS256 JWT) that the session cookie carries."""

from datetime import UTC, datetime, timedelta
from typing import Final
from uuid import UUID

import jwt

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

    Expiry is checked here against `now` rather than by PyJWT, so a test can set the time.

    Raises:
        NotAuthenticated: when the token is malformed, signed with another key or algorithm,
            lacks a claim, names no valid user id, or has expired.
    """
    try:
        payload = jwt.decode(
            token,
            secret,
            algorithms=[ALGORITHM],
            options={"verify_exp": False, "require": ["sub", "iat", "exp"]},
        )
        claims = SessionClaims(
            user_id=UUID(payload["sub"]),
            issued_at=datetime.fromtimestamp(payload["iat"], UTC),
            expires_at=datetime.fromtimestamp(payload["exp"], UTC),
        )
    except (jwt.InvalidTokenError, ValueError, TypeError, OverflowError) as error:
        raise NotAuthenticated from error
    if claims.expires_at <= now:
        raise NotAuthenticated
    return claims
