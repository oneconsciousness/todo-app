from fastapi import FastAPI
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncEngine

from app.db.models import Task
from app.db.tasks import search_condition
from app.domain.search import search_pattern
from tests.support.factories import create_tasks, signed_in_client

TASKS = "/api/v1/tasks"


async def test_search_matches_title_or_notes_ignoring_case_in_rank_order(app: FastAPI) -> None:
    async with signed_in_client(app) as client:
        await client.post(TASKS, json={"title": "Call mum", "notes": "ask about the MILK order"})
        await create_tasks(client, ["Walk the dog", "Buy Milk"])
        response = await client.get(TASKS, params={"q": "  milk "})
    assert response.status_code == 200
    assert [item["title"] for item in response.json()["items"]] == ["Buy Milk", "Call mum"]


async def test_search_treats_percent_and_underscore_literally(app: FastAPI) -> None:
    async with signed_in_client(app) as client:
        await create_tasks(client, ["50% off", "500 off", "a_b", "axb"])
        percent = await client.get(TASKS, params={"q": "50%"})
        underscore = await client.get(TASKS, params={"q": "a_b"})
    assert [item["title"] for item in percent.json()["items"]] == ["50% off"]
    assert [item["title"] for item in underscore.json()["items"]] == ["a_b"]


async def test_search_over_200_characters_returns_400(app: FastAPI) -> None:
    async with signed_in_client(app) as client:
        response = await client.get(TASKS, params={"q": "x" * 201})
    assert response.status_code == 400
    assert response.json()["error"]["details"][0]["field"] == "q"


async def test_search_query_can_use_the_trigram_index(database_engine: AsyncEngine) -> None:
    # The search condition alone: with the owner filter added, a small table is better served by the owner index.
    statement = select(Task.id).where(search_condition(search_pattern("milk")))
    compiled = statement.compile(dialect=database_engine.dialect)
    parameters = tuple(compiled.params[name] for name in compiled.positiontup or ())
    async with database_engine.begin() as connection:
        # With sequential scans priced out, the planner shows which index it can use for the search.
        await connection.execute(text("SET LOCAL enable_seqscan = off"))
        plan = (await connection.exec_driver_sql(f"EXPLAIN {compiled}", parameters)).scalars().all()
    assert any("ix_tasks_search_trgm" in line for line in plan)
