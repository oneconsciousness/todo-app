"""Build the test database from the real migrations."""

import os
import subprocess
import sys
from pathlib import Path
from typing import Final

from sqlalchemy import URL, text
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy.pool import NullPool

BACKEND_DIR: Final = Path(__file__).resolve().parents[2]
# The name the statements below use; change them together.
TEST_DATABASE: Final = "todo_test"


async def recreate_test_database(server_url: URL) -> None:
    """Drop and create the test database through the server's maintenance database."""
    engine = create_async_engine(server_url, isolation_level="AUTOCOMMIT", poolclass=NullPool)
    async with engine.connect() as connection:
        await connection.execute(text("DROP DATABASE IF EXISTS todo_test WITH (FORCE)"))
        await connection.execute(text("CREATE DATABASE todo_test"))
    await engine.dispose()


def migrate(database_url: URL) -> None:
    """Run `alembic upgrade head` in a subprocess, as the migrate container would.

    A subprocess, because alembic's env.py starts its own event loop with `asyncio.run`.
    """
    environment = os.environ | {"DATABASE_URL": database_url.render_as_string(hide_password=False)}
    subprocess.run(
        [sys.executable, "-m", "alembic", "upgrade", "head"],
        cwd=BACKEND_DIR,
        env=environment,
        check=True,
    )
