import asyncio
import os
from collections.abc import AsyncIterator

import pytest
from fastapi import FastAPI
from httpx import AsyncClient
from sqlalchemy import URL, make_url, text
from sqlalchemy.ext.asyncio import AsyncEngine, create_async_engine
from sqlalchemy.pool import NullPool

from app.config import Settings
from app.main import create_app
from tests.support.app import serving
from tests.support.database import TEST_DATABASE, migrate, recreate_test_database

# The server and its maintenance database; the suite builds its own database beside it.
# The default is the compose `test-db` service.
TEST_DATABASE_URL = os.environ.get(
    "TEST_DATABASE_URL", "postgresql+asyncpg://todo_test:todo_test@127.0.0.1:55432/postgres"
)
SIGNING_KEY = "integration-test-signing-key-0123456789abcdef"


@pytest.fixture(scope="session")
def database_url() -> URL:
    """Rebuild the test database from the migrations once per run, and return its URL."""
    server_url = make_url(TEST_DATABASE_URL)
    asyncio.run(recreate_test_database(server_url))
    url = server_url.set(database=TEST_DATABASE)
    migrate(url)
    return url


@pytest.fixture(scope="session")
async def database_engine(database_url: URL) -> AsyncIterator[AsyncEngine]:
    """An engine for test setup and checks, outside any app."""
    engine = create_async_engine(database_url, poolclass=NullPool)
    yield engine
    await engine.dispose()


@pytest.fixture(autouse=True)
async def empty_tables(database_engine: AsyncEngine) -> None:
    """Empty both tables before each test, so a crashed run leaves nothing behind for the next one."""
    async with database_engine.begin() as connection:
        await connection.execute(text("TRUNCATE users, tasks CASCADE"))


@pytest.fixture(scope="session")
def test_settings(database_url: URL) -> Settings:
    """Settings that point the app at the test database."""
    return Settings(database_url=database_url.render_as_string(hide_password=False), jwt_secret=SIGNING_KEY)


@pytest.fixture
def app(test_settings: Settings) -> FastAPI:
    """A fresh app built from the test settings."""
    return create_app(test_settings)


@pytest.fixture
async def client(app: FastAPI) -> AsyncIterator[AsyncClient]:
    """A client for the running app; each request gets its own session and pooled connection."""
    async with serving(app) as client:
        yield client
