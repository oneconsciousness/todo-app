import asyncio

import pytest
from fastapi import FastAPI, Request
from httpx import AsyncClient
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker

from app.config import Settings
from app.db.engine import create_engine
from app.main import create_app
from tests.support.app import serving
from tests.support.factories import PASSWORD

# Nothing listens on port 1, so every connection attempt is refused at once.
UNREACHABLE_DATABASE_URL = "postgresql+asyncpg://todo_test:todo_test@127.0.0.1:1/todo_test"


# The .invalid top-level domain is reserved and never resolves (RFC 2606).
UNRESOLVABLE_DATABASE_URL = "postgresql+asyncpg://todo_test:todo_test@database.invalid:5432/todo_test"
# asyncpg's own connect timeout is 60 s; the app's answer must come long before that.
PROMPT_ANSWER_SECONDS = 10


@pytest.fixture
def unreachable_settings(test_settings: Settings) -> Settings:
    """The test settings, pointed at a database that refuses connections."""
    return Settings(database_url=UNREACHABLE_DATABASE_URL, jwt_secret=test_settings.jwt_secret.get_secret_value())


@pytest.fixture
def unresolvable_settings(test_settings: Settings) -> Settings:
    """The test settings, pointed at a database host name that does not resolve."""
    return Settings(database_url=UNRESOLVABLE_DATABASE_URL, jwt_secret=test_settings.jwt_secret.get_secret_value())


def add_database_ping_route(app: FastAPI) -> None:
    """Add a test-only route that runs one query through a request session from the app's pool."""

    async def ping_database(request: Request) -> dict[str, int]:
        sessionmaker: async_sessionmaker[AsyncSession] = request.app.state.sessionmaker
        async with sessionmaker() as session:
            return {"result": (await session.execute(text("SELECT 1"))).scalar_one()}

    app.add_api_route("/api/v1/test-only/ping-database", ping_database)


async def test_livez_answers_without_a_database(unreachable_settings: Settings) -> None:
    async with serving(create_app(unreachable_settings)) as client:
        response = await client.get("/livez")
    assert (response.status_code, response.json()) == (200, {"status": "alive"})


async def test_readyz_is_200_when_the_database_answers(client: AsyncClient) -> None:
    response = await client.get("/readyz")
    assert (response.status_code, response.json()) == (200, {"status": "ready"})


async def test_readyz_is_503_when_the_database_is_unreachable(unreachable_settings: Settings) -> None:
    async with serving(create_app(unreachable_settings)) as client:
        response = await client.get("/readyz")
    assert response.status_code == 503
    assert response.json()["error"]["code"] == "not_ready"


async def test_readyz_is_503_promptly_when_the_database_host_does_not_resolve(
    unresolvable_settings: Settings,
) -> None:
    async with asyncio.timeout(PROMPT_ANSWER_SECONDS), serving(create_app(unresolvable_settings)) as client:
        response = await client.get("/readyz")
    assert response.status_code == 503
    assert response.json()["error"]["code"] == "not_ready"


async def test_sign_in_is_503_promptly_when_the_database_host_does_not_resolve(
    unresolvable_settings: Settings,
) -> None:
    credentials = {"email": "ada@example.com", "password": PASSWORD}
    async with asyncio.timeout(PROMPT_ANSWER_SECONDS), serving(create_app(unresolvable_settings)) as client:
        response = await client.post("/api/v1/auth/login", json=credentials)
    assert response.status_code == 503
    assert response.json()["error"]["code"] == "service_unavailable"


async def test_request_is_503_when_no_connection_frees_up_in_time(test_settings: Settings) -> None:
    tiny_pool = test_settings.model_copy(
        update={"db_pool_size": 1, "db_max_overflow": 0, "db_pool_timeout_seconds": 0.2}
    )
    app = create_app(tiny_pool)
    add_database_ping_route(app)
    async with serving(app) as client:
        engine: AsyncEngine = app.state.engine
        async with engine.connect():
            response = await client.get("/api/v1/test-only/ping-database")
    assert response.status_code == 503
    assert response.json()["error"]["code"] == "service_unavailable"


async def test_pooled_connections_carry_both_timeouts(test_settings: Settings) -> None:
    engine = create_engine(test_settings)
    async with engine.connect() as connection:
        statement_timeout = (await connection.execute(text("SHOW statement_timeout"))).scalar_one()
        idle_timeout = (await connection.execute(text("SHOW idle_in_transaction_session_timeout"))).scalar_one()
    await engine.dispose()
    assert (statement_timeout, idle_timeout) == ("5s", "10s")
