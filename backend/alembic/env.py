"""Run migrations against the database named by DATABASE_URL, using the async driver."""

import asyncio
from logging.config import fileConfig

from sqlalchemy import Connection, pool
from sqlalchemy.ext.asyncio import create_async_engine

from alembic import context
from app.config import DatabaseSettings

if context.config.config_file_name is not None:
    fileConfig(context.config.config_file_name)


def run_migrations(connection: Connection) -> None:
    """Apply the pending migrations on one connection, in one transaction."""
    context.configure(connection=connection, target_metadata=None)
    with context.begin_transaction():
        context.run_migrations()


async def run_async_migrations() -> None:
    """Open one connection, run the migrations through it, and close it.

    Migrations are synchronous code, so they run inside `run_sync`
    (https://alembic.sqlalchemy.org/en/latest/cookbook.html#using-asyncio-with-alembic).
    """
    engine = create_async_engine(str(DatabaseSettings().database_url), poolclass=pool.NullPool)
    async with engine.connect() as connection:
        await connection.run_sync(run_migrations)
    await engine.dispose()


asyncio.run(run_async_migrations())
