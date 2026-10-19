"""Turn a user's search box text into a safe `ILIKE` pattern."""

from typing import Final

# Each LIKE metacharacter, and the escape character itself, gets a leading backslash.
LIKE_ESCAPES: Final = str.maketrans({"\\": "\\\\", "%": "\\%", "_": "\\_"})


def normalize_query(q: str | None) -> str | None:
    """Return the trimmed search term, or `None` when there is nothing to search for."""
    return (q or "").strip() or None


def search_pattern(q: str) -> str:
    """Return a pattern that matches `q` anywhere, with `%`, `_` and `\\` matched literally.

    The repository passes it as a bound parameter to `ILIKE ... ESCAPE '\\'`
    (https://www.postgresql.org/docs/18/functions-matching.html#FUNCTIONS-LIKE).
    """
    return f"%{q.translate(LIKE_ESCAPES)}%"
