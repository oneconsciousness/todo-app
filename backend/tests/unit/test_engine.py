from typing import Any

import pytest
from sqlalchemy import event
from sqlalchemy.engine.interfaces import Dialect
from sqlalchemy.pool import ConnectionPoolEntry, QueuePool

from app.config import Settings
from app.db.engine import create_engine

SETTINGS = Settings(
    database_url="postgresql+asyncpg://todo:todo@localhost:5432/todo",
    jwt_secret="unit-test-signing-key-0123456789abcdef",
)


class ConnectArgumentsSeen(Exception):
    """Stops a connection attempt once SQLAlchemy has built its arguments, before any socket opens."""

    def __init__(self, arguments: dict[str, Any]) -> None:
        super().__init__()
        self.arguments = arguments


async def test_engine_carries_the_connect_timeout_and_pool_settings() -> None:
    engine = create_engine(SETTINGS)

    # do_connect receives the exact arguments the driver's connect() would get
    # (https://docs.sqlalchemy.org/en/20/core/events.html#sqlalchemy.events.DialectEvents.do_connect).
    @event.listens_for(engine.sync_engine, "do_connect")
    def stop_before_connecting(
        dialect: Dialect, record: ConnectionPoolEntry, cargs: tuple[Any, ...], cparams: dict[str, Any]
    ) -> None:
        raise ConnectArgumentsSeen(dict(cparams))

    with pytest.raises(ConnectArgumentsSeen) as seen:
        await engine.connect()
    await engine.dispose()

    pool = engine.pool
    assert isinstance(pool, QueuePool)
    assert seen.value.arguments["timeout"] == 5
    assert seen.value.arguments["server_settings"] == {
        "statement_timeout": "5000",
        "idle_in_transaction_session_timeout": "10000",
    }
    assert (pool.size(), pool.timeout()) == (10, 5.0)
