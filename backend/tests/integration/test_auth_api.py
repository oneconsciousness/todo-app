import dataclasses
from datetime import UTC, datetime, timedelta
from http.cookies import SimpleCookie
from typing import Literal
from uuid import UUID

import pytest
from argon2 import PasswordHasher
from fastapi import FastAPI
from httpx import AsyncClient, Response
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncEngine

from app.config import Settings
from app.db.models import User
from app.domain.tokens import SESSION_LIFETIME, encode_session
from tests.support.app import client_for
from tests.support.factories import PASSWORD

REGISTER = "/api/v1/auth/register"
LOGIN = "/api/v1/auth/login"
LOGOUT = "/api/v1/auth/logout"
ME = "/api/v1/auth/me"


def session_cookie(response: Response) -> SimpleCookie:
    """Parse the response's Set-Cookie header for the session cookie."""
    cookie: SimpleCookie = SimpleCookie()
    cookie.load(response.headers["set-cookie"])
    return cookie


async def register(client: AsyncClient, email: str = "ada@example.com", password: str = PASSWORD) -> Response:
    """Send a sign-up request."""
    return await client.post(REGISTER, json={"email": email, "password": password})


async def test_register_creates_account_and_signs_in(client: AsyncClient) -> None:
    response = await register(client)
    session = session_cookie(response)["session"]
    assert response.status_code == 201
    assert response.headers["Location"] == "/api/v1/auth/me"
    assert response.json().keys() == {"id", "email"}
    assert (session["path"], session["max-age"], session["httponly"]) == ("/api", "28800", True)
    assert session["samesite"].lower() == "strict"
    assert not session["secure"]


async def test_register_rejects_a_short_password_with_400_envelope(client: AsyncClient) -> None:
    response = await register(client, password="too-short")
    assert response.status_code == 400
    assert response.json()["error"]["code"] == "validation_failed"
    assert response.json()["error"]["details"][0]["field"] == "password"


@pytest.mark.parametrize(
    "email",
    [
        "no-at-sign.example.com",
        "two@at@example.com",
        "has space@example.com",
        "@example.com",
        "ada@localhost-without-dot",
        # 255 characters: every part is within its own limit, but the whole is one over 254.
        "a" * 64 + "@" + "b" * 63 + "." + "c" * 63 + "." + "d" * 58 + ".com",
    ],
    ids=["no-at", "two-at", "space", "empty-local-part", "domain-without-dot", "255-characters"],
)
async def test_register_rejects_an_invalid_email_with_400(client: AsyncClient, email: str) -> None:
    response = await register(client, email=email)
    assert response.status_code == 400
    assert response.json()["error"]["details"][0]["field"] == "email"


async def test_register_stores_the_normalised_email(client: AsyncClient, database_engine: AsyncEngine) -> None:
    response = await register(client, email="Bob@EXAMPLE.com")
    async with database_engine.connect() as connection:
        stored = await connection.scalar(select(User.email).where(User.id == UUID(response.json()["id"])))
    assert (response.json()["email"], stored) == ("Bob@example.com", "Bob@example.com")


async def test_register_rejects_an_email_taken_in_another_case_with_409(client: AsyncClient) -> None:
    await register(client, email="bob@example.com")
    response = await register(client, email="BOB@example.com")
    assert response.status_code == 409
    assert response.json()["error"]["code"] == "email_taken"
    assert response.json()["error"]["details"][0]["field"] == "email"


async def test_login_sets_the_session_cookie(app: FastAPI) -> None:
    async with client_for(app) as signing_up, client_for(app) as signing_in:
        await register(signing_up)
        response = await signing_in.post(LOGIN, json={"email": "ada@example.com", "password": PASSWORD})
        me = await signing_in.get(ME)
    assert response.status_code == 200
    assert session_cookie(response)["session"]["path"] == "/api"
    assert me.json()["email"] == "ada@example.com"


async def test_login_matches_the_email_in_any_letter_case(client: AsyncClient) -> None:
    await register(client, email="ada@example.com")
    response = await client.post(LOGIN, json={"email": "ADA@EXAMPLE.COM", "password": PASSWORD})
    assert response.status_code == 200
    assert response.json()["email"] == "ada@example.com"


