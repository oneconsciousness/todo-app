from sqlalchemy import text

from app.config import Settings
from app.db.engine import create_engine


async def test_pooled_connections_carry_both_timeouts(test_settings: Settings) -> None:
    engine = create_engine(test_settings)
    async with engine.connect() as connection:
        statement_timeout = (await connection.execute(text("SHOW statement_timeout"))).scalar_one()
        idle_timeout = (await connection.execute(text("SHOW idle_in_transaction_session_timeout"))).scalar_one()
    await engine.dispose()
    assert (statement_timeout, idle_timeout) == ("5s", "10s")
