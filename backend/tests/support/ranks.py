"""Build rank sequences the way creates and moves would."""

import random
from functools import reduce

from app.domain.ranks import rank_between


def insert_at(ranks: tuple[str, ...], slot: int) -> tuple[str, ...]:
    """Insert a new rank between the neighbours of a slot, the way a move or create would."""
    index = slot % (len(ranks) + 1)
    lower = ranks[index - 1] if index > 0 else None
    upper = ranks[index] if index < len(ranks) else None
    return (*ranks[:index], rank_between(lower, upper), *ranks[index:])


def seeded_ranks(count: int, seed: int) -> tuple[str, ...]:
    """Return `count` ranks built by inserts at random slots, the same every run for a given seed."""
    generator = random.Random(seed)
    empty: tuple[str, ...] = ()
    return reduce(insert_at, (generator.randrange(count) for _ in range(count)), empty)
