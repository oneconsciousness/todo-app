import asyncio
import base64
import hashlib
import random
import re
from http.cookies import SimpleCookie
from uuid import uuid4

import httpx
import pytest

from support import API_REPLICAS, BASE_URL, PASSWORD, unique_email


def test_migrations_ran_and_signup_works_through_the_proxy(client: httpx.Client) -> None:
    response = client.post("/api/v1/auth/register", json={"email": unique_email(), "password": PASSWORD})

    assert response.status_code == 201


def test_session_cookie_survives_the_proxy_with_its_attributes(client: httpx.Client) -> None:
    response = client.post("/api/v1/auth/register", json={"email": unique_email(), "password": PASSWORD})

    session = SimpleCookie(response.headers["set-cookie"])["session"]
    assert (session["httponly"], session["samesite"].lower(), session["path"], session["max-age"]) == (
        True,
        "strict",
        "/api",
        "28800",
    )


def test_deep_link_serves_the_spa(client: httpx.Client) -> None:
    response = client.get(f"/tasks/{uuid4()}")

    assert response.status_code == 200
    assert response.headers["content-type"].split(";")[0] == "text/html"
    assert '<div id="root">' in response.text


def test_api_docs_are_served_through_the_proxy(client: httpx.Client) -> None:
    page = client.get("/api/docs")
    document = client.get("/api/openapi.json")

    assert (page.status_code, page.headers["content-type"].split(";")[0]) == (200, "text/html")
    assert (document.status_code, document.json()["info"]["title"]) == (200, "todo-app API")


def test_session_from_one_replica_is_accepted_by_every_replica(client: httpx.Client) -> None:
    client.post("/api/v1/auth/register", json={"email": unique_email(), "password": PASSWORD})
    task_id = client.post("/api/v1/tasks", json={"title": "seen by every replica"}).json()["id"]

    # nginx spreads requests over the replicas, so twenty calls per replica reach them all.
    answers = [client.get("/api/v1/tasks") for _ in range(20 * API_REPLICAS)]

    assert {answer.status_code for answer in answers} == {200}
    assert {tuple(item["id"] for item in answer.json()["items"]) for answer in answers} == {(task_id,)}
    assert len({answer.headers["x-served-by"] for answer in answers}) == API_REPLICAS


def test_etag_from_the_proxy_works_as_if_match_for_a_client_that_accepts_gzip(client: httpx.Client) -> None:
    client.post("/api/v1/auth/register", json={"email": unique_email(), "password": PASSWORD})
    task_id = client.post("/api/v1/tasks", json={"title": "edited by a script"}).json()["id"]
    gzip = {"Accept-Encoding": "gzip"}

    read = client.get(f"/api/v1/tasks/{task_id}", headers=gzip)
    edited = client.patch(
        f"/api/v1/tasks/{task_id}", json={"notes": "kept"}, headers={**gzip, "If-Match": read.headers["etag"]}
    )

    assert (read.headers["etag"], edited.status_code) == ('"1"', 200)


SECURITY_HEADERS = {
    "x-content-type-options": "nosniff",
    "referrer-policy": "strict-origin-when-cross-origin",
    "x-frame-options": "DENY",
    "permissions-policy": "camera=(), microphone=(), geolocation=()",
    "cross-origin-opener-policy": "same-origin",
}


def test_security_headers_are_set_on_the_spa(client: httpx.Client) -> None:
    response = client.get("/")

    assert {name: response.headers.get(name) for name in SECURITY_HEADERS} == SECURITY_HEADERS
    # httpx joins repeated headers with ", ", so a second CSP would hide inside the first; count them instead.
    assert len(response.headers.get_list("content-security-policy")) == 1
    assert "default-src 'self'" in response.headers["content-security-policy"]
    assert "frame-ancestors 'none'" in response.headers["content-security-policy"]
    assert response.headers["cache-control"] == "no-cache"
    assert response.headers["server"] == "nginx"


@pytest.mark.parametrize("probe", ["/livez", "/readyz"])
def test_probes_are_not_reachable_through_the_front_door(client: httpx.Client, probe: str) -> None:
    assert client.get(probe).status_code == 404


def test_body_over_64_kb_is_rejected_at_the_proxy(client: httpx.Client) -> None:
    oversized = b"x" * (64 * 1024 + 1)

    response = client.post("/api/v1/tasks", content=oversized, headers={"Content-Type": "application/json"})

    assert response.status_code == 413
    assert "x-served-by" not in response.headers


def test_api_docs_csp_allows_the_inline_script_the_page_serves(client: httpx.Client) -> None:
    page = client.get("/api/docs")

    [inline_script] = re.findall(r"<script>(.*?)</script>", page.text, re.DOTALL)
    digest = base64.b64encode(hashlib.sha256(inline_script.encode()).digest()).decode()
    assert len(page.headers.get_list("content-security-policy")) == 1
    assert f"'sha256-{digest}'" in page.headers["content-security-policy"]


async def fire_moves_through_every_replica(moves: int, seed: int) -> tuple[list[httpx.Response], list[str], list[str]]:
    """Sign up, create ten tasks, then send every move at once; return the answers, task ids and listed ids."""
    async with httpx.AsyncClient(base_url=BASE_URL, headers={"Origin": BASE_URL}, timeout=30.0) as client:
        await client.post("/api/v1/auth/register", json={"email": unique_email(), "password": PASSWORD})
        task_ids = [(await client.post("/api/v1/tasks", json={"title": f"task {n}"})).json()["id"] for n in range(10)]
        pick = random.Random(seed)
        pairs = [pick.sample(task_ids, 2) for _ in range(moves)]
        async with asyncio.TaskGroup() as group:
            sent = [
                group.create_task(client.put(f"/api/v1/tasks/{task}/position", json={"afterId": after}))
                for task, after in pairs
            ]
        listed = (await client.get("/api/v1/tasks")).json()["items"]
    return [move.result() for move in sent], task_ids, [item["rank"] for item in listed]


def test_concurrent_moves_through_every_replica_keep_ranks_unique() -> None:
    answers, task_ids, ranks = asyncio.run(fire_moves_through_every_replica(moves=50, seed=7))

    assert {answer.status_code for answer in answers} == {200}
    assert len({answer.headers["x-served-by"] for answer in answers}) == API_REPLICAS
    assert len(ranks) == len(set(ranks)) == len(task_ids)
