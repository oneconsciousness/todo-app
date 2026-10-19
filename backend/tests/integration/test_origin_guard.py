from fastapi import FastAPI
from httpx import AsyncClient

from tests.support.factories import PASSWORD, signed_in_client

REGISTER = "/api/v1/auth/register"


async def test_write_from_another_origin_is_forbidden(client: AsyncClient) -> None:
    # An invalid body as well: the guard runs before the body is validated, so the answer is still 403.
    response = await client.post(REGISTER, json={"email": "not-an-email"}, headers={"Origin": "https://evil.example"})
    assert response.status_code == 403
    assert response.json()["error"]["code"] == "forbidden_origin"


async def test_write_with_null_origin_is_forbidden(client: AsyncClient) -> None:
    response = await client.post(
        REGISTER, json={"email": "ada@example.com", "password": PASSWORD}, headers={"Origin": "null"}
    )
    assert response.status_code == 403


async def test_write_without_origin_is_allowed(client: AsyncClient) -> None:
    request = client.build_request("POST", REGISTER, json={"email": "ada@example.com", "password": PASSWORD})
    del request.headers["Origin"]
    response = await client.send(request)
    assert response.status_code == 201


async def test_read_from_another_origin_is_allowed(app: FastAPI) -> None:
    async with signed_in_client(app) as client:
        response = await client.get("/api/v1/auth/me", headers={"Origin": "https://evil.example"})
    assert response.status_code == 200


async def test_text_plain_body_is_rejected_with_400(client: AsyncClient) -> None:
    body = '{"email": "ada@example.com", "password": "correct horse battery staple"}'
    response = await client.post(REGISTER, content=body, headers={"Content-Type": "text/plain"})
    assert response.status_code == 400
