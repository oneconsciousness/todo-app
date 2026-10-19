import pytest

from app.api.tasks import expected_version
from app.domain.errors import InvalidPrecondition


async def test_no_if_match_means_no_version_check() -> None:
    assert await expected_version(None) is None


@pytest.mark.parametrize(("if_match", "version"), [('"1"', 1), ('"42"', 42), ('"2147483647"', 2**31 - 1)])
async def test_a_quoted_version_is_read_as_that_number(if_match: str, version: int) -> None:
    assert await expected_version(if_match) == version


@pytest.mark.parametrize(
    "if_match",
    ["1", '"0"', '"-1"', '"01"', '"abc"', 'W/"1"', "*", '"2147483648"', '"' + "1" * 4301 + '"'],
    ids=["unquoted", "zero", "negative", "leading-zero", "not-a-number", "weak", "star", "over-int4", "4301-digits"],
)
async def test_anything_else_is_an_invalid_precondition(if_match: str) -> None:
    with pytest.raises(InvalidPrecondition):
        await expected_version(if_match)
