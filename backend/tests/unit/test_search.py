import re

import pytest
from hypothesis import given
from hypothesis import strategies as st

from app.domain.search import normalize_query, search_pattern

# Inside the wildcards, a backslash, percent or underscore may appear only as the second half of an escape.
ESCAPED_TEXT = re.compile(r"(?:\\[\\%_]|[^\\%_])*")


@pytest.mark.parametrize("query", [None, "", "   ", "\t\n"])
def test_blank_query_means_no_search(query: str | None) -> None:
    assert normalize_query(query) is None


def test_search_pattern_wraps_the_term_in_wildcards() -> None:
    assert search_pattern("milk") == "%milk%"


def test_search_pattern_escapes_backslash_before_percent_and_underscore() -> None:
    assert search_pattern("50%_off\\x") == "%50\\%\\_off\\\\x%"


@given(st.text())
def test_search_pattern_leaves_no_unescaped_wildcard_inside(term: str) -> None:
    inside = search_pattern(term)[1:-1]
    assert ESCAPED_TEXT.fullmatch(inside)
    assert re.sub(r"\\(.)", r"\1", inside, flags=re.DOTALL) == term
