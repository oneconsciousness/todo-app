from http.cookies import SimpleCookie
from unittest.mock import ANY
from uuid import uuid4

import httpx

from support import PASSWORD, unique_email


def test_migrations_ran_and_signup_works_through_the_proxy(client: httpx.Client) -> None:
    email = unique_email()

    response = client.post("/api/v1/auth/register", json={"email": email, "password": PASSWORD})

    assert response.status_code == 201
    assert response.json() == {"id": ANY, "email": email}


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


def test_session_from_one_replica_is_accepted_by_the_other(client: httpx.Client) -> None:
    client.post("/api/v1/auth/register", json={"email": unique_email(), "password": PASSWORD})

    # nginx spreads requests over the replicas, so a few dozen calls reach both.
    answers = [client.get("/api/v1/auth/me") for _ in range(40)]

    assert {answer.status_code for answer in answers} == {200}
    assert len({answer.headers["x-served-by"] for answer in answers}) == 2
