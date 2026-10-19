"""Fractional rank keys that order a user's tasks.

A key is an integer part (a head letter that says how many digits follow, then those
digits) and an optional fraction of base-62 digits that never ends in the zero digit.
Keys compare byte by byte, like Python strings and Postgres `COLLATE "C"`. The format is
David Greenspan's fractional indexing (https://observablehq.com/@dgreensp/implementing-fractional-indexing).
"""

from collections.abc import Callable, Mapping
from functools import reduce
from itertools import takewhile
from string import ascii_letters
from types import MappingProxyType
from typing import Final, Literal

DIGITS: Final = "0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz"
BASE: Final = len(DIGITS)
DIGIT_VALUE: Final[Mapping[str, int]] = MappingProxyType({digit: value for value, digit in enumerate(DIGITS)})
DIGIT_SET: Final[frozenset[str]] = frozenset(DIGITS)
HEAD_LETTERS: Final[frozenset[str]] = frozenset(ascii_letters)
ZERO: Final = DIGITS[0]
TOP: Final = DIGITS[-1]
SMALLEST_INTEGER: Final = "A" + ZERO * 26

type DigitsAndCarry = tuple[tuple[str, ...], bool]


class InvalidRank(ValueError):
    """A string is not a well-formed rank key."""


class InvalidRankOrder(ValueError):
    """The lower bound does not sort before the upper bound."""


def integer_length(head: str) -> int:
    """Return how many characters the integer part has, head included: `a` is 2, `z` is 27, `Z` is 2, `A` is 27."""
    return ord(head) - ord("a") + 2 if head.islower() else ord("Z") - ord(head) + 2


def split_rank(rank: str) -> tuple[str, str]:
    """Split a key into its integer part and its fraction."""
    length = integer_length(rank[0])
    return rank[:length], rank[length:]


def has_head_letter(rank: str) -> bool:
    """Check the key starts with an ASCII letter."""
    return rank[:1] in HEAD_LETTERS


def is_long_enough_for_its_head(rank: str) -> bool:
    """Check the key holds at least as many digits as its head letter announces."""
    return len(rank) >= integer_length(rank[0])


def uses_only_base62_digits(rank: str) -> bool:
    """Check every character after the head is a base-62 digit."""
    return DIGIT_SET.issuperset(rank[1:])


def fraction_has_no_trailing_zero(rank: str) -> bool:
    """Check the fraction does not end in the zero digit, so each position has one spelling."""
    return not split_rank(rank)[1].endswith(ZERO)


def is_not_the_smallest_integer(rank: str) -> bool:
    """Check the key is not the bare smallest integer, which leaves no room before it."""
    return rank != SMALLEST_INTEGER


# Ordered: all() stops at the first rule that fails, so each rule may assume the ones before it held.
RANK_RULES: Final[tuple[Callable[[str], bool], ...]] = (
    has_head_letter,
    is_long_enough_for_its_head,
    uses_only_base62_digits,
    fraction_has_no_trailing_zero,
    is_not_the_smallest_integer,
)


def validate_rank(rank: str) -> str:
    """Return the key unchanged when it is well formed.

    Raises:
        InvalidRank: when any rule in `RANK_RULES` fails.
    """
    if not all(rule(rank) for rule in RANK_RULES):
        raise InvalidRank(rank)
    return rank


def common_prefix_length(lower: str, upper: str) -> int:
    """Count the leading digits two fractions share, reading a short `lower` as padded with zeros."""
    pairs = zip(lower.ljust(len(upper), ZERO), upper, strict=False)
    return sum(1 for _ in takewhile(lambda pair: pair[0] == pair[1], pairs))


def midpoint(lower: str, upper: str | None) -> str:
    """Return a fraction strictly between `lower` and `upper`; `None` means no upper bound."""
    prefix = common_prefix_length(lower, upper) if upper else 0
    if upper and prefix:
        return upper[:prefix] + midpoint(lower[prefix:], upper[prefix:])
    lower_digit = DIGIT_VALUE[lower[0]] if lower else 0
    upper_digit = DIGIT_VALUE[upper[0]] if upper else BASE
    if upper_digit - lower_digit > 1:
        return DIGITS[(lower_digit + upper_digit) // 2]
    if upper and len(upper) > 1:
        return upper[0]
    return DIGITS[lower_digit] + midpoint(lower[1:], None)


def step_digits(digits: str, delta: Literal[1, -1]) -> tuple[str, bool]:
    """Add or subtract one from base-62 digits; return the new digits and whether it carried out of the top."""

    def step(state: DigitsAndCarry, digit: str) -> DigitsAndCarry:
        done, carry = state
        value = DIGIT_VALUE[digit] + delta
        if not carry:
            return (digit, *done), False
        if value == BASE:
            return (ZERO, *done), True
        if value == -1:
            return (TOP, *done), True
        return (DIGITS[value], *done), False

    start: DigitsAndCarry = ((), True)
    stepped, carry = reduce(step, reversed(digits), start)
    return "".join(stepped), carry


def increment(integer: str) -> str | None:
    """Return the next integer part, or `None` past the largest one."""
    head, (digits, carry) = integer[0], step_digits(integer[1:], 1)
    match (carry, head):
        case (False, _):
            return head + digits
        case (True, "Z"):
            return "a" + ZERO
        case (True, "z"):
            return None
        case _:
            following = chr(ord(head) + 1)
            return following + digits + ZERO if following.islower() else following + digits[1:]


def decrement(integer: str) -> str | None:
    """Return the previous integer part, or `None` below the smallest one."""
    head, (digits, borrow) = integer[0], step_digits(integer[1:], -1)
    match (borrow, head):
        case (False, _):
            return head + digits
        case (True, "a"):
            return "Z" + TOP
        case (True, "A"):
            return None
        case _:
            previous = chr(ord(head) - 1)
            return previous + digits + TOP if previous.isupper() else previous + digits[1:]


def _validated(rank: str | None) -> str | None:
    return None if rank is None else validate_rank(rank)


def rank_between(lower: str | None, upper: str | None) -> str:
    """Return a key that sorts strictly between two neighbours; `None` leaves that side open.

    Raises:
        InvalidRank: when a bound is malformed.
        InvalidRankOrder: when `lower` does not sort before `upper`.
    """
    match (_validated(lower), _validated(upper)):
        case (None, None):
            return "a" + ZERO
        case (None, str() as upper_rank):
            integer, fraction = split_rank(upper_rank)
            if fraction and integer != SMALLEST_INTEGER:
                # The bare integer sorts just before any key that extends it.
                return integer
            previous = decrement(integer)
            if previous is None:
                return integer + midpoint("", fraction)
            # The smallest integer is never a key on its own, so a key inside it needs a fraction.
            return previous + midpoint("", None) if previous == SMALLEST_INTEGER else previous
        case (str() as lower_rank, None):
            integer, fraction = split_rank(lower_rank)
            return increment(integer) or integer + midpoint(fraction, None)
        case (str() as lower_rank, str() as upper_rank) if lower_rank < upper_rank:
            (lower_integer, lower_fraction), (upper_integer, upper_fraction) = (
                split_rank(lower_rank),
                split_rank(upper_rank),
            )
            if lower_integer == upper_integer:
                return lower_integer + midpoint(lower_fraction, upper_fraction)
            following = increment(lower_integer)
            if following is not None and following < upper_rank:
                return following
            return lower_integer + midpoint(lower_fraction, None)
        case _:
            raise InvalidRankOrder(f"{lower!r} does not sort before {upper!r}")