async def test_login_rejects_a_wrong_password_with_401(client: AsyncClient) -> None:
    await register(client)
    response = await client.post(LOGIN, json={"email": "ada@example.com", "password": "wrong horse battery"})
    assert response.status_code == 401
    assert response.json()["error"]["code"] == "invalid_credentials"


async def test_login_gives_unknown_email_the_same_401_as_a_wrong_password(client: AsyncClient) -> None:
    await register(client)
    wrong_password = await client.post(LOGIN, json={"email": "ada@example.com", "password": "wrong horse battery"})
    unknown_email = await client.post(LOGIN, json={"email": "nobody@example.com", "password": PASSWORD})
    assert (unknown_email.status_code, unknown_email.json()) == (wrong_password.status_code, wrong_password.json())


class CountingPasswordHasher(PasswordHasher):
    """argon2 at the library boundary, counting how many hashes it checks."""

    def __init__(self) -> None:
        super().__init__()
        self.verifications = 0

    def verify(self, hash: str | bytes, password: str | bytes) -> Literal[True]:
        self.verifications += 1
        return super().verify(hash, password)


async def test_login_checks_one_hash_whether_the_email_is_unknown_or_the_password_wrong(
    app: FastAPI, client: AsyncClient
) -> None:
    await register(client)
    counting = CountingPasswordHasher()
    app.state.hasher = dataclasses.replace(app.state.hasher, hasher=counting)
    await client.post(LOGIN, json={"email": "nobody@example.com", "password": PASSWORD})
    after_unknown_email = counting.verifications
    await client.post(LOGIN, json={"email": "ada@example.com", "password": "wrong horse battery"})
    assert (after_unknown_email, counting.verifications) == (1, 2)


async def test_login_rejects_a_malformed_body_with_400(client: AsyncClient) -> None:
    response = await client.post(LOGIN, json={"email": "ada@example.com"})
    assert response.status_code == 400
    assert response.json()["error"]["details"][0]["field"] == "password"


async def test_logout_clears_the_session_cookie(client: AsyncClient) -> None:
    await register(client)
    response = await client.post(LOGOUT)
    me = await client.get(ME)
    assert response.status_code == 204
    assert session_cookie(response)["session"]["max-age"] == "0"
    assert me.status_code == 401


async def test_me_returns_the_signed_in_user(client: AsyncClient) -> None:
    registered = await register(client)
    response = await client.get(ME)
    assert (response.status_code, response.json()) == (200, registered.json())


async def test_me_without_a_session_returns_401(client: AsyncClient) -> None:
    response = await client.get(ME)
    assert response.status_code == 401
    assert response.json()["error"]["code"] == "not_authenticated"


async def test_me_for_a_deleted_account_returns_401(client: AsyncClient, database_engine: AsyncEngine) -> None:
    user_id = UUID((await register(client)).json()["id"])
    async with database_engine.begin() as connection:
        await connection.execute(delete(User).where(User.id == user_id))
    response = await client.get(ME)
    assert response.status_code == 401
    assert response.json()["error"]["code"] == "not_authenticated"


async def test_me_with_an_expired_token_returns_401(client: AsyncClient, test_settings: Settings) -> None:
    user_id = UUID((await register(client)).json()["id"])
    issued = datetime.now(UTC) - SESSION_LIFETIME - timedelta(seconds=1)
    expired = encode_session(user_id, now=issued, secret=test_settings.jwt_secret.get_secret_value())
    client.cookies.clear()
    response = await client.get(ME, headers={"Cookie": f"session={expired}"})
    assert response.status_code == 401


async def test_me_with_a_tampered_token_returns_401(client: AsyncClient) -> None:
    token = session_cookie(await register(client))["session"].value
    header, payload, signature = token.split(".")
    tampered = ".".join([header, payload, signature[::-1]])
    client.cookies.clear()
    response = await client.get(ME, headers={"Cookie": f"session={tampered}"})
    assert response.status_code == 401
