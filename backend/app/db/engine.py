"""The connection pool and the session factory."""

from typing import Final

from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker, create_async_engine

from app.config import Settings

# Applied by asyncpg to every new connection, so they hold on any Postgres without server flags
# (https://magicstack.github.io/asyncpg/current/api/index.html#connection).
SERVER_SETTINGS: Final = {"statement_timeout": "5000", "idle_in_transaction_session_timeout": "10000"}


def create_engine(settings: Settings) -> AsyncEngine:
    """Build the pool; no connection opens until the first query, so an unreachable database never fails start-up."""
    return create_async_engine(
        str(settings.database_url),
        pool_size=settings.db_pool_size,
        max_overflow=settings.db_max_overflow,
        pool_timeout=settings.db_pool_timeout_seconds,
        pool_pre_ping=True,
        connect_args={"server_settings": SERVER_SETTINGS},
    )


def create_sessionmaker(engine: AsyncEngine) -> async_sessionmaker[AsyncSession]:
    """Build the per-request session factory; rows leave as plain records, so nothing reloads after commit."""
    return async_sessionmaker(engine, expire_on_commit=False)
