from datetime import UTC, datetime, timedelta
from uuid import uuid4

import jwt
import pytest

from app.domain.errors import NotAuthenticated
from app.domain.tokens import SESSION_LIFETIME, decode_session, encode_session

SIGNING_KEY = "unit-test-signing-key-0123456789abcdef"
ISSUED = datetime(2026, 1, 5, 9, 0, tzinfo=UTC)


def test_session_token_round_trips_the_user_id() -> None:
    user_id = uuid4()
    token = encode_session(user_id, now=ISSUED, secret=SIGNING_KEY)
    assert decode_session(token, now=ISSUED + timedelta(hours=1), secret=SIGNING_KEY).user_id == user_id


def test_expired_token_is_rejected() -> None:
    token = encode_session(uuid4(), now=ISSUED, secret=SIGNING_KEY)
    with pytest.raises(NotAuthenticated):
        decode_session(token, now=ISSUED + SESSION_LIFETIME, secret=SIGNING_KEY)


def test_token_signed_with_another_secret_is_rejected() -> None:
    token = encode_session(uuid4(), now=ISSUED, secret="another-signing-key-0123456789abcdef")
    with pytest.raises(NotAuthenticated):
        decode_session(token, now=ISSUED, secret=SIGNING_KEY)


def test_unsigned_alg_none_token_is_rejected() -> None:
    claims = {"sub": str(uuid4()), "iat": ISSUED, "exp": ISSUED + SESSION_LIFETIME}
    token = jwt.encode(claims, key=None, algorithm="none")
    with pytest.raises(NotAuthenticated):
        decode_session(token, now=ISSUED, secret=SIGNING_KEY)


@pytest.mark.parametrize("subject", [None, "not-a-uuid"], ids=["missing", "not-a-uuid"])
def test_token_without_sub_is_rejected(subject: str | None) -> None:
    claims = {"sub": subject, "iat": ISSUED, "exp": ISSUED + SESSION_LIFETIME}
    token = jwt.encode({k: v for k, v in claims.items() if v is not None}, SIGNING_KEY, algorithm="HS256")
    with pytest.raises(NotAuthenticated):
        decode_session(token, now=ISSUED, secret=SIGNING_KEY)
