"""Turn a partial update into the column values to write."""

from dataclasses import fields
from typing import cast

from app.domain.errors import EmptyPatch
from app.domain.types import TaskChanges, TaskPatch, Unset


def apply_patch(patch: TaskPatch) -> TaskChanges:
    """Return only the fields that were sent, keyed by column name; a `None` due date is kept, since it clears.

    Raises:
        EmptyPatch: when no field was sent.
    """
    changes = {field.name: value for field in fields(patch) if (value := getattr(patch, field.name)) is not Unset.UNSET}
    if not changes:
        raise EmptyPatch
    # TaskPatch's field names are TaskChanges' keys; mypy cannot follow names read through fields().
    return cast(TaskChanges, changes)
