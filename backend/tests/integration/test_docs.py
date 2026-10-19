from httpx import AsyncClient


async def test_openapi_document_and_docs_page_are_served(client: AsyncClient) -> None:
    document = await client.get("/api/openapi.json")
    page = await client.get("/api/docs")
    assert (document.status_code, document.json()["info"]["title"]) == (200, "todo-app API")
    assert (page.status_code, page.headers["content-type"].split(";")[0]) == (200, "text/html")
