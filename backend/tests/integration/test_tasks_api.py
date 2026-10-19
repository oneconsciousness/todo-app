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


async def test_patch_changes_only_sent_fields_and_bumps_version(app: FastAPI) -> None:
    async with signed_in_client(app) as client:
        created = (await client.post(TASKS, json={"title": "Buy milk", "notes": "two litres"})).json()
        response = await client.patch(task_path(created["id"]), json={"completed": True})
    task = response.json()
    assert response.status_code == 200
    assert response.headers["ETag"] == '"2"'
    assert (task["title"], task["notes"], task["completed"], task["version"]) == ("Buy milk", "two litres", True, 2)
    assert task["updatedAt"] > created["updatedAt"]


async def test_patch_with_null_due_date_clears_it(app: FastAPI) -> None:
    async with signed_in_client(app) as client:
        created = (await client.post(TASKS, json={"title": "Pay rent", "dueDate": "2026-11-01"})).json()
        response = await client.patch(task_path(created["id"]), json={"dueDate": None})
    assert (response.status_code, response.json()["dueDate"]) == (200, None)


async def test_patch_accepts_an_iso_due_date(app: FastAPI) -> None:
    async with signed_in_client(app) as client:
        [task] = await create_tasks(client, ["Pay rent"])
        response = await client.patch(task_path(task.id), json={"dueDate": "2026-12-01"})
    assert (response.status_code, response.json()["dueDate"]) == (200, "2026-12-01")


async def test_patch_rejects_a_string_boolean_with_400(app: FastAPI) -> None:
    async with signed_in_client(app) as client:
        [task] = await create_tasks(client, ["Buy milk"])
        response = await client.patch(task_path(task.id), json={"completed": "true"})
    assert response.status_code == 400
    assert response.json()["error"]["details"][0]["field"] == "completed"


async def test_patch_with_the_current_if_match_succeeds(app: FastAPI) -> None:
    async with signed_in_client(app) as client:
        [task] = await create_tasks(client, ["Buy milk"])
        response = await client.patch(task_path(task.id), json={"title": "Buy oat milk"}, headers={"If-Match": '"1"'})
    assert (response.status_code, response.json()["title"]) == (200, "Buy oat milk")


async def test_patch_with_a_stale_if_match_returns_412(app: FastAPI) -> None:
    async with signed_in_client(app) as client:
        [task] = await create_tasks(client, ["Buy milk"])
        await client.patch(task_path(task.id), json={"notes": "from the other tab"})
        response = await client.patch(task_path(task.id), json={"title": "Buy oat milk"}, headers={"If-Match": '"1"'})
        unchanged = (await client.get(task_path(task.id))).json()
    assert response.status_code == 412
    assert response.json()["error"]["code"] == "version_mismatch"
    assert (unchanged["title"], unchanged["version"]) == ("Buy milk", 2)


async def test_patch_with_a_malformed_if_match_returns_400(app: FastAPI) -> None:
    async with signed_in_client(app) as client:
        [task] = await create_tasks(client, ["Buy milk"])
        long_version = '"' + "1" * 4301 + '"'
        response = await client.patch(task_path(task.id), json={"completed": True}, headers={"If-Match": long_version})
    assert response.status_code == 400
    assert response.json()["error"]["code"] == "invalid_if_match"


async def test_patch_rejects_a_null_title_with_400(app: FastAPI) -> None:
    async with signed_in_client(app) as client:
        [task] = await create_tasks(client, ["Buy milk"])
        response = await client.patch(task_path(task.id), json={"title": None})
    assert response.status_code == 400
    assert response.json()["error"]["details"][0]["field"] == "title"


async def test_patch_rejects_an_empty_body_with_400(app: FastAPI) -> None:
    async with signed_in_client(app) as client:
        [task] = await create_tasks(client, ["Buy milk"])
        response = await client.patch(task_path(task.id), json={})
    assert response.status_code == 400
    assert response.json()["error"]["code"] == "validation_failed"


async def test_patch_after_delete_returns_404(app: FastAPI) -> None:
    async with signed_in_client(app) as client:
        [task] = await create_tasks(client, ["Buy milk"])
        await client.delete(task_path(task.id))
        response = await client.patch(task_path(task.id), json={"completed": True}, headers={"If-Match": '"1"'})
    assert response.status_code == 404
    assert response.json()["error"]["code"] == "not_found"


async def test_delete_returns_204_and_the_task_is_gone(app: FastAPI) -> None:
    async with signed_in_client(app) as client:
        [task] = await create_tasks(client, ["Buy milk"])
        response = await client.delete(task_path(task.id))
        after = await client.get(task_path(task.id))
    assert (response.status_code, response.content) == (204, b"")
    assert after.status_code == 404


async def test_delete_another_users_task_returns_404(app: FastAPI) -> None:
    async with signed_in_client(app) as ada, signed_in_client(app) as bob:
        [task] = await create_tasks(ada, ["Ada's task"])
        response = await bob.delete(task_path(task.id))
        still_there = await ada.get(task_path(task.id))
    assert response.status_code == 404
    assert still_there.status_code == 200


async def test_patch_another_users_task_returns_404(app: FastAPI) -> None:
    async with signed_in_client(app) as ada, signed_in_client(app) as bob:
        [task] = await create_tasks(ada, ["Ada's task"])
        response = await bob.patch(task_path(task.id), json={"completed": True})
        untouched = (await ada.get(task_path(task.id))).json()
    assert response.status_code == 404
    assert (untouched["completed"], untouched["version"]) == (False, 1)
