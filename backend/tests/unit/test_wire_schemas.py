import pytest

from app.api.schemas import TaskUpdate


def update_field_types(field: str) -> set[str]:
    """Return the JSON types the published schema allows for one field of a task update."""
    schema = TaskUpdate.model_json_schema(by_alias=True)["properties"][field]
    return {option["type"] for option in schema.get("anyOf", [schema])}


@pytest.mark.parametrize(("field", "json_type"), [("title", "string"), ("notes", "string"), ("completed", "boolean")])
def test_update_schema_does_not_offer_null_where_the_api_refuses_it(field: str, json_type: str) -> None:
    assert update_field_types(field) == {json_type}


def test_update_schema_offers_null_for_due_date_which_clears_it() -> None:
    assert update_field_types("dueDate") == {"string", "null"}
