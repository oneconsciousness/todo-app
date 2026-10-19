from collections.abc import Callable
from itertools import accumulate
from string import ascii_letters

import pytest
from hypothesis import given
from hypothesis import strategies as st

from app.domain.ranks import (
    DIGITS,
    SMALLEST_INTEGER,
    ZERO,
    InvalidRank,
    InvalidRankOrder,
    fraction_has_no_trailing_zero,
    has_head_letter,
    integer_length,
    is_long_enough_for_its_head,
    is_not_the_smallest_integer,
    rank_between,
    uses_only_base62_digits,
    validate_rank,
)

# An integer part: a head letter followed by the number of digits it announces.
integer_parts = st.sampled_from(ascii_letters).flatmap(
    lambda head: st.text(alphabet=DIGITS, min_size=integer_length(head) - 1, max_size=integer_length(head) - 1).map(
        lambda digits: head + digits
    )
)
fractions = st.text(alphabet=DIGITS, max_size=6).filter(lambda text: not text.endswith(ZERO))


def as_key(integer: str, fraction: str) -> str:
    """Join the parts, nudging the one bare key the format forbids to its nearest valid neighbour."""
    key = integer + fraction
    return key if key != SMALLEST_INTEGER else key + "1"


valid_ranks = st.builds(as_key, integer_parts, fractions)
ranks_sharing_an_integer = integer_parts.flatmap(
    lambda integer: st.lists(fractions.map(lambda fraction: as_key(integer, fraction)), min_size=2, unique=True)
)
sorted_ranks = st.one_of(st.lists(valid_ranks, min_size=2, unique=True), ranks_sharing_an_integer).map(sorted)


def insert_at(ranks: tuple[str, ...], slot: int) -> tuple[str, ...]:
    """Insert a new rank between the neighbours of a slot, the way a move or create would."""
    index = slot % (len(ranks) + 1)
    lower = ranks[index - 1] if index > 0 else None
    upper = ranks[index] if index < len(ranks) else None
    return (*ranks[:index], rank_between(lower, upper), *ranks[index:])


def insertion_states(slots: list[int]) -> list[tuple[str, ...]]:
    """Return the list of ranks after each insert driven by the slots."""
    empty: tuple[str, ...] = ()
    return list(accumulate(slots, insert_at, initial=empty))


@pytest.mark.parametrize(
    ("rule", "rank"),
    [
        (has_head_letter, "0a"),
        (has_head_letter, ""),
        (is_long_enough_for_its_head, "b0"),
        (uses_only_base62_digits, "a!"),
        (fraction_has_no_trailing_zero, "a0V0"),
        (is_not_the_smallest_integer, SMALLEST_INTEGER),
    ],
)
def test_validate_rank_rejects_each_malformed_shape(rule: Callable[[str], bool], rank: str) -> None:
    assert not rule(rank)
    with pytest.raises(InvalidRank):
        validate_rank(rank)


def test_rank_between_with_no_neighbours_is_a0() -> None:
    assert rank_between(None, None) == "a0"


def test_rank_between_a0_and_a1_is_a0V() -> None:
    assert rank_between("a0", "a1") == "a0V"


def test_rank_between_a0_and_a0V_is_a0F() -> None:
    assert rank_between("a0", "a0V") == "a0F"


def test_rank_before_a0_is_Zz() -> None:
    assert rank_between(None, "a0") == "Zz"


@pytest.mark.parametrize(("lower", "upper"), [("a1", "a0"), ("a0", "a0")])
def test_rank_between_rejects_unordered_bounds(lower: str, upper: str) -> None:
    with pytest.raises(InvalidRankOrder):
        rank_between(lower, upper)


def test_rank_between_rejects_a_malformed_key() -> None:
    with pytest.raises(InvalidRank):
        rank_between("a", None)


def test_thousand_prepends_keep_ranks_at_most_three_characters() -> None:
    ranks = list(accumulate(range(999), lambda first, _: rank_between(None, first), initial="a0"))
    assert max(map(len, ranks)) <= 3


def test_thousand_appends_keep_ranks_at_most_three_characters() -> None:
    ranks = list(accumulate(range(999), lambda last, _: rank_between(last, None), initial="a0"))
    assert max(map(len, ranks)) <= 3


@given(sorted_ranks, st.data())
def test_rank_is_strictly_between_its_bounds(ranks: list[str], data: st.DataObject) -> None:
    lower_index = data.draw(st.integers(min_value=0, max_value=len(ranks) - 2))
    upper_index = data.draw(st.integers(min_value=lower_index + 1, max_value=len(ranks) - 1))
    lower, upper = ranks[lower_index], ranks[upper_index]
    assert lower < rank_between(lower, upper) < upper


@given(valid_ranks)
def test_rank_before_first_sorts_first(first: str) -> None:
    assert rank_between(None, first) < first


@given(valid_ranks)
def test_rank_after_last_sorts_last(last: str) -> None:
    assert rank_between(last, None) > last


@given(st.lists(st.integers(min_value=0), max_size=60))
def test_any_insertion_sequence_keeps_ranks_sorted_and_unique(slots: list[int]) -> None:
    assert all(ranks == tuple(sorted(set(ranks))) for ranks in insertion_states(slots))


@given(st.lists(valid_ranks, max_size=2, unique=True).map(sorted), st.lists(st.integers(min_value=0), max_size=30))
def test_generated_ranks_are_valid_keys(seeds: list[str], slots: list[int]) -> None:
    states = accumulate(slots, insert_at, initial=tuple(seeds))
    generated = {rank for ranks in states for rank in ranks} - set(seeds)
    assert all(validate_rank(rank) == rank for rank in generated)
