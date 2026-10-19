from uuid import uuid4

from fastapi import FastAPI
from httpx import AsyncClient

from tests.support.factories import create_tasks, signed_in_client

TASKS = "/api/v1/tasks"


def task_path(task_id: object) -> str:
    """Return the address of one task."""
    return f"{TASKS}/{task_id}"


async def test_list_returns_only_own_tasks_in_rank_order(app: FastAPI) -> None:
    async with signed_in_client(app) as ada, signed_in_client(app) as bob:
        await create_tasks(ada, ["first", "second", "third"])
        await create_tasks(bob, ["bob's task"])
        response = await ada.get(TASKS)
    items = response.json()["items"]
    assert response.status_code == 200
    assert [item["title"] for item in items] == ["third", "second", "first"]
    assert [item["rank"] for item in items] == sorted(item["rank"] for item in items)


async def test_list_without_a_session_returns_401(client: AsyncClient) -> None:
    response = await client.get(TASKS)
    assert response.status_code == 401
    assert response.json()["error"]["code"] == "not_authenticated"


async def test_create_puts_the_task_at_the_top_with_location_and_etag(app: FastAPI) -> None:
    async with signed_in_client(app) as client:
        [older] = await create_tasks(client, ["older"])
        response = await client.post(TASKS, json={"title": "  Buy milk  ", "dueDate": "2026-10-20"})
        listed = (await client.get(TASKS)).json()["items"]
    task = response.json()
    assert response.status_code == 201
    assert response.headers["Location"] == task_path(task["id"])
    assert response.headers["ETag"] == '"1"'
    assert (task["title"], task["notes"], task["dueDate"], task["completed"]) == ("Buy milk", "", "2026-10-20", False)
    assert [item["id"] for item in listed] == [task["id"], str(older.id)]


async def test_create_rejects_a_blank_title_with_400(app: FastAPI) -> None:
    async with signed_in_client(app) as client:
        response = await client.post(TASKS, json={"title": "   "})
    assert response.status_code == 400
    assert response.json()["error"]["details"][0]["field"] == "title"


async def test_create_rejects_an_unknown_field_with_400(app: FastAPI) -> None:
    async with signed_in_client(app) as client:
        response = await client.post(TASKS, json={"title": "Buy milk", "priority": "high"})
    assert response.status_code == 400
    assert response.json()["error"]["details"][0]["field"] == "priority"


async def test_get_returns_the_task_with_its_etag(app: FastAPI) -> None:
    async with signed_in_client(app) as client:
        [task] = await create_tasks(client, ["Buy milk"])
        response = await client.get(task_path(task.id))
    assert response.status_code == 200
    assert response.headers["ETag"] == '"1"'
    assert response.json()["id"] == str(task.id)


async def test_get_another_users_task_returns_404(app: FastAPI) -> None:
    async with signed_in_client(app) as ada, signed_in_client(app) as bob:
        [task] = await create_tasks(ada, ["Ada's task"])
        response = await bob.get(task_path(task.id))
    assert response.status_code == 404
    assert response.json()["error"]["code"] == "not_found"


async def test_get_an_unknown_task_returns_404(app: FastAPI) -> None:
    async with signed_in_client(app) as client:
        response = await client.get(task_path(uuid4()))
    assert response.status_code == 404
    assert response.json()["error"]["code"] == "not_found"


async def test_get_with_a_malformed_id_returns_400(app: FastAPI) -> None:
    async with signed_in_client(app) as client:
        response = await client.get(task_path("not-a-uuid"))
    assert response.status_code == 400
    assert response.json()["error"]["code"] == "validation_failed"
