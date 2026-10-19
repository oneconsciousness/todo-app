from uuid import uuid4

from fastapi import FastAPI
from httpx import AsyncClient

from app.api.schemas import TaskRead
from tests.support.factories import create_tasks, signed_in_client

TASKS = "/api/v1/tasks"


def position_path(task_id: object) -> str:
    """Return the address that sets a task's place in the list."""
    return f"{TASKS}/{task_id}/position"


async def listed_titles(client: AsyncClient) -> list[str]:
    """Return the titles in list order."""
    return [item["title"] for item in (await client.get(TASKS)).json()["items"]]


async def test_move_to_the_top(app: FastAPI) -> None:
    async with signed_in_client(app) as client:
        oldest, _, _ = await create_tasks(client, ["a", "b", "c"])
        response = await client.put(position_path(oldest.id), json={"afterId": None})
        titles = await listed_titles(client)
    assert response.status_code == 200
    assert response.headers["ETag"] == '"1"'
    assert titles == ["a", "c", "b"]


async def test_move_after_another_task(app: FastAPI) -> None:
    async with signed_in_client(app) as client:
        a, _, c = await create_tasks(client, ["a", "b", "c"])
        response = await client.put(position_path(c.id), json={"afterId": str(a.id)})
        titles = await listed_titles(client)
    assert response.status_code == 200
    assert titles == ["b", "a", "c"]


async def test_move_keeps_version_and_updated_at(app: FastAPI) -> None:
    async with signed_in_client(app) as client:
        a, b = await create_tasks(client, ["a", "b"])
        response = await client.put(position_path(b.id), json={"afterId": str(a.id)})
    moved = TaskRead.model_validate(response.json())
    assert moved.rank != b.rank
    assert (moved.version, moved.updated_at) == (b.version, b.updated_at)


async def test_move_after_an_unknown_task_returns_400(app: FastAPI) -> None:
    async with signed_in_client(app) as client:
        [task] = await create_tasks(client, ["a"])
        response = await client.put(position_path(task.id), json={"afterId": str(uuid4())})
    assert response.status_code == 400
    assert response.json()["error"]["code"] == "invalid_position"


async def test_move_after_another_users_task_returns_the_same_400(app: FastAPI) -> None:
    async with signed_in_client(app) as ada, signed_in_client(app) as bob:
        [adas] = await create_tasks(ada, ["Ada's task"])
        [bobs] = await create_tasks(bob, ["Bob's task"])
        theirs = await bob.put(position_path(bobs.id), json={"afterId": str(adas.id)})
        unknown = await bob.put(position_path(bobs.id), json={"afterId": str(uuid4())})
    assert (theirs.status_code, theirs.json()) == (unknown.status_code, unknown.json())


async def test_move_after_itself_returns_400(app: FastAPI) -> None:
    async with signed_in_client(app) as client:
        [task] = await create_tasks(client, ["a"])
        response = await client.put(position_path(task.id), json={"afterId": str(task.id)})
    assert response.status_code == 400
    assert response.json()["error"]["code"] == "invalid_position"


async def test_move_another_users_task_returns_404(app: FastAPI) -> None:
    async with signed_in_client(app) as ada, signed_in_client(app) as bob:
        [adas] = await create_tasks(ada, ["Ada's task"])
        response = await bob.put(position_path(adas.id), json={"afterId": None})
    assert response.status_code == 404
    assert response.json()["error"]["code"] == "not_found"


async def test_move_to_where_it_already_is_keeps_its_rank(app: FastAPI) -> None:
    async with signed_in_client(app) as client:
        a, b = await create_tasks(client, ["a", "b"])
        after_its_predecessor = await client.put(position_path(a.id), json={"afterId": str(b.id)})
        top_to_top = await client.put(position_path(b.id), json={"afterId": None})
    assert after_its_predecessor.json()["rank"] == a.rank
    assert top_to_top.json()["rank"] == b.rank
