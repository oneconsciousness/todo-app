import base64
import hashlib
import re
from http.cookies import SimpleCookie
from unittest.mock import ANY
from uuid import uuid4

import httpx
import pytest

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
    assert f"'sha256-{digest}'" in page.headers["content-security-policy"]
